"""Legacy LogPanel — kept for backward compatibility.
New code should call SettingsTab.log() directly.
"""
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextCursor

LEVEL_COLORS = {
    "info":  "#9cdcfe",
    "ok":    "#3fb950",
    "warn":  "#d29922",
    "error": "#f85149",
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
            "background:#1c1c1c;color:#e8e8e8;"
            "border:1px solid #2a2a2a;border-radius:3px;"
        )
        self.setMinimumHeight(120)

    def append_line(self, message: str, level: str = "info") -> None:
        color = LEVEL_COLORS.get(level, "#e8e8e8")
        icon  = LEVEL_ICONS.get(level, "·")
        self.append(f'<span style="color:{color}">{icon} {message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self) -> None:
        self.clear()
