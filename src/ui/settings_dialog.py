from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel,
)


class SettingsDialog(QDialog):
    def __init__(self, current_openocd_path: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._openocd_input = QLineEdit(current_openocd_path)
        form.addRow(QLabel("OpenOCD executable path:"), self._openocd_input)
        layout.addLayout(form)

        hint = QLabel(
            "Use 'openocd' if it is on your PATH, "
            "or provide the full absolute path."
        )
        hint.setStyleSheet("color: #797876; font-size: 12px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def openocd_path(self) -> str:
        return self._openocd_input.text().strip()
