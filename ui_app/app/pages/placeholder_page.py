"""Trang tạm cho những màn hình chưa làm — sẽ thay bằng trang thật (Task 11, 12, 9)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str, note: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        box = QLabel(f"<b>{title}</b><br><span style='color:#7D6A84'>{note}</span>")
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setProperty("cssClass", "placeholder")
        layout.addWidget(box)
