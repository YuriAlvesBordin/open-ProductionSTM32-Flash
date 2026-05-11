from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt


class LogPanel(QTextEdit):
    _COLOR_MAP = {
        "ERROR": "#e05c5c",
        "WARNING": "#e0a85c",
        "passed": "#6daa45",
        "activated": "#6daa45",
        "connected": "#6daa45",
        "written": "#6daa45",
    }
    _DEFAULT_COLOR = "#cdccca"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            "background-color: #1c1b19; "
            "color: #cdccca; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 13px; "
            "border: 1px solid #393836; "
            "border-radius: 6px; "
            "padding: 8px;"
        )

    def append_line(self, text: str) -> None:
        color = self._DEFAULT_COLOR
        for keyword, hex_color in self._COLOR_MAP.items():
            if keyword in text:
                color = hex_color
                break

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_log(self) -> None:
        self.clear()
