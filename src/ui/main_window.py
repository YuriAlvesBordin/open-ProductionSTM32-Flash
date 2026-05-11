"""Main application window — remastered UI.

Layout: two-tab design  (Flash | Settings)
Style:  dense, dark, minimalist.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.family_config import get_families, get_interfaces, get_config, get_interface_cfg
from core.flash_worker import FlashWorker
from ui.settings_tab import SettingsTab

# ── palette ──────────────────────────────────────────────────────────────────
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

APP_STYLESHEET = f"""
QWidget {{
    background: {COLOR['bg']};
    color: {COLOR['text']};
    font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
}}
QTabWidget::pane {{
    border: 1px solid {COLOR['border']};
    border-top: none;
    background: {COLOR['surface']};
}}
QTabBar::tab {{
    background: {COLOR['surface2']};
    color: {COLOR['muted']};
    border: 1px solid {COLOR['border']};
    border-bottom: none;
    padding: 6px 20px;
    margin-right: 2px;
    font-size: 11px;
    letter-spacing: 0.5px;
}}
QTabBar::tab:selected {{
    background: {COLOR['surface']};
    color: {COLOR['text']};
    border-bottom: 2px solid {COLOR['accent']};
}}
QTabBar::tab:hover:!selected {{
    color: {COLOR['text']};
}}
QGroupBox {{
    border: 1px solid {COLOR['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 10px;
    font-size: 10px;
    color: {COLOR['muted']};
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QLineEdit {{
    background: {COLOR['surface2']};
    border: 1px solid {COLOR['border']};
    border-radius: 3px;
    padding: 5px 8px;
    color: {COLOR['text']};
    selection-background-color: {COLOR['accent']};
}}
QLineEdit:focus {{
    border-color: {COLOR['accent']};
}}
QComboBox {{
    background: {COLOR['surface2']};
    border: 1px solid {COLOR['border']};
    border-radius: 3px;
    padding: 5px 8px;
    color: {COLOR['text']};
    min-width: 120px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {COLOR['surface2']};
    border: 1px solid {COLOR['border']};
    selection-background-color: {COLOR['accent']};
}}
QPushButton {{
    background: {COLOR['surface2']};
    border: 1px solid {COLOR['border']};
    border-radius: 3px;
    padding: 5px 12px;
    color: {COLOR['text']};
}}
QPushButton:hover {{
    border-color: {COLOR['accent']};
    color: {COLOR['text']};
}}
QPushButton:pressed {{
    background: {COLOR['accent_p']};
}}
QPushButton:disabled {{
    background: {COLOR['disabled']};
    color: {COLOR['muted']};
    border-color: {COLOR['border']};
}}
QProgressBar {{
    border: 1px solid {COLOR['border']};
    border-radius: 3px;
    background: {COLOR['surface2']};
    text-align: center;
    color: {COLOR['muted']};
    font-size: 10px;
    max-height: 14px;
}}
QProgressBar::chunk {{
    background: {COLOR['accent']};
    border-radius: 2px;
}}
QStatusBar {{
    background: {COLOR['surface2']};
    color: {COLOR['muted']};
    font-size: 10px;
    border-top: 1px solid {COLOR['border']};
}}
QScrollBar:vertical {{
    background: {COLOR['surface2']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR['border']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel {{ background: transparent; }}
"""

DEFAULT_PASSWORD_HASH = hashlib.sha256(b"123").hexdigest()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STM32 Flash")
        self.setMinimumSize(680, 520)
        self._firmware_path = ""
        self._worker: Optional[FlashWorker] = None
        self.setStyleSheet(APP_STYLESHEET)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet(
            f"background:{COLOR['surface2']};border-bottom:1px solid {COLOR['border']};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel("STM32 FLASH")
        lbl.setStyleSheet(
            f"color:{COLOR['text']};font-size:13px;font-weight:bold;letter-spacing:2px;"
        )
        hl.addWidget(lbl)
        hl.addStretch()
        ver = QLabel("v2.0")
        ver.setStyleSheet(f"color:{COLOR['muted']};font-size:10px;")
        hl.addWidget(ver)
        root.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs)

        self._tab_flash = QWidget()
        self._build_flash_tab(self._tab_flash)
        self._tabs.addTab(self._tab_flash, "FLASH")

        self._settings_tab = SettingsTab(self)
        self._settings_tab.openocd_path_changed.connect(self._on_openocd_path_changed)
        self._tabs.addTab(self._settings_tab, "SETTINGS  🔒")
        self._tabs.tabBar().setTabEnabled(1, False)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready.")

        self._auto_detect_openocd()

    def _build_flash_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Target group ──
        grp_target = QGroupBox("TARGET")
        tl = QVBoxLayout(grp_target)
        tl.setSpacing(6)

        hw_row = QHBoxLayout()
        hw_row.addWidget(self._lbl("Interface"))
        self._combo_iface = QComboBox()
        self._combo_iface.addItems(get_interfaces())
        hw_row.addWidget(self._combo_iface)
        hw_row.addSpacing(12)
        hw_row.addWidget(self._lbl("Family"))
        self._combo_family = QComboBox()
        self._combo_family.addItems(get_families())
        hw_row.addWidget(self._combo_family)
        hw_row.addStretch()
        tl.addLayout(hw_row)
        layout.addWidget(grp_target)

        # ── Firmware group ──
        grp_fw = QGroupBox("FIRMWARE")
        fl = QHBoxLayout(grp_fw)
        fl.setSpacing(6)
        self._lbl_firmware = QLabel("No file selected")
        self._lbl_firmware.setStyleSheet(f"color:{COLOR['muted']};font-style:italic;")
        self._lbl_firmware.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fl.addWidget(self._lbl_firmware)
        btn_fw = QPushButton("Browse")
        btn_fw.setFixedWidth(80)
        btn_fw.clicked.connect(self._browse_firmware)
        fl.addWidget(btn_fw)
        layout.addWidget(grp_fw)

        # ── Options ──
        grp_opts = QGroupBox("OPTIONS")
        ol = QHBoxLayout(grp_opts)
        self._btn_rdp = QPushButton("RDP Level 1")
        self._btn_rdp.setCheckable(True)
        self._btn_rdp.setChecked(True)
        self._btn_rdp.setFixedWidth(110)
        self._btn_rdp.setStyleSheet(
            f"""
            QPushButton {{
                background:{COLOR['surface2']};
                border:1px solid {COLOR['border']};
                border-radius:3px; padding:4px 10px;
                color:{COLOR['muted']};
            }}
            QPushButton:checked {{
                background:{COLOR['accent_p']};
                border-color:{COLOR['accent']};
                color:{COLOR['ok']};
                font-weight:bold;
            }}
            """
        )
        ol.addWidget(self._btn_rdp)
        ol.addWidget(self._lbl("Enable RDP after flashing", muted=True))
        ol.addStretch()
        layout.addWidget(grp_opts)

        layout.addStretch(1)

        # ── Flash button ──
        self._btn_flash = QPushButton("▶  FLASH")
        self._btn_flash.setMinimumHeight(40)
        self._btn_flash.setStyleSheet(
            f"""
            QPushButton {{
                background:{COLOR['accent']};
                border:none; border-radius:3px;
                color:#fff; font-size:13px; font-weight:bold;
                letter-spacing:1px;
            }}
            QPushButton:hover   {{ background:{COLOR['accent_h']}; }}
            QPushButton:pressed {{ background:{COLOR['accent_p']}; }}
            QPushButton:disabled {{ background:{COLOR['disabled']}; color:{COLOR['muted']}; }}
            """
        )
        self._btn_flash.clicked.connect(self._start_flash)
        layout.addWidget(self._btn_flash)

        # ── Progress ──
        self._progress = QProgressBar()
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # ── Settings unlock shortcut ──
        lock_row = QHBoxLayout()
        lock_row.addStretch()
        btn_unlock = QPushButton("🔓  Settings")
        btn_unlock.setFixedHeight(26)
        btn_unlock.setStyleSheet(
            f"font-size:10px;color:{COLOR['muted']};border:1px solid {COLOR['border']};"
            f"border-radius:3px;background:transparent;padding:2px 8px;"
        )
        btn_unlock.clicked.connect(self._request_unlock)
        lock_row.addWidget(btn_unlock)
        layout.addLayout(lock_row)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _lbl(text: str, muted: bool = False) -> QLabel:
        lbl = QLabel(text)
        if muted:
            lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:11px;")
        return lbl

    def _on_openocd_path_changed(self, path: str) -> None:
        self._status.showMessage(f"OpenOCD: {path}")

    def _auto_detect_openocd(self) -> None:
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
            self._settings_tab.set_openocd_path(path)
            self._settings_tab.log(f"OpenOCD auto-detected: {path}", "ok")
        else:
            self._settings_tab.log(
                "OpenOCD not found. Set the path manually in Settings.", "warn"
            )

    # ── settings lock / unlock ────────────────────────────────────────────────

    def _request_unlock(self) -> None:
        dlg = PasswordDialog(self, stored_hash=self._settings_tab.get_password_hash())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._tabs.tabBar().setTabEnabled(1, True)
            self._tabs.setCurrentIndex(1)
            self._tabs.setTabText(1, "SETTINGS")
            self._settings_tab.log("Settings unlocked.", "ok")

    def lock_settings(self) -> None:
        self._tabs.tabBar().setTabEnabled(1, False)
        self._tabs.setCurrentIndex(0)
        self._tabs.setTabText(1, "SETTINGS  🔒")
        self._settings_tab.log("Settings locked.", "info")

    # ── firmware ──────────────────────────────────────────────────────────────

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "",
            "Firmware (*.bin *.hex *.elf);;All files (*)"
        )
        if path:
            self._firmware_path = path
            self._lbl_firmware.setText(Path(path).name)
            self._lbl_firmware.setStyleSheet(
                f"color:{COLOR['ok']};font-style:normal;font-weight:bold;"
            )
            self._settings_tab.log(f"Firmware selected: {path}", "info")

    # ── flash ─────────────────────────────────────────────────────────────────

    def _start_flash(self) -> None:
        openocd = self._settings_tab.get_openocd_path().strip()
        if not openocd:
            QMessageBox.warning(self, "OpenOCD",
                                "OpenOCD path is not configured. Open Settings to set it.")
            return
        if not self._firmware_path:
            QMessageBox.warning(self, "Firmware", "Please select a firmware file first.")
            return

        family_cfg = get_config(self._combo_family.currentText())
        interface_cfg = get_interface_cfg(self._combo_iface.currentText())

        self._btn_flash.setEnabled(False)
        self._progress.setValue(0)
        self._status.showMessage("Flashing...")

        self._worker = FlashWorker(
            openocd_path=openocd,
            firmware_path=self._firmware_path,
            interface_cfg=interface_cfg,
            family=family_cfg,
            enable_rdp=self._btn_rdp.isChecked(),
        )
        self._worker.log.connect(self._on_flash_log)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_flash_log(self, message: str, level: str) -> None:
        self._settings_tab.log(message, level)

    def _on_finished(self, success: bool, message: str) -> None:
        self._btn_flash.setEnabled(True)
        self._settings_tab.log(message, "ok" if success else "error")
        self._settings_tab.record_flash(success)
        if success:
            self._status.showMessage("Completed successfully.")
            self._progress.setValue(100)
        else:
            self._status.showMessage("Flash failed.")


# ─── password dialog ──────────────────────────────────────────────────────────

class PasswordDialog(QDialog):
    """Simple password prompt to unlock the Settings tab."""

    def __init__(self, parent, stored_hash: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Authentication")
        self.setFixedWidth(300)
        self._stored_hash = stored_hash or hashlib.sha256(b"123").hexdigest()
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel("Password:"))
        self._pwd = QLineEdit()
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText("Enter password")
        layout.addWidget(self._pwd)

        self._err = QLabel("")
        self._err.setStyleSheet(f"color:{COLOR['err']};font-size:10px;")
        layout.addWidget(self._err)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._validate)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._pwd.returnPressed.connect(self._validate)

    def _validate(self) -> None:
        entered_hash = hashlib.sha256(self._pwd.text().encode()).hexdigest()
        if entered_hash == self._stored_hash:
            self.accept()
        else:
            self._err.setText("Incorrect password.")
            self._pwd.clear()
            self._pwd.setFocus()
