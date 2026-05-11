import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar,
    QComboBox, QGroupBox, QFrame, QStatusBar,
    QMessageBox, QLineEdit,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from core.family_config import get_families, get_interfaces, get_config, get_interface_cfg
from core.flash_worker import FlashWorker
from ui.log_panel import LogPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STM32 Production Flasher")
        self.setMinimumSize(720, 600)
        self._firmware_path = ""
        self._worker: FlashWorker | None = None
        self._build_ui()
        self._detect_openocd()

    def _detect_openocd(self) -> None:
        path = shutil.which("openocd")
        if path:
            self._openocd_input.setText(path)
            self._log(f"OpenOCD detected at: {path}", "ok")
        else:
            self._log("OpenOCD not found in PATH. Enter the path manually.", "warn")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        title = QLabel("STM32 Production Flasher")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("Firmware flashing + RDP activation via OpenOCD")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ccc;")
        root.addWidget(sep)

        cfg_group = QGroupBox("Configuration")
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(8)

        ocd_row = QHBoxLayout()
        ocd_row.addWidget(QLabel("OpenOCD:"))
        self._openocd_input = QLineEdit()
        self._openocd_input.setPlaceholderText("Path to openocd executable")
        ocd_row.addWidget(self._openocd_input)
        btn_ocd = QPushButton("...")
        btn_ocd.setFixedWidth(36)
        btn_ocd.clicked.connect(self._browse_openocd)
        ocd_row.addWidget(btn_ocd)
        cfg_layout.addLayout(ocd_row)

        hw_row = QHBoxLayout()
        hw_row.addWidget(QLabel("Interface:"))
        self._combo_iface = QComboBox()
        self._combo_iface.addItems(get_interfaces())
        hw_row.addWidget(self._combo_iface)
        hw_row.addSpacing(16)
        hw_row.addWidget(QLabel("STM32 Family:"))
        self._combo_family = QComboBox()
        self._combo_family.addItems(get_families())
        hw_row.addWidget(self._combo_family)
        cfg_layout.addLayout(hw_row)

        fw_row = QHBoxLayout()
        fw_row.addWidget(QLabel("Firmware:"))
        self._lbl_firmware = QLabel("No file selected")
        self._lbl_firmware.setStyleSheet("color: #888; font-style: italic;")
        fw_row.addWidget(self._lbl_firmware, stretch=1)
        btn_fw = QPushButton("Select .bin / .hex / .elf")
        btn_fw.clicked.connect(self._browse_firmware)
        fw_row.addWidget(btn_fw)
        cfg_layout.addLayout(fw_row)

        root.addWidget(cfg_group)

        opt_group = QGroupBox("Options")
        opt_layout = QHBoxLayout(opt_group)
        self._btn_rdp = QPushButton("🔒  Enable RDP Level 1 after flashing")
        self._btn_rdp.setCheckable(True)
        self._btn_rdp.setChecked(True)
        self._btn_rdp.setStyleSheet("""
            QPushButton { background: #f0f0f0; border: 1px solid #ccc; border-radius: 6px; padding: 6px 14px; }
            QPushButton:checked { background: #d4edda; border-color: #28a745; color: #155724; font-weight: bold; }
        """)
        opt_layout.addWidget(self._btn_rdp)
        opt_layout.addStretch()
        root.addWidget(opt_group)

        self._btn_flash = QPushButton("▶  Flash + Lock")
        self._btn_flash.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._btn_flash.setMinimumHeight(48)
        self._btn_flash.setStyleSheet("""
            QPushButton { background: #01696f; color: white; border-radius: 8px; border: none; }
            QPushButton:hover   { background: #0c4e54; }
            QPushButton:pressed { background: #0f3638; }
            QPushButton:disabled { background: #aaa; color: #ddd; }
        """)
        self._btn_flash.clicked.connect(self._start_flash)
        root.addWidget(self._btn_flash)

        self._progress = QProgressBar()
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet("""
            QProgressBar { border: 1px solid #ccc; border-radius: 6px; height: 22px; text-align: center; }
            QProgressBar::chunk { background: #01696f; border-radius: 5px; }
        """)
        root.addWidget(self._progress)

        log_label = QLabel("Execution log:")
        log_label.setFont(QFont("Segoe UI", 9))
        root.addWidget(log_label)

        self._log_panel = LogPanel()
        root.addWidget(self._log_panel)

        btn_clear = QPushButton("Clear log")
        btn_clear.setFixedWidth(100)
        btn_clear.clicked.connect(self._log_panel.clear_log)
        root.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready.")

    def _browse_openocd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Locate OpenOCD", "", "Executables (*)")
        if path:
            self._openocd_input.setText(path)

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "",
            "Firmware (*.bin *.hex *.elf);;All files (*)"
        )
        if path:
            self._firmware_path = path
            self._lbl_firmware.setText(Path(path).name)
            self._lbl_firmware.setStyleSheet("color: #155724; font-style: normal; font-weight: bold;")
            self._log(f"Firmware selected: {path}", "info")

    def _log(self, message: str, level: str = "info") -> None:
        self._log_panel.append_line(message, level)

    def _start_flash(self) -> None:
        openocd = self._openocd_input.text().strip()
        if not openocd:
            QMessageBox.warning(self, "OpenOCD", "Enter the path to the OpenOCD executable.")
            return
        if not self._firmware_path:
            QMessageBox.warning(self, "Firmware", "Select a firmware file first.")
            return

        family_cfg   = get_config(self._combo_family.currentText())
        interface_cfg = get_interface_cfg(self._combo_iface.currentText())

        self._btn_flash.setEnabled(False)
        self._progress.setValue(0)
        self._status.showMessage("Flashing...")

        self._worker = FlashWorker(
            openocd_path  = openocd,
            firmware_path = self._firmware_path,
            interface_cfg = interface_cfg,
            family        = family_cfg,
            enable_rdp    = self._btn_rdp.isChecked(),
        )
        self._worker.log.connect(self._log)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool, message: str) -> None:
        self._btn_flash.setEnabled(True)
        if success:
            self._log(message, "ok")
            self._status.showMessage("Completed successfully.")
            QMessageBox.information(self, "Success", message)
        else:
            self._log(message, "error")
            self._status.showMessage("Process failed.")
            QMessageBox.critical(self, "Error", message)
