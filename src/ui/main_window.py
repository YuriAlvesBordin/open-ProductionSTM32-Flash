from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QComboBox, QProgressBar,
    QMenuBar, QMenu,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from core.family_config import get_families, get_config
from core.flash_worker import FlashWorker
from ui.log_panel import LogPanel
from ui.settings_dialog import SettingsDialog


INTERFACE_MAP = {
    "ST-Link SWD": "config/interfaces/stlink_swd.cfg",
    "J-Link SWD": "config/interfaces/jlink_swd.cfg",
}

RDP_OPTIONS = [
    "Level 1 (0xBB) — Reversible",
    "Level 2 (0xCC) — IRREVERSIBLE",
]


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STM32 Production Flasher")
        self.setMinimumWidth(680)
        self._firmware_path = ""
        self._openocd_path = "openocd"
        self._worker: FlashWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 16, 20, 20)

        menu_bar = QMenuBar()
        tools_menu = QMenu("Tools", self)
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)
        menu_bar.addMenu(tools_menu)
        root.setMenuBar(menu_bar)

        firmware_row = QHBoxLayout()
        self._lbl_firmware = QLabel("No firmware selected")
        self._lbl_firmware.setStyleSheet("color: #797876;")
        btn_browse = QPushButton("Browse firmware...")
        btn_browse.clicked.connect(self._browse_firmware)
        firmware_row.addWidget(self._lbl_firmware, stretch=1)
        firmware_row.addWidget(btn_browse)
        root.addLayout(firmware_row)

        options_row = QHBoxLayout()

        family_col = QVBoxLayout()
        family_col.addWidget(QLabel("MCU Family"))
        self._combo_family = QComboBox()
        self._combo_family.addItems(get_families())
        family_col.addWidget(self._combo_family)

        iface_col = QVBoxLayout()
        iface_col.addWidget(QLabel("Interface"))
        self._combo_iface = QComboBox()
        self._combo_iface.addItems(list(INTERFACE_MAP.keys()))
        iface_col.addWidget(self._combo_iface)

        rdp_col = QVBoxLayout()
        rdp_col.addWidget(QLabel("RDP Level"))
        self._combo_rdp = QComboBox()
        self._combo_rdp.addItems(RDP_OPTIONS)
        rdp_col.addWidget(self._combo_rdp)

        options_row.addLayout(family_col)
        options_row.addLayout(iface_col)
        options_row.addLayout(rdp_col)
        root.addLayout(options_row)

        self._btn_flash = QPushButton("Flash + Lock")
        self._btn_flash.setMinimumHeight(44)
        self._btn_flash.setStyleSheet(
            "QPushButton { background-color: #01696f; color: white; "
            "border-radius: 6px; font-size: 15px; font-weight: 600; } "
            "QPushButton:hover { background-color: #0c4e54; } "
            "QPushButton:disabled { background-color: #393836; color: #5a5957; }"
        )
        self._btn_flash.clicked.connect(self._start_flash)
        root.addWidget(self._btn_flash)

        self._progress = QProgressBar()
        self._progress.setValue(0)
        root.addWidget(self._progress)

        self._log = LogPanel()
        self._log.setMinimumHeight(240)
        root.addWidget(self._log)

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "",
            "Firmware Files (*.bin *.hex *.elf)"
        )
        if path:
            self._firmware_path = path
            short = path.split("/")[-1]
            self._lbl_firmware.setText(short)
            self._lbl_firmware.setStyleSheet("color: #cdccca;")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._openocd_path, parent=self)
        if dialog.exec():
            self._openocd_path = dialog.openocd_path

    def _start_flash(self) -> None:
        if not self._firmware_path:
            self._log.append_line("WARNING: Select a firmware file first.")
            return

        family_label = self._combo_family.currentText()
        iface_label = self._combo_iface.currentText()
        rdp_label = self._combo_rdp.currentText()

        family_cfg = get_config(family_label)
        interface_cfg = INTERFACE_MAP[iface_label]

        self._btn_flash.setEnabled(False)
        self._progress.setValue(0)
        self._log.clear_log()

        self._worker = FlashWorker(
            firmware_path=self._firmware_path,
            interface_cfg=interface_cfg,
            family=family_cfg,
            rdp_label=rdp_label,
            openocd_path=self._openocd_path,
        )
        self._worker.log.connect(self._log.append_line)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool) -> None:
        self._btn_flash.setEnabled(True)
        if success:
            self._log.append_line("All steps completed successfully.")
        else:
            self._log.append_line("Process failed. Check the log above.")
