"""Settings tab — password-protected, RDP level selector, timestamped logs."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ── persistence paths ────────────────────────────────────────────────────────────────────
_CONFIG_DIR  = Path.home() / ".stm32flash"
_CONFIG_FILE = _CONFIG_DIR / "settings.json"
_STATS_FILE  = _CONFIG_DIR / "stats.json"

DEFAULT_PASSWORD_HASH = hashlib.sha256(b"123").hexdigest()

COLOR = {
    "bg":       "#0f0f0f",
    "surface":  "#161616",
    "surface2": "#1c1c1c",
    "border":   "#2a2a2a",
    "text":     "#e8e8e8",
    "muted":    "#6a6a6a",
    "accent":   "#01696f",
    "accent_h": "#0c4e54",
    "accent_p": "#0f3638",
    "ok":       "#3fb950",
    "warn":     "#d29922",
    "err":      "#f85149",
    "disabled": "#2e2e2e",
}

LEVEL_COLORS = {
    "info":  "#9cdcfe",
    "ok":    "#3fb950",
    "warn":  "#d29922",
    "error": "#f85149",
}

# ── RDP warning messages ──────────────────────────────────────────────────────────────────
_RDP_WARNINGS = {
    0: None,   # No protection — no popup needed
    1: (
        "RDP Level 1",
        "This protection level enables read-out protection of the firmware binary.\n\n"
        "It is REVERSIBLE, but reverting to Level 0 will ERASE the firmware stored on the device.\n\n"
        "Are you sure you want to enable RDP Level 1?"
    ),
    2: (
        "RDP Level 2 \u2014 PERMANENT",
        "\u26a0\ufe0f WARNING: RDP Level 2 is PERMANENT and IRREVERSIBLE.\n\n"
        "Once set, all debug access is permanently disabled and CANNOT be undone \u2014 ever.\n\n"
        "This level does NOT protect against firmware reverse engineering \u2014 it only "
        "disables debug interfaces.\n\n"
        "Are you absolutely sure you want to continue?"
    ),
}


# ── persistence helpers ───────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    # fix: default rdp_level corrigido de 1 para 0.
    # Primeira instalação não deve pré-selecionar RDP sem ação explícita do usuário.
    return {"password_hash": DEFAULT_PASSWORD_HASH, "openocd_path": "", "rdp_level": 0}


def _save_config(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(data, indent=2))


def _load_stats() -> dict:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if _STATS_FILE.exists():
        try:
            return json.loads(_STATS_FILE.read_text())
        except Exception:
            pass
    return {"total": 0, "success": 0, "failed": 0, "last_flash": None}


def _save_stats(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _STATS_FILE.write_text(json.dumps(data, indent=2))


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── SettingsTab ──────────────────────────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    """Settings panel: OpenOCD path, RDP level, password management, system log."""

    openocd_path_changed = pyqtSignal(str)

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self._main   = main_window
        self._config = _load_config()
        self._stats  = _load_stats()
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── OpenOCD path ──
        grp_ocd = QGroupBox("OPENOCD")
        ocd_row = QHBoxLayout(grp_ocd)
        ocd_row.setSpacing(6)
        ocd_row.addWidget(_lbl("Path:"))

        self._ocd_input = QLineEdit()
        self._ocd_input.setPlaceholderText(
            "Path to openocd executable (auto-detection enabled at startup)"
        )
        self._ocd_input.setText(self._config.get("openocd_path", ""))
        self._ocd_input.editingFinished.connect(self._save_openocd_path)
        ocd_row.addWidget(self._ocd_input)

        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(32)
        btn_browse.clicked.connect(self._browse_openocd)
        ocd_row.addWidget(btn_browse)

        btn_detect = QPushButton("Auto")
        btn_detect.setFixedWidth(48)
        btn_detect.setToolTip("Re-run auto-detection in default locations")
        btn_detect.clicked.connect(self._auto_detect)
        ocd_row.addWidget(btn_detect)

        root.addWidget(grp_ocd)

        # ── RDP level ──
        grp_rdp = QGroupBox("READ PROTECTION (RDP)")
        rdp_col = QVBoxLayout(grp_rdp)
        rdp_col.setSpacing(4)

        rdp_desc = QLabel(
            "Select the RDP level to apply after flashing. "
            "Changing from Level 1 or 2 requires confirmation."
        )
        rdp_desc.setStyleSheet(f"color:{COLOR['muted']};font-size:10px;")
        rdp_desc.setWordWrap(True)
        rdp_col.addWidget(rdp_desc)

        rdp_btn_row = QHBoxLayout()
        self._rdp_group = QButtonGroup(self)
        rdp_labels = [
            ("Level 0",  "No protection (factory default)"),
            ("Level 1",  "Read-out protection (reversible \u2014 erase on revert)"),
            ("Level 2",  "Full debug lock (PERMANENT \u2014 irreversible)"),
        ]
        for i, (btn_text, tooltip) in enumerate(rdp_labels):
            rb = QRadioButton(btn_text)
            rb.setToolTip(tooltip)
            rb.setStyleSheet(f"color:{COLOR['text']};font-size:11px;")
            self._rdp_group.addButton(rb, i)
            rdp_btn_row.addWidget(rb)
        rdp_btn_row.addStretch()

        saved_level = self._config.get("rdp_level", 0)
        btn = self._rdp_group.button(saved_level)
        if btn:
            btn.setChecked(True)

        self._rdp_group.idClicked.connect(self._on_rdp_selected)
        rdp_col.addLayout(rdp_btn_row)
        root.addWidget(grp_rdp)

        # ── Password ──
        grp_pwd = QGroupBox("SECURITY")
        pwd_row = QHBoxLayout(grp_pwd)
        pwd_row.setSpacing(6)
        pwd_row.addWidget(_lbl("New password:"))

        self._pwd_new = QLineEdit()
        self._pwd_new.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_new.setPlaceholderText("Leave empty to disable password protection")
        self._pwd_new.setFixedWidth(200)
        pwd_row.addWidget(self._pwd_new)

        pwd_row.addWidget(_lbl("Confirm:"))
        self._pwd_confirm = QLineEdit()
        self._pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_confirm.setPlaceholderText("Confirm password")
        self._pwd_confirm.setFixedWidth(180)
        pwd_row.addWidget(self._pwd_confirm)

        btn_save_pwd = QPushButton("Save")
        btn_save_pwd.setFixedWidth(64)
        btn_save_pwd.clicked.connect(self._change_password)
        pwd_row.addWidget(btn_save_pwd)
        pwd_row.addStretch()
        root.addWidget(grp_pwd)

        # ── System log ──
        grp_log = QGroupBox("SYSTEM LOG")
        log_layout = QVBoxLayout(grp_log)
        log_layout.setSpacing(4)

        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setFont(QFont("Consolas", 9))
        self._log_panel.setStyleSheet(
            f"background:{COLOR['surface2']};color:{COLOR['text']};"
            f"border:1px solid {COLOR['border']};border-radius:3px;"
        )
        self._log_panel.setMinimumHeight(200)
        log_layout.addWidget(self._log_panel)

        btn_clear = QPushButton("Clear log")
        btn_clear.setFixedWidth(80)
        btn_clear.setStyleSheet(f"font-size:10px;color:{COLOR['muted']};")
        btn_clear.clicked.connect(self._log_panel.clear)
        log_layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        root.addWidget(grp_log)

    # ── RDP selection ────────────────────────────────────────────────────────────────────────

    def _on_rdp_selected(self, level_id: int) -> None:
        warning = _RDP_WARNINGS.get(level_id)
        if warning is None:
            # Level 0 — no confirmation needed
            self._save_rdp_level(level_id)
            self.log(f"RDP level set to {level_id} (no protection).", "info")
            return

        title, text = warning
        reply = QMessageBox.warning(
            self, title, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._save_rdp_level(level_id)
            self.log(f"RDP level set to {level_id}.", "warn")
        else:
            # Revert radio button to previously saved level
            prev = self._config.get("rdp_level", 0)
            btn = self._rdp_group.button(prev)
            if btn:
                btn.setChecked(True)

    def _save_rdp_level(self, level: int) -> None:
        self._config["rdp_level"] = level
        _save_config(self._config)

    # ── public API ─────────────────────────────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        """Append a timestamped entry to the system log."""
        color = LEVEL_COLORS.get(level, COLOR["text"])
        ts    = _timestamp()
        self._log_panel.append(
            f'<span style="color:{COLOR["muted"]};">[{ts}]</span> '
            f'<span style="color:{color};">{message}</span>'
        )
        self._log_panel.moveCursor(QTextCursor.MoveOperation.End)

    def get_openocd_path(self) -> str:
        return self._ocd_input.text().strip()

    def set_openocd_path(self, path: str) -> None:
        self._ocd_input.setText(path)
        self._config["openocd_path"] = path
        _save_config(self._config)
        self.openocd_path_changed.emit(path)

    def get_password_hash(self) -> str:
        return self._config.get("password_hash", DEFAULT_PASSWORD_HASH)

    def password_is_empty(self) -> bool:
        """Returns True when the stored password hash represents an empty string."""
        return self._config.get("password_hash", "") == hashlib.sha256(b"").hexdigest()

    def get_rdp_level(self) -> int:
        return self._config.get("rdp_level", 0)

    def record_flash(self, success: bool) -> None:
        """Update and persist usage statistics, then refresh Flash tab cards."""
        self._stats["total"]  = self._stats.get("total", 0) + 1
        key = "success" if success else "failed"
        self._stats[key]      = self._stats.get(key, 0) + 1
        self._stats["last_flash"] = _timestamp()
        _save_stats(self._stats)
        self._main.refresh_stats(self._stats)

    # ── private actions ───────────────────────────────────────────────────────────────────────────

    def _save_openocd_path(self) -> None:
        path = self._ocd_input.text().strip()
        self._config["openocd_path"] = path
        _save_config(self._config)
        self.openocd_path_changed.emit(path)

    def _browse_openocd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Locate OpenOCD", "", "Executables (*)"
        )
        if path:
            self.set_openocd_path(path)
            self.log(f"OpenOCD path set manually: {path}", "info")

    def _auto_detect(self) -> None:
        path = shutil.which("openocd")
        if not path:
            candidates = [
                r"C:\Program Files\OpenOCD\bin\openocd.exe",
                r"C:\OpenOCD\bin\openocd.exe",
                r"C:\tools\OpenOCD\bin\openocd.exe",
                "/usr/bin/openocd",
                "/usr/local/bin/openocd",
                "/opt/homebrew/bin/openocd",
                "/opt/openocd/bin/openocd",
            ]
            for c in candidates:
                if Path(c).exists():
                    path = c
                    break
        if path:
            self.set_openocd_path(path)
            self.log(f"OpenOCD detected: {path}", "ok")
        else:
            self.log("OpenOCD not found in default locations.", "warn")

    def _change_password(self) -> None:
        new_pwd = self._pwd_new.text()
        confirm = self._pwd_confirm.text()
        if new_pwd != confirm:
            QMessageBox.warning(self, "Password", "Passwords do not match.")
            return
        # Empty password disables protection (hash of empty string stored)
        new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
        self._config["password_hash"] = new_hash
        _save_config(self._config)
        self._pwd_new.clear()
        self._pwd_confirm.clear()
        if new_pwd:
            self.log("Password changed successfully.", "ok")
            QMessageBox.information(self, "Password", "Password changed successfully.")
        else:
            self.log("Password protection disabled (empty password).", "warn")
            QMessageBox.information(
                self, "Password",
                "Password cleared. Settings tab is now unprotected."
            )


# ── module-level helpers ────────────────────────────────────────────────────────────────────────

def _lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:11px;min-width:90px;")
    return lbl
