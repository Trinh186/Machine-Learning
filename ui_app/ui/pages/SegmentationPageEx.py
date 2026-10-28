"""Xử lý giao diện Customer Segmentation (Task 12).

Giao diện được tạo bởi pyuic6: ui/pages/SegmentationPage.py (từ SegmentationPage.ui).
Lớp Ex chỉ xử lý trạng thái widget, signal/slot và gọi service:
    get_cluster_profiles(), get_customer_countries(), get_segment_customers(...), export_customers_csv(...)
"""
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.widgets.segment_card import SegmentCard
from app.widgets.table_helpers import Pager, fill_table, setup_table
from ui.pages.SegmentationPage import Ui_SegmentationPage

HEADERS = ["Customer ID", "Country", "Recency (days)", "Frequency", "Monetary (£)", "Segment"]
NUMBER_COLS = (2, 3, 4)
SORT_OPTIONS = [
    ("Sort: Customer ID", "customer_id"),
    ("Sort: Monetary (high → low)", "monetary_desc"),
    ("Sort: Frequency (high → low)", "frequency_desc"),
    ("Sort: Recency (most recent)", "recency_asc"),
    ("Sort: Recency (longest inactive)", "recency_desc"),
]


def describe_target(target: dict) -> str:
    """{'min_recency': 91, 'max_recency': 180} -> 'Recency 91–180 days'"""
    parts = []
    lo, hi = target.get("min_recency"), target.get("max_recency")
    if lo is not None and hi is not None:
        parts.append(f"Recency {lo}–{hi} days")
    elif lo is not None:
        parts.append(f"Recency ≥ {lo} days")
    elif hi is not None:
        parts.append(f"Recency ≤ {hi} days")
    lo, hi = target.get("min_frequency"), target.get("max_frequency")
    if lo is not None and hi is not None:
        parts.append(f"Frequency {lo}–{hi}")
    elif lo is not None:
        parts.append(f"Frequency ≥ {lo}")
    elif hi is not None:
        parts.append("one-time buyers" if hi == 1 else f"Frequency ≤ {hi}")
    return " · ".join(parts) or "All customers in the segment"


class SegmentationPageEx(QWidget, Ui_SegmentationPage):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.extra_filter = {}        # bộ lọc thêm từ Marketing Action Center (vd. Recency 91–180)
        self.setupUi(self)            # sinh bởi pyuic6
        self.setupControls()
        self.setupSignalAndSlot()
        self.reset_filters()

    # ---------------------------------------------------------------- setup
    def setupControls(self):
        profiles = self.service.get_cluster_profiles()
        self.colors = {p["cluster"]: p["color"] for p in profiles}
        total_c = sum(p["customers"] for p in profiles)
        total_r = sum(p["revenue"] for p in profiles)

        # Thẻ "All customers" + 1 thẻ cho mỗi phân khúc
        all_profile = {"segment_name_en": "All Customers", "segment_name": "Tất cả khách hàng",
                       "customers": total_c, "revenue": total_r, "color": "#A23E9C"}
        self.cards = [SegmentCard(None, all_profile, total_c, total_r)]
        self.cards += [SegmentCard(p["cluster"], p, total_c, total_r)
                       for p in sorted(profiles, key=lambda p: p["cluster"])]
        for card in self.cards:
            self.layoutSegmentCards.addWidget(card, 1)

        self.cboSegment.addItem("All segments", None)
        for p in sorted(profiles, key=lambda p: p["cluster"]):
            self.cboSegment.addItem(f"Cluster {p['cluster']} – {p['segment_name_en']}", p["cluster"])
        self.cboCountry.addItem("All countries", None)
        for country in self.service.get_customer_countries():
            self.cboCountry.addItem(country, country)
        for text, key in SORT_OPTIONS:
            self.cboSort.addItem(text, key)

        setup_table(self.tblCustomers, HEADERS, right_cols=NUMBER_COLS, stretch_col=5)
        self.pager = Pager(self.cboCustomersPageSize, self.btnCustomersPrevPage, self.btnCustomersNextPage,
                           self.lblCustomersPageInfo, self.lblCustomersSummary, unit="customers", parent=self)

    def setupSignalAndSlot(self):
        for card in self.cards:
            card.clicked.connect(self.select_segment)
        self.btnSearch.clicked.connect(self.search)
        self.btnReset.clicked.connect(self.reset_filters)
        self.txtCustomerSearch.returnPressed.connect(self.search)
        for combo in (self.cboSegment, self.cboCountry, self.cboSort):
            combo.currentIndexChanged.connect(lambda _i: self.search())
        self.btnClearActiveFilter.clicked.connect(self.clear_action_filter)
        self.btnExportCsv.clicked.connect(self.export_csv)
        self.pager.page_changed.connect(self.load_page)

    # ---------------------------------------------------------------- filters
    def _set_combo(self, combo, data):
        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(data)))
        combo.blockSignals(False)

    def current_filters(self) -> dict:
        return {
            "keyword": self.txtCustomerSearch.text(),
            "cluster": self.cboSegment.currentData(),
            "country": self.cboCountry.currentData(),
            "sort_by": self.cboSort.currentData(),
            **self.extra_filter,
        }

    def select_segment(self, cluster):
        """Bấm thẻ phân khúc → lọc theo phân khúc đó."""
        self._set_combo(self.cboSegment, cluster)
        self.search()

    def apply_action_target(self, cluster, target: dict, title: str = ""):
        """Gọi từ Marketing Action Center: lọc đúng nhóm khách của 1 hành động marketing."""
        self.extra_filter = dict(target)
        self._set_combo(self.cboSegment, cluster)
        label = describe_target(target)
        self.lblActiveFilter.setText(f"Action filter: {title} · {label}" if title else f"Action filter: {label}")
        self.search()

    def clear_action_filter(self):
        self.extra_filter = {}
        self.search()

    def reset_filters(self):
        self.extra_filter = {}
        self.txtCustomerSearch.clear()
        for combo in (self.cboSegment, self.cboCountry, self.cboSort):
            self._set_combo(combo, combo.itemData(0))
        self.search()

    def search(self):
        self.pager.reset()
        self.load_page()

    # ---------------------------------------------------------------- data
    def load_page(self):
        filters = self.current_filters()
        result = self.service.get_segment_customers(**filters, page=self.pager.page,
                                                    page_size=self.pager.page_size)
        rows, colors = [], {}
        for i, r in enumerate(result["rows"]):
            rows.append([
                str(r["customer_id"]),
                r["country"],
                f"{r['recency']:,}",
                f"{r['frequency']:,}",
                f"{r['monetary']:,.2f}",
                f"●  C{r['cluster']} · {r['segment_name_en']}",
            ])
            colors[(i, 5)] = self.colors.get(r["cluster"], "#2D1B36")
        fill_table(self.tblCustomers, rows, right_cols=NUMBER_COLS, colors=colors)
        self.lblTotalMonetary.setText(f"Total spend: £{result['total_monetary']:,.0f}")
        self.pager.update(result["total_rows"])

        has_action = bool(self.extra_filter)
        self.lblActiveFilter.setVisible(has_action)
        self.btnClearActiveFilter.setVisible(has_action)
        for card in self.cards:
            card.set_selected(card.cluster == filters["cluster"])
        self.btnExportCsv.setEnabled(result["total_rows"] > 0)

    def export_csv(self):
        filters = self.current_filters()
        cluster = filters["cluster"]
        default = "customers_all.csv" if cluster is None else f"customers_cluster_{cluster}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export customers", default, "CSV files (*.csv)")
        if not path:
            return
        try:
            count = self.service.export_customers_csv(path, **filters)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"Exported {count:,} customers to:\n{path}")
