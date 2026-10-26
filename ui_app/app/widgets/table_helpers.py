"""Hàm/lớp dùng chung cho các trang có bảng: đổ dữ liệu vào QTableWidget và phân trang."""

from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


def setup_table(table: QTableWidget, headers: list[str], right_cols=(), stretch_col=None):
    """Đặt tiêu đề cột + căn lề. right_cols: các cột số (căn phải)."""
    table.setColumnCount(len(headers))
    for col, text in enumerate(headers):
        item = QTableWidgetItem(text)
        item.setTextAlignment(RIGHT if col in right_cols else LEFT)
        table.setHorizontalHeaderItem(col, item)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_col is not None:
        header.setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)
    header.setStretchLastSection(stretch_col is None)
    table.verticalHeader().setDefaultSectionSize(34)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)


def fill_table(table: QTableWidget, rows: list[list], right_cols=(), colors: dict | None = None,
               row_data: list | None = None):
    """
    rows     : danh sách dòng, mỗi dòng là list chuỗi đã định dạng
    colors   : {(row, col): "#hex"} để tô màu chữ một ô (vd. tên phân khúc)
    row_data : giá trị gắn vào cột 0 (Qt.UserRole) để lấy lại khi người dùng chọn dòng
    """
    table.setRowCount(len(rows))
    for r, values in enumerate(rows):
        for c, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setTextAlignment(RIGHT if c in right_cols else LEFT)
            if colors and (r, c) in colors:
                item.setForeground(QColor(colors[(r, c)]))
            if c == 0 and row_data is not None:
                item.setData(Qt.ItemDataRole.UserRole, row_data[r])
            table.setItem(r, c, item)
    table.scrollToTop()


class Pager(QObject):
    """
    Điều khiển phân trang gồm: combo số dòng/trang, nút Prev/Next, nhãn trang và nhãn tóm tắt.
    Phát tín hiệu page_changed khi người dùng đổi trang hoặc đổi số dòng/trang.
    """
    page_changed = pyqtSignal()

    def __init__(self, cbo_page_size, btn_prev, btn_next, lbl_page, lbl_summary,
                 sizes=(25, 50, 100), default=50, unit="rows", parent=None):
        super().__init__(parent)
        self.cbo, self.btn_prev, self.btn_next = cbo_page_size, btn_prev, btn_next
        self.lbl_page, self.lbl_summary, self.unit = lbl_page, lbl_summary, unit
        self.page, self.total = 1, 0
        for s in sizes:
            self.cbo.addItem(str(s), s)
        self.cbo.setCurrentIndex(sizes.index(default))
        self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.cbo.currentIndexChanged.connect(lambda _i: self._go(1))

    @property
    def page_size(self) -> int:
        return int(self.cbo.currentData())

    @property
    def page_count(self) -> int:
        return max(1, -(-self.total // self.page_size))

    def reset(self):
        self.page = 1

    def update(self, total: int, extra: str = ""):
        """Gọi sau mỗi lần nạp dữ liệu để cập nhật nhãn và trạng thái nút."""
        self.total = total
        first = 0 if total == 0 else (self.page - 1) * self.page_size + 1
        last = min(self.page * self.page_size, total)
        text = f"{first:,}–{last:,} of {total:,} {self.unit}"
        self.lbl_summary.setText(text + (f"  ·  {extra}" if extra else ""))
        self.lbl_page.setText(f"Page {self.page:,} / {self.page_count:,}")
        self.btn_prev.setEnabled(self.page > 1)
        self.btn_next.setEnabled(self.page < self.page_count)

    def _go(self, page: int):
        self.page = min(max(1, page), self.page_count) if self.total else 1
        self.page_changed.emit()
