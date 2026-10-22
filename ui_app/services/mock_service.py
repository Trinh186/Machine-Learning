"""
mock_service.py — DỮ LIỆU GIẢ để dựng giao diện khi chưa có MySQL / model thật.

Các con số được tính sẵn từ online_retail_II.xlsx (đã làm sạch cơ bản: bỏ Customer ID trống,
bỏ hóa đơn hủy 'C', Quantity > 0, Price > 0, bỏ dòng trùng) và một lần chạy thử
RFM → log1p → StandardScaler → K-Means (K = 2). Đây CHỈ là số mẫu để giao diện có dữ liệu,
không phải kết quả chính thức của nhóm.

>>> Khi các phần thật xong, tạo file services/db_service.py có ĐÚNG các hàm dưới đây
>>> (cùng tên, cùng tham số, cùng kiểu dữ liệu trả về), rồi đổi 1 dòng trong services/__init__.py.
"""

from datetime import datetime

# Tên phân khúc TẠM — thay bằng tên chính thức trong mục 3.5 của báo cáo.
_SEGMENTS = [
    {
        "cluster_id": 1,
        "segment_name": "High-Value Loyal",
        "customers": 2320,
        "avg_recency": 50.6,
        "avg_frequency": 12.7,
        "avg_monetary": 6547.0,
        "revenue": 15188971.2,
        "color": "#3B5BDB",
    },
    {
        "cluster_id": 0,
        "segment_name": "Low-Engagement",
        "customers": 3558,
        "avg_recency": 299.6,
        "avg_frequency": 2.1,
        "avg_monetary": 614.3,
        "revenue": 2185833.1,
        "color": "#F59F00",
    },
]

_MONTHLY = {
    "2009-12": 683504, "2010-01": 555803, "2010-02": 504559, "2010-03": 696978,
    "2010-04": 591982, "2010-05": 597833, "2010-06": 636371, "2010-07": 589736,
    "2010-08": 602225, "2010-09": 829014, "2010-10": 1033112, "2010-11": 1166460,
    "2010-12": 570423, "2011-01": 568101, "2011-02": 446085, "2011-03": 594082,
    "2011-04": 468374, "2011-05": 677355, "2011-06": 660046, "2011-07": 598963,
    "2011-08": 644051, "2011-09": 950690, "2011-10": 1035642, "2011-11": 1156206,
    "2011-12": 517208,
}


def get_dashboard_stats() -> dict:
    """Số liệu tổng quan cho 4 thẻ KPI trên Dashboard."""
    return {
        "total_customers": 5878,
        "total_invoices": 36969,
        "total_revenue": 17374804.27,       # đơn vị: GBP (£)
        "num_segments": len(_SEGMENTS),
        "date_from": datetime(2009, 12, 1),
        "date_to": datetime(2011, 12, 9),
    }


def get_monthly_revenue() -> list[tuple[str, float]]:
    """Doanh thu theo tháng: [("2009-12", 683504.0), ...], sắp xếp tăng dần theo tháng."""
    return [(month, float(value)) for month, value in _MONTHLY.items()]


def get_segment_summary() -> list[dict]:
    """
    Mỗi phần tử là 1 phân khúc:
      cluster_id, segment_name, customers, avg_recency (ngày), avg_frequency (số hóa đơn),
      avg_monetary (£), revenue (£), color (mã màu hex dùng chung cho mọi biểu đồ).
    """
    return [dict(s) for s in _SEGMENTS]
