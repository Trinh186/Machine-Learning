"""Thẻ phân khúc bấm được (trang Customer Segmentation). Số thẻ phụ thuộc K nên tạo bằng code."""

from PyQt6.QtCore import Qt, pyqtSignal

from app.theme import segment_label
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


def _money(v: float) -> str:
    return f"£{v / 1_000_000:,.2f}M" if v >= 1_000_000 else f"£{v:,.0f}"


class SegmentCard(QFrame):
    """
    clicked(cluster) phát ra khi bấm thẻ; cluster = None nghĩa là thẻ "All customers".
    profile: 1 phần tử của service.get_cluster_profiles() (hoặc dict tổng hợp cho "All customers").
    """
    clicked = pyqtSignal(object)

    def __init__(self, cluster, profile: dict, total_customers: int, total_revenue: float, parent=None):
        super().__init__(parent)
        self.cluster = cluster
        color = profile.get("color", "#A23E9C")
        self.setProperty("cssClass", "segmentCard")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"segmentCard{'All' if cluster is None else cluster}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(2)

        title = QLabel(f"●  {segment_label(profile)}")
        title.setProperty("cssClass", "segmentCardTitle")
        title.setStyleSheet(f"color: {color};")
        value = QLabel(f"{profile['customers']:,}")
        value.setProperty("cssClass", "kpiValue")
        share = profile["customers"] / total_customers if total_customers else 0
        rev_share = profile["revenue"] / total_revenue if total_revenue else 0
        line1 = QLabel(f"khách hàng · {share:.1%}")
        line1.setProperty("cssClass", "kpiTitle")
        line2 = QLabel(f"Doanh thu {_money(profile['revenue'])} · {rev_share:.1%} tổng")
        line2.setProperty("cssClass", "cardSubtitle")
        lay.addWidget(title)
        lay.addSpacing(4)
        lay.addWidget(value)
        lay.addWidget(line1)
        lay.addWidget(line2)
        if "recency_mean" in profile:
            line3 = QLabel(f"TB: R {profile['recency_mean']:.0f} ngày · F {profile['frequency_mean']:.1f}"
                           f" · M {_money(profile['monetary_mean'])}")
            line3.setProperty("cssClass", "kpiNote")
            lay.addWidget(line3)

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cluster)
        super().mouseReleaseEvent(event)
