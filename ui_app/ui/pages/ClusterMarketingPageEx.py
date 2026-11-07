"""Xử lý giao diện Cluster Analysis & Marketing Action Center (Task 12).

Giao diện được tạo bởi pyuic6: ui/pages/ClusterMarketingPage.py (từ ClusterMarketingPage.ui).
Lớp Ex chỉ xử lý trạng thái widget, signal/slot và gọi service:
    get_cluster_profiles(), get_cluster_centroids(), get_segments(), get_marketing_actions(cluster),
    get_segment_customers(...), export_customers_csv(...)
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFileDialog, QHeaderView, QListWidgetItem, QMessageBox, QTableWidgetItem, QWidget

from app.widgets.charts import GroupedBarChart, MultiLineChart
from ui.pages.ClusterMarketingPage import Ui_ClusterMarketingPage
from ui.pages.SegmentationPageEx import describe_target

# (nhãn dòng, khóa trong profile, định dạng)
PROFILE_ROWS = [
    ("Customers", "customers", "{:,.0f}"),
    ("Share of customers", "customer_pct", "{:.1f}%"),
    ("Revenue (£)", "revenue", "{:,.0f}"),
    ("Share of revenue", "revenue_pct", "{:.1f}%"),
    ("Recency mean / median (days)", ("recency_mean", "recency_median"), "{:,.1f} / {:,.0f}"),
    ("Frequency mean / median", ("frequency_mean", "frequency_median"), "{:,.2f} / {:,.0f}"),
    ("Monetary mean / median (£)", ("monetary_mean", "monetary_median"), "{:,.0f} / {:,.0f}"),
    ("Average invoice value (£)", "avg_invoice_value", "{:,.2f}"),
    ("One-time buyers", "one_time_pct", "{:.1f}%"),
    ("Bought in last 30 days", "recency_le_30_pct", "{:.1f}%"),
    ("Inactive > 90 days", "recency_gt_90_pct", "{:.1f}%"),
    ("Inactive > 180 days", "recency_gt_180_pct", "{:.1f}%"),
    ("Median tenure (days)", "tenure_median", "{:,.0f}"),
    ("Mean silhouette", "silhouette_mean", "{:.3f}"),
]


class ClusterMarketingPageEx(QWidget, Ui_ClusterMarketingPage):
    # Phát ra khi bấm "View customers": (cluster, target filter, tên hành động)
    view_customers_requested = pyqtSignal(object, dict, str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setupUi(self)            # sinh bởi pyuic6
        self.setupControls()
        self.setupSignalAndSlot()
        self.load_analysis()
        self.load_segment_actions()

    # ---------------------------------------------------------------- setup
    def setupControls(self):
        self.profiles = sorted(self.service.get_cluster_profiles(), key=lambda p: p["segment_name_en"])
        self.segments = {s["cluster"]: s for s in self.service.get_segments()}

        self.shareChart = GroupedBarChart()
        self.hostShareChart.layout().addWidget(self.shareChart, 1)
        self.snakeChart = MultiLineChart()
        self.hostSnakeChart.layout().addWidget(self.snakeChart, 1)

        for p in self.profiles:
            self.cboActionSegment.addItem(p["segment_name_en"], p["cluster"])
        self.lstActions.setProperty("cssClass", "actionList")

    def setupSignalAndSlot(self):
        self.cboActionSegment.currentIndexChanged.connect(lambda _i: self.load_segment_actions())
        self.lstActions.currentRowChanged.connect(self.show_action)
        self.btnExportTarget.clicked.connect(self.export_target)
        self.btnViewTarget.clicked.connect(self.view_target)

    # ---------------------------------------------------------------- cluster analysis
    def load_analysis(self):
        total_inv = sum(p["invoices"] for p in self.profiles) or 1
        self.shareChart.set_data(
            ["Customers", "Invoices", "Revenue"],
            [(p["segment_name_en"],
              [p["customer_pct"], p["invoices"] / total_inv * 100, p["revenue_pct"]],
              p["color"]) for p in self.profiles],
            value_format="{:.1f}%", max_value=100)

        cent = self.service.get_cluster_centroids()
        self.snakeChart.set_data(
            cent["features"],
            [(p["segment_name_en"], cent["centroids"][p["cluster"]], p["color"]) for p in self.profiles])

        self._fill_profile_table()

    def _fill_profile_table(self):
        t = self.tblProfile
        t.setColumnCount(1 + len(self.profiles))
        t.setRowCount(len(PROFILE_ROWS))
        heads = ["Metric"] + [p['segment_name_en'].replace(' Customers', '')
                             for p in self.profiles]
        for c, text in enumerate(heads):
            item = QTableWidgetItem(text)
            item.setTextAlignment((Qt.AlignmentFlag.AlignLeft if c == 0 else Qt.AlignmentFlag.AlignRight)
                                  | Qt.AlignmentFlag.AlignVCenter)
            if c > 0:
                item.setForeground(QColor(self.profiles[c - 1]["color"]))
            t.setHorizontalHeaderItem(c, item)
        for r, (label, key, fmt) in enumerate(PROFILE_ROWS):
            t.setItem(r, 0, QTableWidgetItem(label))
            for c, p in enumerate(self.profiles, start=1):
                values = [p[k] for k in key] if isinstance(key, tuple) else [p[key]]
                item = QTableWidgetItem(fmt.format(*values))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(r, c, item)
        header = t.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(1, t.columnCount()):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setDefaultSectionSize(30)
        t.setWordWrap(False)

    # ---------------------------------------------------------------- marketing action center
    @property
    def cluster(self):
        return self.cboActionSegment.currentData()

    def load_segment_actions(self):
        seg = self.segments.get(self.cluster, {})
        self.lblSegmentStrategy.setText(f"Strategy: {seg.get('marketing_strategy', '')}")
        self.actions = self.service.get_marketing_actions(self.cluster)
        self.lstActions.clear()
        for i, action in enumerate(self.actions, start=1):
            count = self.service.get_segment_customers(cluster=self.cluster, page_size=1,
                                                       **action["target"])["total_rows"]
            action["count"] = count
            QListWidgetItem(f"{i}.  {action['title']}   ·   {count:,} customers", self.lstActions)
        if self.actions:
            self.lstActions.setCurrentRow(0)
        else:
            self.show_action(-1)

    def show_action(self, row):
        has = 0 <= row < len(self.actions)
        self.btnExportTarget.setEnabled(has)
        self.btnViewTarget.setEnabled(has)
        if not has:
            self.lblActionTitle.setText("No action selected")
            for lbl in (self.lblActionDescription, self.lblActionTarget, self.lblActionKpi):
                lbl.setText("")
            self.lblTargetCount.setText("0 customers")
            return
        a = self.actions[row]
        self.lblActionTitle.setText(a["title"])
        self.lblActionDescription.setText(a["description"])
        self.lblActionTarget.setText(f"<b>Target:</b> {describe_target(a['target'])}")
        self.lblActionKpi.setText(f"<b>KPI to track:</b> {a['kpi']}")
        self.lblTargetCount.setText(f"{a['count']:,} target customers")

    def _current_action(self):
        row = self.lstActions.currentRow()
        return self.actions[row] if 0 <= row < len(self.actions) else None

    def view_target(self):
        a = self._current_action()
        if a:
            self.view_customers_requested.emit(self.cluster, a["target"], a["title"])

    def export_target(self):
        a = self._current_action()
        if not a:
            return
        slug = "".join(ch if ch.isalnum() else "_" for ch in a["title"].lower()).strip("_")
        path, _ = QFileDialog.getSaveFileName(self, "Export target list",
                                              f"target_cluster_{self.cluster}_{slug}.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            count = self.service.export_customers_csv(path, cluster=self.cluster, sort_by="monetary_desc",
                                                      **a["target"])
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Export complete", f"Exported {count:,} customers to:\n{path}")
