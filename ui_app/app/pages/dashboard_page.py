"""Trang Dashboard: nạp giao diện từ ui/pages/dashboard.ui và đổ dữ liệu từ service."""

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QWidget

from app.paths import UI_DIR
from app.theme import segment_label
from app.widgets.charts import BarChart, DonutChart


class DashboardPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_DIR / "pages" / "dashboard.ui", self)
        self.service = service

        # Gắn biểu đồ vào các khung "host" đã đặt sẵn trong Qt Designer
        self.revenueChart = BarChart()
        self.hostRevenueChart.layout().addWidget(self.revenueChart)
        self.segmentChart = DonutChart()
        self.hostSegmentChart.layout().addWidget(self.segmentChart)

        self.refresh()

    def refresh(self):
        """Gọi lại khi dữ liệu thay đổi (vd. sau khi import dữ liệu mới)."""
        stats = self.service.get_dashboard_stats()
        segments = self.service.get_segment_summary()

        # --- 4 thẻ KPI ---
        self.lblKpiCustomersValue.setText(f"{stats['total_customers']:,}")
        # Thẻ đếm mọi khách có mua; vài khách bị loại khỏi RFM (tổng chi ≤ 0 sau khi trừ hàng trả lại)
        segmented = sum(s["customers"] for s in segments)
        self.lblKpiCustomersNote.setText(f"{segmented:,} khách được phân khúc RFM")
        self.lblKpiInvoicesValue.setText(f"{stats['total_invoices']:,}")
        self.lblKpiRevenueValue.setText(f"£{stats['total_revenue'] / 1_000_000:,.2f}M")
        self.lblKpiRevenueNote.setText(
            f"{stats['date_from']:%m/%Y} – {stats['date_to']:%m/%Y}")
        self.lblKpiSegmentsValue.setText(str(stats["num_segments"]))
        self.lblKpiSegmentsNote.setText(f"Phân cụm K-Means, K = {stats['num_segments']}")

        # --- biểu đồ ---
        monthly = self.service.get_monthly_revenue()
        self.revenueChart.set_data([self._month_label(m) for m, _ in monthly],
                                   [v for _, v in monthly])
        self.segmentChart.set_data(
            [(segment_label(s, short=True), s["customers"], s["color"]) for s in segments], "khách hàng")

        # --- bảng tóm tắt phân khúc ---
        self._fill_segment_table(segments)

    @staticmethod
    def _month_label(month: str) -> str:
        year, mon = month.split("-")
        return f"{mon}/{year[2:]}"

    def _fill_segment_table(self, segments):
        headers = ["Phân khúc", "Khách hàng", "Tỷ lệ", "Recency (ngày)",
                   "Frequency", "Monetary (£)", "Doanh thu (£)", "Tỷ trọng DT"]
        total_c = sum(s["customers"] for s in segments) or 1
        total_r = sum(s["revenue"] for s in segments) or 1

        t = self.tblSegmentSummary
        t.setColumnCount(len(headers))
        for col, text in enumerate(headers):
            head = QTableWidgetItem(text)
            align = Qt.AlignmentFlag.AlignLeft if col == 0 else Qt.AlignmentFlag.AlignRight
            head.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            t.setHorizontalHeaderItem(col, head)
        t.setRowCount(len(segments))
        for row, s in enumerate(segments):
            values = [
                f"●  {segment_label(s)}",
                f"{s['customers']:,}",
                f"{s['customers'] / total_c:.1%}",
                f"{s['avg_recency']:,.1f}",
                f"{s['avg_frequency']:,.1f}",
                f"{s['avg_monetary']:,.0f}",
                f"{s['revenue']:,.0f}",
                f"{s['revenue'] / total_r:.1%}",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setForeground(QColor(s["color"]))
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(row, col, item)

        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t.verticalHeader().setDefaultSectionSize(38)
        t.setFixedHeight(t.horizontalHeader().height() + 38 * len(segments) + 6)
