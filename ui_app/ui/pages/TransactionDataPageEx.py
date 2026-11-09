"""Xử lý giao diện Transaction Data (Task 11).

Giao diện được tạo bởi pyuic6: ui/pages/TransactionDataPage.py (từ TransactionDataPage.ui).
Lớp Ex chỉ xử lý trạng thái widget, signal/slot và gọi service.get_transactions(...).
"""
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox, QWidget

from app.widgets.table_helpers import Pager, fill_table, setup_table
from ui.pages.TransactionDataPage import Ui_TransactionDataPage

HEADERS = ["Số hóa đơn", "Ngày lập", "Mã KH", "Quốc gia", "Mã hàng",
           "Mô tả", "Số lượng", "Đơn giá (£)", "Thành tiền (£)"]
NUMBER_COLS = (2, 6, 7, 8)
ALL_COUNTRIES = "Tất cả quốc gia"


class TransactionDataPageEx(QWidget, Ui_TransactionDataPage):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setupUi(self)          # sinh bởi pyuic6
        self.setupControls()
        self.setupSignalAndSlot()
        self.reset_filters()

    # ---------------------------------------------------------------- setup
    def setupControls(self):
        setup_table(self.tblTransactions, HEADERS, right_cols=NUMBER_COLS, stretch_col=5)

        self.cboCountry.addItem(ALL_COUNTRIES, None)
        for country in self.service.get_countries():
            self.cboCountry.addItem(country, country)

        stats = self.service.get_dashboard_stats()
        self._min_date = QDate(stats["date_from"].year, stats["date_from"].month, stats["date_from"].day)
        self._max_date = QDate(stats["date_to"].year, stats["date_to"].month, stats["date_to"].day)
        for widget in (self.dateFrom, self.dateTo):
            widget.setDateRange(self._min_date, self._max_date)

        self.pager = Pager(self.cboTransactionsPageSize, self.btnTransactionsPrevPage,
                           self.btnTransactionsNextPage, self.lblTransactionsPageInfo,
                           self.lblTransactionsSummary, unit="dòng giao dịch", parent=self)

    def setupSignalAndSlot(self):
        self.btnSearch.clicked.connect(self.search)
        self.btnReset.clicked.connect(self.reset_filters)
        self.txtSearch.returnPressed.connect(self.search)
        self.cboCountry.currentIndexChanged.connect(lambda _i: self.search())
        self.pager.page_changed.connect(self.load_page)

    # ---------------------------------------------------------------- actions
    def reset_filters(self):
        self.txtSearch.clear()
        self.cboCountry.blockSignals(True)
        self.cboCountry.setCurrentIndex(0)
        self.cboCountry.blockSignals(False)
        self.dateFrom.setDate(self._min_date)
        self.dateTo.setDate(self._max_date)
        self.search()

    def search(self):
        if self.dateFrom.date() > self.dateTo.date():
            QMessageBox.warning(self, "Khoảng ngày không hợp lệ", "'Từ ngày' phải trước hoặc bằng 'Đến ngày'.")
            return
        self.pager.reset()
        self.load_page()

    def load_page(self):
        result = self.service.get_transactions(
            keyword=self.txtSearch.text(),
            country=self.cboCountry.currentData(),
            date_from=self.dateFrom.date().toPyDate(),
            date_to=self.dateTo.date().toPyDate(),
            page=self.pager.page,
            page_size=self.pager.page_size,
        )
        rows = [[
            r["invoice_no"],
            r["invoice_date"].strftime("%d/%m/%Y %H:%M"),
            str(r["customer_id"]),
            r["country"],
            r["stock_code"],
            r["description"],
            f"{r['quantity']:,}",
            f"{r['unit_price']:,.2f}",
            f"{r['total_amount']:,.2f}",
        ] for r in result["rows"]]
        fill_table(self.tblTransactions, rows, right_cols=NUMBER_COLS)
        self.lblTotalAmount.setText(f"Tổng tiền: £{result['total_amount']:,.2f}")
        self.pager.update(result["total_rows"])
