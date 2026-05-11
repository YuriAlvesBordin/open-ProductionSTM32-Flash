"""Main application window.

Tabs: FLASH | SETTINGS
- Settings tab asks for password on every click (skipped when password is empty).
- RDP level selection lives in Settings.
- Usage statistics are displayed on the Flash tab.
- Auto-detect button probes the connected device for family + interface.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
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
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.device_detector import detect_device
from core.family_config import get_families, get_interfaces, get_config, get_interface_cfg
from core.flash_worker import FlashWorker
from ui.settings_tab import SettingsTab

# ── palette ───────────────────────────────────────────────────────────────────
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
QTabBar::tab:hover:!selected {{ color: {COLOR['text']}; }}
QGroupBox {{
    border: 1px solid {COLOR['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 10px;
    font-size: 10px;
    color: {COLOR['muted']};
    letter-spacing: 1px;
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
QLineEdit:focus {{ border-color: {COLOR['accent']}; }}
QComboBox {{
    background: {COLOR['surface2']};
    border: 1px solid {COLOR['border']};
    border-radius: 3px;
    padding: 5px 8px;
    color: {COLOR['text']};
    min-width: 120px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
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
QPushButton:hover {{ border-color: {COLOR['accent']}; }}
QPushButton:pressed {{ background: {COLOR['accent_p']}; }}
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
QProgressBar::chunk {{ background: {COLOR['accent']}; border-radius: 2px; }}
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


# ── detector thread ───────────────────────────────────────────────────────────

class _DetectorThread(QThread):
    progress  = pyqtSignal(str)          # status messages
    detected  = pyqtSignal(str, str, int)  # iface_label, family_label, idcode
    not_found = pyqtSignal()

    def __init__(self, openocd_path: str):
        super().__init__()
        self._openocd = openocd_path

    def run(self) -> None:
        result = detect_device(
            self._openocd,
            progress_cb=lambda msg: self.progress.emit(msg),
        )
        if result:
            self.detected.emit(
                result.interface_label,
                result.family_label,
                result.idcode,
            )
        else:
            self.not_found.emit()


# ── password-gate tab bar ───────────────────────────────────────────────────────

class _PasswordGateTabBar(QTabBar):
    SETTINGS_INDEX = 1

    def __init__(self, main_window: "MainWindow"):
        super().__init__()
        self._main = main_window

    def mousePressEvent(self, event) -> None:
        idx = self.tabAt(event.pos())
        if idx == self.SETTINGS_INDEX:
            if self._main._settings_tab.password_is_empty():
                super().mousePressEvent(event)
            else:
                dlg = PasswordDialog(
                    self._main,
                    stored_hash=self._main._settings_tab.get_password_hash(),
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self._main._settings_tab.log("Settings accessed.", "info")
                    super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)


# ── main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STM32 Flash")
        self.setMinimumSize(700, 560)
        self._firmware_path = ""
        self._worker: Optional[FlashWorker] = None
        self._detector: Optional[_DetectorThread] = None
        self.setStyleSheet(APP_STYLESHEET)
        self._build_ui()

    # ── construction ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet(
            f"background:{COLOR['surface2']};border-bottom:1px solid {COLOR['border']};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 12, 0)
        title_lbl = QLabel("STM32 FLASH")
        title_lbl.setStyleSheet(
            f"color:{COLOR['text']};font-size:13px;font-weight:bold;letter-spacing:2px;"
        )
        hl.addWidget(title_lbl)
        hl.addStretch()
        ver_lbl = QLabel("v2.0")
        ver_lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:10px;")
        hl.addWidget(ver_lbl)
        root.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabBar(_PasswordGateTabBar(self))
        root.addWidget(self._tabs)

        self._tab_flash = QWidget()
        self._build_flash_tab(self._tab_flash)
        self._tabs.addTab(self._tab_flash, "FLASH")

        self._settings_tab = SettingsTab(self)
        self._settings_tab.openocd_path_changed.connect(self._on_openocd_path_changed)
        self._tabs.addTab(self._settings_tab, "SETTINGS")

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
        hw_row.addWidget(_lbl("Interface"))
        self._combo_iface = QComboBox()
        self._combo_iface.addItems(get_interfaces())
        hw_row.addWidget(self._combo_iface)
        hw_row.addSpacing(12)
        hw_row.addWidget(_lbl("Family"))
        self._combo_family = QComboBox()
        self._combo_family.addItems(get_families())
        hw_row.addWidget(self._combo_family)
        hw_row.addSpacing(12)

        self._btn_detect_device = QPushButton("Detect Device")
        self._btn_detect_device.setFixedWidth(110)
        self._btn_detect_device.setToolTip(
            "Probe the connected device to auto-detect interface and MCU family"
        )
        self._btn_detect_device.clicked.connect(self._start_device_detect)
        hw_row.addWidget(self._btn_detect_device)
        hw_row.addStretch()
        tl.addLayout(hw_row)

        # Detection status label
        self._lbl_detect_status = QLabel("")
        self._lbl_detect_status.setStyleSheet(
            f"color:{COLOR['muted']};font-size:10px;font-style:italic;"
        )
        tl.addWidget(self._lbl_detect_status)

        layout.addWidget(grp_target)

        # ── Firmware group ──
        grp_fw = QGroupBox("FIRMWARE")
        fl = QHBoxLayout(grp_fw)
        fl.setSpacing(6)
        self._lbl_firmware = QLabel("No file selected")
        self._lbl_firmware.setStyleSheet(f"color:{COLOR['muted']};font-style:italic;")
        self._lbl_firmware.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        fl.addWidget(self._lbl_firmware)
        btn_fw = QPushButton("Browse")
        btn_fw.setFixedWidth(80)
        btn_fw.clicked.connect(self._browse_firmware)
        fl.addWidget(btn_fw)
        layout.addWidget(grp_fw)

        layout.addStretch(1)

        # ── Statistics ──
        grp_stats = QGroupBox("STATISTICS")
        stats_row = QHBoxLayout(grp_stats)
        stats_row.setSpacing(12)
        self._sc_total   = _stat_card("Total",   "0")
        self._sc_success = _stat_card("Success", "0", color=COLOR["ok"])
        self._sc_failed  = _stat_card("Failed",  "0", color=COLOR["err"])
        self._sc_last    = _stat_card("Last",    "-")
        for card, _ in (self._sc_total, self._sc_success,
                        self._sc_failed, self._sc_last):
            stats_row.addWidget(card)
        stats_row.addStretch()
        layout.addWidget(grp_stats)

        # ── Flash button ──
        self._btn_flash = QPushButton("\u25b6  FLASH")
        self._btn_flash.setMinimumHeight(40)
        self._btn_flash.setStyleSheet(
            f"""
            QPushButton {{
                background:{COLOR['accent']};
                border:none; border-radius:3px;
                color:#fff; font-size:13px; font-weight:bold; letter-spacing:1px;
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

    # ── device detection ───────────────────────────────────────────────────────

    def _start_device_detect(self) -> None:
        openocd = self._settings_tab.get_openocd_path().strip()
        if not openocd:
            QMessageBox.warning(
                self, "OpenOCD",
                "OpenOCD path is not configured.\nOpen Settings to set it first."
            )
            return
        self._btn_detect_device.setEnabled(False)
        self._btn_detect_device.setText("Detecting...")
        self._lbl_detect_status.setText("Scanning interfaces...")
        self._lbl_detect_status.setStyleSheet(
            f"color:{COLOR['muted']};font-size:10px;font-style:italic;"
        )
        self._settings_tab.log("Device detection started.", "info")

        self._detector = _DetectorThread(openocd)
        self._detector.progress.connect(
            lambda msg: self._lbl_detect_status.setText(msg)
        )
        self._detector.detected.connect(self._on_device_detected)
        self._detector.not_found.connect(self._on_device_not_found)
        self._detector.start()

    def _on_device_detected(self, iface: str, family: str, idcode: int) -> None:
        self._btn_detect_device.setEnabled(True)
        self._btn_detect_device.setText("Detect Device")

        # Update combo boxes
        iface_idx = self._combo_iface.findText(iface)
        if iface_idx >= 0:
            self._combo_iface.setCurrentIndex(iface_idx)

        family_idx = self._combo_family.findText(family)
        if family_idx >= 0:
            self._combo_family.setCurrentIndex(family_idx)

        msg = f"Detected: {iface} • {family} (IDCODE 0x{idcode:08X})"
        self._lbl_detect_status.setText(msg)
        self._lbl_detect_status.setStyleSheet(
            f"color:{COLOR['ok']};font-size:10px;font-style:normal;"
        )
        self._status.showMessage(msg)
        self._settings_tab.log(msg, "ok")

    def _on_device_not_found(self) -> None:
        self._btn_detect_device.setEnabled(True)
        self._btn_detect_device.setText("Detect Device")
        msg = "No device detected. Check connection and OpenOCD path."
        self._lbl_detect_status.setText(msg)
        self._lbl_detect_status.setStyleSheet(
            f"color:{COLOR['err']};font-size:10px;font-style:italic;"
        )
        self._status.showMessage("Detection failed.")
        self._settings_tab.log(msg, "warn")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _on_openocd_path_changed(self, path: str) -> None:
        self._status.showMessage(f"OpenOCD: {path}")

    def _auto_detect_openocd(self) -> None:
        path = shutil.which("openocd")
        if not path:
            for c in _OPENOCD_CANDIDATES:
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

    def refresh_stats(self, stats: dict) -> None:
        self._sc_total[1].setText(str(stats.get("total", 0)))
        self._sc_success[1].setText(str(stats.get("success", 0)))
        self._sc_failed[1].setText(str(stats.get("failed", 0)))
        last = stats.get("last_flash") or "-"
        self._sc_last[1].setText(last)
        self._sc_last[1].setStyleSheet(
            f"color:{COLOR['muted']};font-size:10px;font-weight:normal;border:none;"
        )

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

    # ── flash ────────────────────────────────────────────────────────────────

    def _start_flash(self) -> None:
        openocd = self._settings_tab.get_openocd_path().strip()
        if not openocd:
            QMessageBox.warning(
                self, "OpenOCD",
                "OpenOCD path is not configured.\nOpen Settings to set it."
            )
            return
        if not self._firmware_path:
            QMessageBox.warning(self, "Firmware", "Please select a firmware file first.")
            return

        family_cfg    = get_config(self._combo_family.currentText())
        interface_cfg = get_interface_cfg(self._combo_iface.currentText())
        rdp_level     = self._settings_tab.get_rdp_level()

        self._btn_flash.setEnabled(False)
        self._progress.setValue(0)
        self._status.showMessage("Flashing...")

        self._worker = FlashWorker(
            openocd_path=openocd,
            firmware_path=self._firmware_path,
            interface_cfg=interface_cfg,
            family=family_cfg,
            enable_rdp=rdp_level > 0,
        )
        self._worker.log.connect(lambda msg, lvl: self._settings_tab.log(msg, lvl))
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool, message: str) -> None:
        self._btn_flash.setEnabled(True)
        self._settings_tab.log(message, "ok" if success else "error")
        self._settings_tab.record_flash(success)
        if success:
            self._status.showMessage("Completed successfully.")
            self._progress.setValue(100)
        else:
            self._status.showMessage("Flash failed.")


# ── shared helpers ───────────────────────────────────────────────────────────

_OPENOCD_CANDIDATES = [
    r"C:\Program Files\OpenOCD\bin\openocd.exe",
    r"C:\OpenOCD\bin\openocd.exe",
    r"C:\tools\OpenOCD\bin\openocd.exe",
    "/usr/bin/openocd",
    "/usr/local/bin/openocd",
    "/opt/homebrew/bin/openocd",
    "/opt/openocd/bin/openocd",
]


def _lbl(text: str, muted: bool = False) -> QLabel:
    lbl = QLabel(text)
    if muted:
        lbl.setStyleSheet(f"color:{COLOR['muted']};font-size:11px;")
    return lbl


def _stat_card(label: str, value: str, color: str = "") -> tuple:
    container = QWidget()
    container.setStyleSheet(
        f"background:{COLOR['surface2']};border:1px solid {COLOR['border']};border-radius:3px;"
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
        f"color:{color if color else COLOR['text']};font-size:18px;font-weight:bold;border:none;"
    )
    vl.addWidget(lbl_name)
    vl.addWidget(lbl_val)
    return (container, lbl_val)


# ── password dialog ────────────────────────────────────────────────────────────

class PasswordDialog(QDialog):
    def __init__(self, parent, stored_hash: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Authentication Required")
        self.setFixedWidth(300)
        self._stored_hash = stored_hash
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
