"""Settings tab — password-protected, logs with timestamp, usage statistics.

This module is decoupled from the main window: it emits signals for any
data that other parts of the UI need to consume.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ─── paths ───────────────────────────────────────────────────────────────────

_CONFIG_DIR = Path.home() / ".stm32flash"
_CONFIG_FILE = _CONFIG_DIR / "settings.json"
_STATS_FILE = _CONFIG_DIR / "stats.json"

DEFAULT_PASSWORD_HASH = hashlib.sha256(b"123").hexdigest()

COLOR = {
    "bg":         "#0f0f0f",
    "surface":    "#161616",
    "surface2":   "#1c1c1c",
    "border":     "#2a2a2a",
    "text":       "#e8e8e8",
    "muted":      "#6a6a6a",
    "accent":     "#01696f",
    "accent_h":   "#0c4e54",
    "accent_p":   "#0f3638",
    "ok":         "#3fb950",
    "warn":       "#d29922",
    "err":        "#f85149",
    "disabled":   "#2e2e2e",
}

LEVEL_COLORS = {
    "info":  "#9cdcfe",
    "ok":    "#3fb950",
    "warn":  "#d29922",
    "error": "#f85149",
}


# ─── helpers ─────────────────────────────────────────────────────────────────

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
    return {"total": 0, "success": 0, "fail": 0, "last_flash": None}


def _save_stats(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _STATS_FILE.write_text(json.dumps(data, indent=2))


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── Settings Tab ────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    """Password-protected settings tab."""

    openocd_path_changed = pyqtSignal(str)

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        self._main = main_window
        self._config = _load_config()
        self._stats = _load_stats()
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── OpenOCD path ──
        grp_ocd = QGroupBox("OPENOCD")
        ocd_layout = QHBoxLayout(grp_ocd)
        ocd_layout.setSpacing(6)

        ocd_layout.addWidget(self._lbl("Caminho:"))
        self._ocd_input = QLineEdit()
        self._ocd_input.setPlaceholderText("Caminho para openocd (detecção automática habilitada)")
        self._ocd_input.setText(self._config.get("openocd_path", ""))
        self._ocd_input.editingFinished.connect(self._save_openocd_path)
        ocd_layout.addWidget(self._ocd_input)

        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(32)
        btn_browse.clicked.connect(self._browse_openocd)
        ocd_layout.addWidget(btn_browse)

        btn_detect = QPushButton("Auto")
        btn_detect.setFixedWidth(48)
        btn_detect.setToolTip("Detectar OpenOCD automaticamente")
        btn_detect.clicked.connect(self._auto_detect)
        ocd_layout.addWidget(btn_detect)

        root.addWidget(grp_ocd)

        # ── Password ──
        grp_pwd = QGroupBox("SEGURANÇA")
        pwd_layout = QHBoxLayout(grp_pwd)
        pwd_layout.setSpacing(6)

        pwd_layout.addWidget(self._lbl("Nova senha:"))
        self._pwd_new = QLineEdit()
        self._pwd_new.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_new.setPlaceholderText("Nova senha")
        self._pwd_new.setFixedWidth(150)
        pwd_layout.addWidget(self._pwd_new)

        pwd_layout.addWidget(self._lbl("Confirmar:"))
        self._pwd_confirm = QLineEdit()
        self._pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_confirm.setPlaceholderText("Confirmar senha")
        self._pwd_confirm.setFixedWidth(150)
        pwd_layout.addWidget(self._pwd_confirm)

        btn_change_pwd = QPushButton("Salvar Senha")
        btn_change_pwd.setFixedWidth(100)
        btn_change_pwd.clicked.connect(self._change_password)
        pwd_layout.addWidget(btn_change_pwd)
        pwd_layout.addStretch()

        root.addWidget(grp_pwd)

        # ── Statistics ──
        grp_stats = QGroupBox("ESTATÍSTICAS")
        stats_layout = QHBoxLayout(grp_stats)
        stats_layout.setSpacing(16)

        self._lbl_total = self._stat_widget("Total", "0")
        self._lbl_success = self._stat_widget("Sucesso", "0", color=COLOR['ok'])
        self._lbl_fail = self._stat_widget("Falhas", "0", color=COLOR['err'])
        self._lbl_last = self._stat_widget("Última", "—")

        stats_layout.addWidget(self._lbl_total[0])
        stats_layout.addWidget(self._lbl_success[0])
        stats_layout.addWidget(self._lbl_fail[0])
        stats_layout.addWidget(self._lbl_last[0])
        stats_layout.addStretch()

        btn_reset_stats = QPushButton("Zerar")
        btn_reset_stats.setFixedWidth(56)
        btn_reset_stats.setStyleSheet(
            f"color:{COLOR['err']};border-color:{COLOR['err']};font-size:10px;"
        )
        btn_reset_stats.clicked.connect(self._reset_stats)
        stats_layout.addWidget(btn_reset_stats)

        root.addWidget(grp_stats)
        self._refresh_stats_ui()

        # ── Lock + separator ──
        sep_row = QHBoxLayout()
        sep_row.addStretch()
        btn_lock = QPushButton("🔒  Bloquear")
        btn_lock.setFixedHeight(26)
        btn_lock.setStyleSheet(
            f"font-size:10px;color:{COLOR['muted']};border:1px solid {COLOR['border']};"
            f"border-radius:3px;background:transparent;padding:2px 8px;"
        )
        btn_lock.clicked.connect(self._lock)
        sep_row.addWidget(btn_lock)
        root.addLayout(sep_row)

        # ── Log panel ──
        grp_log = QGroupBox("LOG DO SISTEMA")
        log_layout = QVBoxLayout(grp_log)
        log_layout.setSpacing(4)

        self._log_panel = QTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setFont(QFont("Consolas", 9))
        self._log_panel.setStyleSheet(
            f"background:{COLOR['surface2']};color:{COLOR['text']};"
            f"border:1px solid {COLOR['border']};border-radius:3px;"
        )
        self._log_panel.setMinimumHeight(160)
        log_layout.addWidget(self._log_panel)

        btn_clear = QPushButton("Limpar log")
        btn_clear.setFixedWidth(90)
        btn_clear.setStyleSheet(f"font-size:10px;color:{COLOR['muted']};")
        btn_clear.clicked.connect(self._log_panel.clear)
        log_layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        root.addWidget(grp_log)

    # ── stat widget helper ────────────────────────────────────────────────────

    def _stat_widget(self, label: str, value: str, color: str = "") -> tuple:
        container = QWidget()
        container.setStyleSheet(
            f"background:{COLOR['surface2']};border:1px solid {COLOR['border']};"
            f"border-radius:3px;"
        )
        vl = QVBoxLayout(container)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        lbl_name = QLabel(label)
        lbl_name.setStyleSheet(f"color:{COLOR['muted']};font-size:9px;letter-spacing:1px;border:none;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(
            f"color:{color if color else COLOR['text']};font-size:18px;font-weight:bold;border:none;"
        )
        vl.addWidget(lbl_name)
        vl.addWidget(lbl_val)
        return (container, lbl_val)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:11px;min-width:70px;")
        return lbl

    # ── public API ────────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        """Append a timestamped log line."""
        color = LEVEL_COLORS.get(level, COLOR['text'])
        ts = _ts()
        self._log_panel.append(
            f'<span style="color:{COLOR[\'muted\']};">[{ts}]</span> '
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
        """Update usage statistics after a flash attempt."""
        self._stats["total"] = self._stats.get("total", 0) + 1
        if success:
            self._stats["success"] = self._stats.get("success", 0) + 1
        else:
            self._stats["fail"] = self._stats.get("fail", 0) + 1
        self._stats["last_flash"] = _ts()
        _save_stats(self._stats)
        self._refresh_stats_ui()

    # ── private actions ───────────────────────────────────────────────────────

    def _save_openocd_path(self) -> None:
        path = self._ocd_input.text().strip()
        self._config["openocd_path"] = path
        _save_config(self._config)
        self.openocd_path_changed.emit(path)

    def _browse_openocd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Localizar OpenOCD", "", "Executáveis (*)"
        )
        if path:
            self.set_openocd_path(path)
            self.log(f"OpenOCD configurado manualmente: {path}", "info")

    def _auto_detect(self) -> None:
        path = shutil.which("openocd")
        if not path:
            candidates = [
                r"C:\\Program Files\\OpenOCD\\bin\\openocd.exe",
                r"C:\\OpenOCD\\bin\\openocd.exe",
                r"C:\\tools\\OpenOCD\\bin\\openocd.exe",
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
            self.log(f"OpenOCD detectado: {path}", "ok")
        else:
            self.log("OpenOCD não encontrado nos caminhos padrão.", "warn")

    def _change_password(self) -> None:
        new_pwd = self._pwd_new.text()
        confirm = self._pwd_confirm.text()
        if not new_pwd:
            QMessageBox.warning(self, "Senha", "A nova senha não pode ser vazia.")
            return
        if new_pwd != confirm:
            QMessageBox.warning(self, "Senha", "As senhas não coincidem.")
            return
        new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
        self._config["password_hash"] = new_hash
        _save_config(self._config)
        self._pwd_new.clear()
        self._pwd_confirm.clear()
        self.log("Senha alterada com sucesso.", "ok")
        QMessageBox.information(self, "Senha", "Senha alterada com sucesso.")

    def _reset_stats(self) -> None:
        reply = QMessageBox.question(
            self, "Zerar estatísticas",
            "Deseja zerar todas as estatísticas de uso?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._stats = {"total": 0, "success": 0, "fail": 0, "last_flash": None}
            _save_stats(self._stats)
            self._refresh_stats_ui()
            self.log("Estatísticas zeradas.", "warn")

    def _lock(self) -> None:
        self._main.lock_settings()

    def _refresh_stats_ui(self) -> None:
        self._lbl_total[1].setText(str(self._stats.get("total", 0)))
        self._lbl_success[1].setText(str(self._stats.get("success", 0)))
        self._lbl_fail[1].setText(str(self._stats.get("fail", 0)))
        last = self._stats.get("last_flash") or "—"
        self._lbl_last[1].setText(last)
        self._lbl_last[1].setStyleSheet(
            f"color:{COLOR['muted']};font-size:11px;font-weight:normal;border:none;"
        )
