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
from app.theme import segment_label
from ui.pages.ClusterMarketingPage import Ui_ClusterMarketingPage
from ui.pages.SegmentationPageEx import describe_target

# (nhãn dòng, khóa trong profile, định dạng)
PROFILE_ROWS = [
    ("Khách hàng", "customers", "{:,.0f}"),
    ("Tỷ lệ khách hàng", "customer_pct", "{:.1f}%"),
    ("Doanh thu (£)", "revenue", "{:,.0f}"),
    ("Tỷ trọng doanh thu", "revenue_pct", "{:.1f}%"),
    ("Recency TB / trung vị (ngày)", ("recency_mean", "recency_median"), "{:,.1f} / {:,.0f}"),
    ("Frequency TB / trung vị", ("frequency_mean", "frequency_median"), "{:,.2f} / {:,.0f}"),
    ("Monetary TB / trung vị (£)", ("monetary_mean", "monetary_median"), "{:,.0f} / {:,.0f}"),
    ("Giá trị TB mỗi hóa đơn (£)", "avg_invoice_value", "{:,.2f}"),
    ("Khách mua 1 lần", "one_time_pct", "{:.1f}%"),
    ("Mua trong 30 ngày gần nhất", "recency_le_30_pct", "{:.1f}%"),
    ("Không mua > 90 ngày", "recency_gt_90_pct", "{:.1f}%"),
    ("Không mua > 180 ngày", "recency_gt_180_pct", "{:.1f}%"),
    ("Thâm niên trung vị (ngày)", "tenure_median", "{:,.0f}"),
    ("Silhouette trung bình", "silhouette_mean", "{:.3f}"),
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
            self.cboActionSegment.addItem(segment_label(p), p["cluster"])
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
            ["Khách hàng", "Hóa đơn", "Doanh thu"],
            [(segment_label(p, short=True),
              [p["customer_pct"], p["invoices"] / total_inv * 100, p["revenue_pct"]],
              p["color"]) for p in self.profiles],
            value_format="{:.1f}%", max_value=100)

        cent = self.service.get_cluster_centroids()
        self.snakeChart.set_data(
            cent["features"],
            [(segment_label(p, short=True), cent["centroids"][p["cluster"]], p["color"]) for p in self.profiles])

        self._fill_profile_table()

    def _fill_profile_table(self):
        t = self.tblProfile
        t.setColumnCount(1 + len(self.profiles))
        t.setRowCount(len(PROFILE_ROWS))
        heads = ["Chỉ số"] + [segment_label(p, short=True)
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
        self.lblSegmentStrategy.setText(f"Chiến lược: {seg.get('marketing_strategy', '')}")
        self.actions = self.service.get_marketing_actions(self.cluster)
        self.lstActions.clear()
        for i, action in enumerate(self.actions, start=1):
            count = self.service.get_segment_customers(cluster=self.cluster, page_size=1,
                                                       **action["target"])["total_rows"]
            action["count"] = count
            QListWidgetItem(f"{i}.  {action['title']}   ·   {count:,} khách hàng", self.lstActions)
        if self.actions:
            self.lstActions.setCurrentRow(0)
        else:
            self.show_action(-1)

    def show_action(self, row):
        has = 0 <= row < len(self.actions)
        self.btnExportTarget.setEnabled(has)
        self.btnViewTarget.setEnabled(has)
        if not has:
            self.lblActionTitle.setText("Chưa chọn hành động")
            for lbl in (self.lblActionDescription, self.lblActionTarget, self.lblActionKpi):
                lbl.setText("")
            self.lblTargetCount.setText("0 khách hàng")
            return
        a = self.actions[row]
        self.lblActionTitle.setText(a["title"])
        self.lblActionDescription.setText(a["description"])
        self.lblActionTarget.setText(f"<b>Đối tượng:</b> {describe_target(a['target'])}")
        self.lblActionKpi.setText(f"<b>KPI theo dõi:</b> {a['kpi']}")
        self.lblTargetCount.setText(f"{a['count']:,} khách hàng mục tiêu")

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
        path, _ = QFileDialog.getSaveFileName(self, "Xuất danh sách mục tiêu",
                                              f"target_cluster_{self.cluster}_{slug}.csv", "Tệp CSV (*.csv)")
        if not path:
            return
        try:
            count = self.service.export_customers_csv(path, cluster=self.cluster, sort_by="monetary_desc",
                                                      **a["target"])
        except OSError as exc:
            QMessageBox.warning(self, "Xuất tệp thất bại", str(exc))
            return
        QMessageBox.information(self, "Xuất tệp thành công", f"Đã xuất {count:,} khách hàng ra:\n{path}")
