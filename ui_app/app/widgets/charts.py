"""
Biểu đồ vẽ bằng QPainter — không cần cài thêm thư viện (QtCharts / matplotlib).
Cách dùng: tạo widget rồi gọi set_data(...); widget tự co giãn theo khung chứa.
"""

from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

TEXT_MUTED = QColor("#6B7280")
TEXT_MAIN = QColor("#111827")
GRID = QColor("#EEF1F6")
ACCENT = QColor("#3B5BDB")
ACCENT_HOVER = QColor("#2B48C0")


def short_money(value: float) -> str:
    """17374804 -> '£17.4M', 683504 -> '£684K'."""
    if abs(value) >= 1_000_000:
        return f"£{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"£{value / 1_000:.0f}K"
    return f"£{value:.0f}"


class BarChart(QWidget):
    """Biểu đồ cột dọc. set_data(labels, values); hover vào cột để xem giá trị."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: list[str] = []
        self._values: list[float] = []
        self._bar_rects: list[QRectF] = []
        self._hover = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(200)

    def set_data(self, labels, values):
        self._labels = list(labels)
        self._values = [float(v) for v in values]
        self.update()

    # ---- vẽ ----
    def paintEvent(self, event):
        if not self._values:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1.5))
        p.setFont(small)

        left, right, top, bottom = 52, 8, 8, 26
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        vmax = max(self._values) * 1.12 or 1

        # lưới ngang + nhãn trục Y
        steps = 4
        for i in range(steps + 1):
            y = plot.bottom() - plot.height() * i / steps
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(0, y - 8, left - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       short_money(vmax * i / steps))

        # cột
        n = len(self._values)
        slot = plot.width() / n
        bar_w = max(4.0, slot * 0.62)
        self._bar_rects = []
        for i, v in enumerate(self._values):
            h = plot.height() * v / vmax
            rect = QRectF(plot.left() + slot * i + (slot - bar_w) / 2, plot.bottom() - h, bar_w, h)
            self._bar_rects.append(rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACCENT_HOVER if i == self._hover else ACCENT)
            p.drawRoundedRect(rect, 3, 3)

        # nhãn trục X: hiển thị thưa để không chồng chữ
        every = max(1, round(n / max(1, plot.width() // 70)))
        p.setPen(TEXT_MUTED)
        for i, lab in enumerate(self._labels):
            if i % every:
                continue
            cx = plot.left() + slot * i + slot / 2
            p.drawText(QRectF(cx - 35, plot.bottom() + 6, 70, 16), Qt.AlignmentFlag.AlignCenter, lab)
        p.end()

    # ---- tooltip khi rê chuột ----
    def mouseMoveEvent(self, event):
        pos = event.position()
        idx = next((i for i, r in enumerate(self._bar_rects)
                    if r.left() <= pos.x() <= r.right()), -1)
        if idx != self._hover:
            self._hover = idx
            self.update()
        if idx >= 0:
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{self._labels[idx]}: £{self._values[idx]:,.0f}", self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event):
        self._hover = -1
        self.update()


class DonutChart(QWidget):
    """Biểu đồ vành khuyên + chú thích. set_data([(nhãn, giá trị, '#màu'), ...], center_caption)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, float, QColor]] = []
        self._caption = ""
        self.setMinimumHeight(200)

    def set_data(self, items, center_caption="customers"):
        self._items = [(lab, float(v), QColor(c)) for lab, v, c in items]
        self._caption = center_caption
        self.update()

    def paintEvent(self, event):
        total = sum(v for _, v, _ in self._items)
        if not total:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        legend_h = 22 * len(self._items) + 6
        size = min(self.width(), self.height() - legend_h) - 8
        ring = max(14.0, size * 0.16)
        rect = QRectF((self.width() - size) / 2 + ring / 2, ring / 2 + 2, size - ring, size - ring)

        # các cung
        start = 90 * 16
        for _, v, color in self._items:
            span = -int(round(360 * 16 * v / total))
            pen = QPen(color, ring)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, start, span)
            start += span

        # chữ ở giữa
        big = QFont(self.font())
        big.setPointSizeF(self.font().pointSizeF() + 6)
        big.setBold(True)
        p.setFont(big)
        p.setPen(TEXT_MAIN)
        p.drawText(rect.adjusted(0, -10, 0, -10), Qt.AlignmentFlag.AlignCenter, f"{total:,.0f}")
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1))
        p.setFont(small)
        p.setPen(TEXT_MUTED)
        p.drawText(rect.adjusted(0, 26, 0, 26), Qt.AlignmentFlag.AlignCenter, self._caption)

        # chú thích
        y = size + 10
        for lab, v, color in self._items:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(8, y + 4, 10, 10), 2, 2)
            p.setPen(TEXT_MAIN)
            p.drawText(QRectF(26, y, self.width() - 90, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lab)
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(self.width() - 80, y, 72, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{v / total:.1%}")
            y += 22
        p.end()
