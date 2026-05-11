from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextCursor


LEVEL_COLORS = {
    "info":  "#9cdcfe",
    "ok":    "#4ec94e",
    "warn":  "#f0a500",
    "error": "#f44747",
}

LEVEL_ICONS = {
    "info":  "ℹ",
    "ok":    "✓",
    "warn":  "⚠",
    "error": "✗",
}


class LogPanel(QTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.setStyleSheet(
            "background: #1a1a2e; "
            "color: #e0e0e0; "
            "border-radius: 6px;"
        )
        self.setMinimumHeight(160)

    def append_line(self, message: str, level: str = "info") -> None:
        color = LEVEL_COLORS.get(level, "#e0e0e0")
        icon  = LEVEL_ICONS.get(level, "·")
        self.append(f'<span style="color:{color}">{icon} {message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self) -> None:
        self.clear()
