"""
Biểu đồ vẽ bằng QPainter — không cần cài thêm thư viện (QtCharts / matplotlib).
Cách dùng: tạo widget rồi gọi set_data(...); widget tự co giãn theo khung chứa.
"""

from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QToolTip, QWidget

TEXT_MUTED = QColor("#7D6A84")
TEXT_MAIN = QColor("#2D1B36")
GRID = QColor("#F5E8F1")
ACCENT = QColor("#A23E9C")
ACCENT_HOVER = QColor("#7E2E7E")


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
            if i == self._hover:
                p.setBrush(ACCENT_HOVER)
            else:
                grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                grad.setColorAt(0, QColor("#D0509E"))
                grad.setColorAt(1, QColor("#8E44B5"))
                p.setBrush(grad)
            p.drawRoundedRect(rect, 4, 4)

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


class LineChart(QWidget):
    """
    Biểu đồ đường có đánh dấu 1 điểm (vd. K được chọn).
    set_data(labels, values, highlight_index=None, value_format="{:,.0f}", color="#A23E9C")
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: list[str] = []
        self._values: list[float] = []
        self._highlight = None
        self._fmt = "{:,.0f}"
        self._color = ACCENT
        self.setMinimumHeight(180)

    def set_data(self, labels, values, highlight_index=None, value_format="{:,.0f}", color="#A23E9C"):
        self._labels = [str(x) for x in labels]
        self._values = [float(v) for v in values]
        self._highlight = highlight_index
        self._fmt = value_format
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        if len(self._values) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1.5))
        p.setFont(small)

        left, right, top, bottom = 52, 14, 22, 24
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        vmin, vmax = min(self._values), max(self._values)
        pad = (vmax - vmin) * 0.15 or abs(vmax) * 0.1 or 1
        lo, hi = vmin - pad, vmax + pad

        def pt(i, v):
            x = plot.left() + plot.width() * i / (len(self._values) - 1)
            y = plot.bottom() - plot.height() * (v - lo) / (hi - lo)
            return QPointF(x, y)

        # lưới + nhãn trục Y
        for i in range(4):
            v = lo + (hi - lo) * i / 3
            y = plot.bottom() - plot.height() * i / 3
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(0, y - 8, left - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._fmt.format(v))

        # đường + điểm
        pts = [pt(i, v) for i, v in enumerate(self._values)]
        p.setPen(QPen(self._color, 2.2))
        for a, b in zip(pts, pts[1:]):
            p.drawLine(a, b)
        for i, point in enumerate(pts):
            big = i == self._highlight
            p.setPen(QPen(QColor("#FFFFFF"), 2))
            p.setBrush(QColor("#E0559B") if big else self._color)
            r = 6.5 if big else 4
            p.drawEllipse(point, r, r)
            if big:
                p.setPen(QColor("#E0559B"))
                p.drawText(QRectF(point.x() - 60, point.y() - 24, 120, 16), Qt.AlignmentFlag.AlignCenter,
                           f"K = {self._labels[i]}: {self._fmt.format(self._values[i])}")

        # nhãn trục X
        p.setPen(TEXT_MUTED)
        for i, lab in enumerate(self._labels):
            x = pts[i].x()
            p.drawText(QRectF(x - 20, plot.bottom() + 6, 40, 16), Qt.AlignmentFlag.AlignCenter, lab)
        p.end()


def _legend(p: QPainter, items, x: float, y: float, font: QFont):
    """Vẽ chú thích ngang: ô màu + tên, bắt đầu từ (x, y)."""
    p.setFont(font)
    for name, color in items:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(x, y + 3, 10, 10), 2, 2)
        p.setPen(TEXT_MAIN)
        w = p.fontMetrics().horizontalAdvance(name) + 28
        p.drawText(QRectF(x + 16, y, w, 16), Qt.AlignmentFlag.AlignVCenter, name)
        x += w


class GroupedBarChart(QWidget):
    """
    Cột nhóm: mỗi nhóm (vd. Customers / Revenue / Invoices) có 1 cột cho mỗi series (phân khúc).
    set_data(groups, series=[(tên, [giá trị theo nhóm], "#màu")], value_format="{:.1f}%", max_value=100)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: list[str] = []
        self._series: list[tuple[str, list[float], QColor]] = []
        self._fmt = "{:.1f}%"
        self._max = None
        self.setMinimumHeight(200)

    def set_data(self, groups, series, value_format="{:.1f}%", max_value=None):
        self._groups = list(groups)
        self._series = [(n, [float(v) for v in vals], QColor(c)) for n, vals, c in series]
        self._fmt = value_format
        self._max = max_value
        self.update()

    def paintEvent(self, event):
        if not self._series:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1.5))

        left, right, top, bottom = 40, 8, 26, 24
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        vmax = self._max or max(max(v) for _, v, _ in self._series) * 1.15 or 1

        p.setFont(small)
        for i in range(5):
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(0, y - 8, left - 6, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       self._fmt.format(vmax * i / 4).replace(".0", ""))

        n_groups, n_series = len(self._groups), len(self._series)
        slot = plot.width() / n_groups
        bar_w = min(46.0, slot * 0.7 / n_series)
        for g, group in enumerate(self._groups):
            x0 = plot.left() + slot * g + (slot - bar_w * n_series - 6 * (n_series - 1)) / 2
            for s, (_, values, color) in enumerate(self._series):
                v = values[g]
                h = plot.height() * v / vmax
                rect = QRectF(x0 + s * (bar_w + 6), plot.bottom() - h, bar_w, h)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color)
                p.drawRoundedRect(rect, 3, 3)
                p.setPen(TEXT_MAIN)
                p.drawText(QRectF(rect.center().x() - 30, rect.top() - 16, 60, 14),
                           Qt.AlignmentFlag.AlignCenter, self._fmt.format(v))
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(plot.left() + slot * g, plot.bottom() + 6, slot, 16),
                       Qt.AlignmentFlag.AlignCenter, group)
        _legend(p, [(n, c) for n, _, c in self._series], left, 2, small)
        p.end()


class MultiLineChart(QWidget):
    """
    Nhiều đường trên cùng trục (vd. snake plot tâm cụm).
    set_data(labels, series=[(tên, [giá trị], "#màu")], value_format="{:+.2f}", zero_line=True)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: list[str] = []
        self._series: list[tuple[str, list[float], QColor]] = []
        self._fmt = "{:+.2f}"
        self._zero = True
        self.setMinimumHeight(200)

    def set_data(self, labels, series, value_format="{:+.2f}", zero_line=True):
        self._labels = [str(x) for x in labels]
        self._series = [(n, [float(v) for v in vals], QColor(c)) for n, vals, c in series]
        self._fmt = value_format
        self._zero = zero_line
        self.update()

    def paintEvent(self, event):
        if not self._series or len(self._labels) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1.5))

        left, right, top, bottom = 44, 40, 26, 24
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        values = [v for _, vals, _ in self._series for v in vals]
        lo, hi = min(values + [0]), max(values + [0])
        pad = (hi - lo) * 0.15 or 1
        lo, hi = lo - pad, hi + pad

        def pt(i, v):
            return QPointF(plot.left() + plot.width() * i / (len(self._labels) - 1),
                           plot.bottom() - plot.height() * (v - lo) / (hi - lo))

        p.setFont(small)
        for i in range(5):
            v = lo + (hi - lo) * i / 4
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_MUTED)
            p.drawText(QRectF(0, y - 8, left - 6, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{v:+.1f}")
        if self._zero:
            pen = QPen(QColor("#AD9AB2"), 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(pt(0, 0), QPointF(plot.right(), pt(0, 0).y()))

        for _, vals, color in self._series:
            pts = [pt(i, v) for i, v in enumerate(vals)]
            p.setPen(QPen(color, 2.4))
            for a, b in zip(pts, pts[1:]):
                p.drawLine(a, b)
            for point, v in zip(pts, vals):
                p.setPen(QPen(QColor("#FFFFFF"), 2))
                p.setBrush(color)
                p.drawEllipse(point, 5, 5)
                p.setPen(color)
                dy = -20 if v >= 0 else 6
                p.drawText(QRectF(point.x() + 6, point.y() + dy, 48, 14),
                           Qt.AlignmentFlag.AlignLeft, self._fmt.format(v))

        p.setPen(TEXT_MUTED)
        for i, lab in enumerate(self._labels):
            x = pt(i, 0).x()
            p.drawText(QRectF(x - 40, plot.bottom() + 6, 80, 16), Qt.AlignmentFlag.AlignCenter, lab)
        _legend(p, [(n, c) for n, _, c in self._series], left, 2, small)
        p.end()
