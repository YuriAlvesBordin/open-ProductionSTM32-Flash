"""Settings tab — password-protected, timestamped logs, usage statistics."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ── paths ─────────────────────────────────────────────────────────────────────
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


# ── persistence helpers ───────────────────────────────────────────────────────

def _load_config() -> dict:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"password_hash": DEFAULT_PASSWORD_HASH, "openocd_path": ""}


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


# ── SettingsTab ───────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    """Password-protected settings panel with logs and usage statistics."""

    openocd_path_changed = pyqtSignal(str)

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self._main    = main_window
        self._config  = _load_config()
        self._stats   = _load_stats()
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── OpenOCD path ──
        grp_ocd = QGroupBox("OPENOCD")
        ocd_row = QHBoxLayout(grp_ocd)
        ocd_row.setSpacing(6)
        ocd_row.addWidget(self._label("Path:"))

        self._ocd_input = QLineEdit()
        self._ocd_input.setPlaceholderText("Path to openocd executable (auto-detection enabled)")
        self._ocd_input.setText(self._config.get("openocd_path", ""))
        self._ocd_input.editingFinished.connect(self._save_openocd_path)
        ocd_row.addWidget(self._ocd_input)

        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(32)
        btn_browse.clicked.connect(self._browse_openocd)
        ocd_row.addWidget(btn_browse)

        btn_detect = QPushButton("Auto")
        btn_detect.setFixedWidth(48)
        btn_detect.setToolTip("Auto-detect OpenOCD in default locations")
        btn_detect.clicked.connect(self._auto_detect)
        ocd_row.addWidget(btn_detect)

        root.addWidget(grp_ocd)

        # ── Password ──
        grp_pwd = QGroupBox("SECURITY")
        pwd_row = QHBoxLayout(grp_pwd)
        pwd_row.setSpacing(6)

        pwd_row.addWidget(self._label("New password:"))
        self._pwd_new = QLineEdit()
        self._pwd_new.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_new.setPlaceholderText("New password")
        self._pwd_new.setFixedWidth(150)
        pwd_row.addWidget(self._pwd_new)

        pwd_row.addWidget(self._label("Confirm:"))
        self._pwd_confirm = QLineEdit()
        self._pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_confirm.setPlaceholderText("Confirm password")
        self._pwd_confirm.setFixedWidth(150)
        pwd_row.addWidget(self._pwd_confirm)

        btn_save_pwd = QPushButton("Save")
        btn_save_pwd.setFixedWidth(64)
        btn_save_pwd.clicked.connect(self._change_password)
        pwd_row.addWidget(btn_save_pwd)
        pwd_row.addStretch()
        root.addWidget(grp_pwd)

        # ── Statistics ──
        grp_stats = QGroupBox("STATISTICS")
        stats_row = QHBoxLayout(grp_stats)
        stats_row.setSpacing(16)

        self._stat_total   = self._stat_card("Total",   "0")
        self._stat_success = self._stat_card("Success", "0", color=COLOR["ok"])
        self._stat_failed  = self._stat_card("Failed",  "0", color=COLOR["err"])
        self._stat_last    = self._stat_card("Last",    "—")

        for card, _ in (self._stat_total, self._stat_success,
                        self._stat_failed, self._stat_last):
            stats_row.addWidget(card)
        stats_row.addStretch()

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedWidth(56)
        btn_reset.setStyleSheet(
            f"color:{COLOR['err']};border-color:{COLOR['err']};font-size:10px;"
        )
        btn_reset.clicked.connect(self._reset_stats)
        stats_row.addWidget(btn_reset)
        root.addWidget(grp_stats)
        self._refresh_stats()

        # ── Lock button ──
        lock_row = QHBoxLayout()
        lock_row.addStretch()
        btn_lock = QPushButton("🔒  Lock")
        btn_lock.setFixedHeight(26)
        btn_lock.setStyleSheet(
            f"font-size:10px;color:{COLOR['muted']};border:1px solid {COLOR['border']};"
            f"border-radius:3px;background:transparent;padding:2px 8px;"
        )
        btn_lock.clicked.connect(self._lock)
        lock_row.addWidget(btn_lock)
        root.addLayout(lock_row)

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
        self._log_panel.setMinimumHeight(180)
        log_layout.addWidget(self._log_panel)

        btn_clear = QPushButton("Clear log")
        btn_clear.setFixedWidth(80)
        btn_clear.setStyleSheet(f"font-size:10px;color:{COLOR['muted']};")
        btn_clear.clicked.connect(self._log_panel.clear)
        log_layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        root.addWidget(grp_log)

    # ── stat card helper ──────────────────────────────────────────────────────

    def _stat_card(self, label: str, value: str, color: str = "") -> tuple:
        container = QWidget()
        container.setStyleSheet(
            f"background:{COLOR['surface2']};border:1px solid {COLOR['border']};"
            f"border-radius:3px;"
        )
        vl = QVBoxLayout(container)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        lbl_name = QLabel(label)
        lbl_name.setStyleSheet(
            f"color:{COLOR['muted']};font-size:9px;letter-spacing:1px;border:none;"
        )
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(
            f"color:{color if color else COLOR['text']};"
            f"font-size:18px;font-weight:bold;border:none;"
        )
        vl.addWidget(lbl_name)
        vl.addWidget(lbl_val)
        return (container, lbl_val)

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:11px;min-width:90px;")
        return lbl

    # ── public API ────────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        """Append a timestamped log line to the system log."""
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

    def record_flash(self, success: bool) -> None:
        """Increment usage counters and persist statistics."""
        self._stats["total"]   = self._stats.get("total", 0) + 1
        key = "success" if success else "failed"
        self._stats[key]       = self._stats.get(key, 0) + 1
        self._stats["last_flash"] = _timestamp()
        _save_stats(self._stats)
        self._refresh_stats()

    # ── private actions ───────────────────────────────────────────────────────

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
        import shutil
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
        if not new_pwd:
            QMessageBox.warning(self, "Password", "New password cannot be empty.")
            return
        if new_pwd != confirm:
            QMessageBox.warning(self, "Password", "Passwords do not match.")
            return
        self._config["password_hash"] = hashlib.sha256(new_pwd.encode()).hexdigest()
        _save_config(self._config)
        self._pwd_new.clear()
        self._pwd_confirm.clear()
        self.log("Password changed successfully.", "ok")
        QMessageBox.information(self, "Password", "Password changed successfully.")

    def _reset_stats(self) -> None:
        reply = QMessageBox.question(
            self, "Reset Statistics",
            "Reset all usage statistics?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._stats = {"total": 0, "success": 0, "failed": 0, "last_flash": None}
            _save_stats(self._stats)
            self._refresh_stats()
            self.log("Statistics reset.", "warn")

    def _lock(self) -> None:
        self._main.lock_settings()

    def _refresh_stats(self) -> None:
        self._stat_total[1].setText(str(self._stats.get("total", 0)))
        self._stat_success[1].setText(str(self._stats.get("success", 0)))
        self._stat_failed[1].setText(str(self._stats.get("failed", 0)))
        last = self._stats.get("last_flash") or "—"
        self._stat_last[1].setText(last)
        self._stat_last[1].setStyleSheet(
            f"color:{COLOR['muted']};font-size:11px;font-weight:normal;border:none;"
        )
