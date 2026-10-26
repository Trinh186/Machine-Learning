"""
mock_service.py — DỮ LIỆU GIẢ để dựng và chạy thử giao diện khi chưa có MySQL / model thật.

Nguồn số liệu (để giao diện khớp báo cáo):
  - datasets/processed/Online Retail_cleaned.xlsx  (mục 3.2) → thống kê Dashboard, 4.000 dòng giao dịch mẫu
  - RFM theo công thức mục 3.3.1 (Reference Date 2011-12-10) → mock_data/rfm_customers.csv
  - K-Means K = 2 (log1p + StandardScaler, n_init = 10, random_state = 42) như mục 3.4–3.5
    → tham số scaler + tâm cụm trong mock_data/model_params.json
    (kết quả khớp outputs/cluster_profile.csv và cluster_metrics.csv)

>>> Khi phần thật xong, tạo services/db_service.py có ĐÚNG các hàm dưới đây
>>> (cùng tên, cùng tham số, cùng kiểu trả về) rồi đổi 1 dòng import trong services/__init__.py.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "mock_data"

# Giống bảng `segments` trong customer_segmentation/database/database.sql
_SEGMENTS = [
    {
        "cluster": 0,
        "segment_name": "Khách hàng giá trị cao",
        "segment_name_en": "High-Value Customers",
        "description": "Mua gần đây (Recency TB 26,45 ngày), mua thường xuyên (Frequency TB 8,44 hóa đơn), "
                       "chi tiêu cao (Monetary TB £4.535,74). Chiếm 38,45% khách hàng nhưng 85,13% doanh thu.",
        "marketing_strategy": "Ưu tiên chăm sóc; chương trình khách hàng thân thiết/VIP và ưu đãi cá nhân hóa "
                              "phù hợp với giá trị mua hàng.",
        "color": "#1B7A4E",
    },
    {
        "cluster": 1,
        "segment_name": "Khách hàng ít hoạt động",
        "segment_name_en": "Low-Activity Customers",
        "description": "Lâu chưa quay lại (Recency TB 134,67 ngày), mua ít (Frequency TB 1,67 hóa đơn), "
                       "chi tiêu thấp (Monetary TB £494,98). Chiếm 61,55% khách hàng, 14,87% doanh thu.",
        "marketing_strategy": "Thử nghiệm chiến dịch kích hoạt lại, voucher quay lại và nhắc mua hàng; "
                              "đánh giá hiệu quả theo phản hồi thực tế.",
        "color": "#767676",
    },
]
_SEGMENT_BY_CLUSTER = {s["cluster"]: s for s in _SEGMENTS}

# Bảng 3.5.1 – cluster_metrics.csv
_MODEL_METRICS = {
    "k": 2,
    "silhouette": 0.4325,
    "davies_bouldin": 0.8913,
    "calinski_harabasz": 4376.83,
    "inertia": 6476.51,
}

_MONTHLY = {
    "2010-12": 570423, "2011-01": 568101, "2011-02": 446085, "2011-03": 594082,
    "2011-04": 468374, "2011-05": 677355, "2011-06": 660046, "2011-07": 598963,
    "2011-08": 644051, "2011-09": 950690, "2011-10": 1035642, "2011-11": 1156206,
    "2011-12": 517190,
}


# ----------------------------------------------------------------------------
# Đọc file mock (chỉ đọc 1 lần)
# ----------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _transactions() -> list[dict]:
    with open(_DATA_DIR / "transactions_sample.csv", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append({
                "invoice_no": r["invoice_no"],
                "invoice_date": datetime.fromisoformat(r["invoice_date"]),
                "customer_id": int(r["customer_id"]),
                "country": r["country"],
                "stock_code": r["stock_code"],
                "description": r["description"],
                "quantity": int(r["quantity"]),
                "unit_price": float(r["unit_price"]),
                "total_amount": float(r["total_amount"]),
            })
    return rows


@lru_cache(maxsize=None)
def _rfm() -> list[dict]:
    with open(_DATA_DIR / "rfm_customers.csv", encoding="utf-8") as f:
        return [{
            "customer_id": int(r["customer_id"]),
            "recency": int(r["recency"]),
            "frequency": int(r["frequency"]),
            "monetary": float(r["monetary"]),
            "cluster": int(r["cluster"]),
        } for r in csv.DictReader(f)]


@lru_cache(maxsize=None)
def _model_params() -> dict:
    return json.loads((_DATA_DIR / "model_params.json").read_text(encoding="utf-8"))


def _paginate(rows: list, page: int, page_size: int) -> tuple[list, int]:
    page = max(1, int(page))
    start = (page - 1) * page_size
    return rows[start:start + page_size], len(rows)


# ----------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------
def get_dashboard_stats() -> dict:
    """Số liệu tổng quan cho 4 thẻ KPI trên Dashboard."""
    return {
        "total_customers": 4338,
        "total_invoices": 18532,
        "total_revenue": 8887208.89,         # GBP (£)
        "num_segments": len(_SEGMENTS),
        "date_from": datetime(2010, 12, 1, 8, 26),
        "date_to": datetime(2011, 12, 9, 12, 50),
    }


def get_monthly_revenue() -> list[tuple[str, float]]:
    """Doanh thu theo tháng: [("2010-12", 570423.0), ...], tăng dần theo tháng."""
    return [(m, float(v)) for m, v in _MONTHLY.items()]


def get_segment_summary() -> list[dict]:
    """Mỗi phân khúc: cluster, segment_name, segment_name_en, customers, avg_recency,
    avg_frequency, avg_monetary, revenue, color."""
    out = []
    for seg in _SEGMENTS:
        members = [r for r in _rfm() if r["cluster"] == seg["cluster"]]
        n = len(members)
        out.append({
            "cluster": seg["cluster"],
            "segment_name": seg["segment_name"],
            "segment_name_en": seg["segment_name_en"],
            "customers": n,
            "avg_recency": sum(r["recency"] for r in members) / n,
            "avg_frequency": sum(r["frequency"] for r in members) / n,
            "avg_monetary": sum(r["monetary"] for r in members) / n,
            "revenue": sum(r["monetary"] for r in members),
            "color": seg["color"],
        })
    return out


# ----------------------------------------------------------------------------
# TRANSACTION DATA
# ----------------------------------------------------------------------------
def get_countries() -> list[str]:
    """Danh sách quốc gia (để đổ vào ô lọc), sắp xếp A–Z."""
    return sorted({r["country"] for r in _transactions()})


def get_transactions(keyword: str = "", country: str | None = None,
                     date_from: date | None = None, date_to: date | None = None,
                     page: int = 1, page_size: int = 50) -> dict:
    """
    Tìm kiếm / lọc dòng giao dịch, mới nhất trước.
      keyword   : tìm trong invoice_no, customer_id, stock_code, description (không phân biệt hoa thường)
      country   : None = tất cả
      date_from / date_to : lọc theo ngày (tính cả 2 đầu)
    Trả về: {"rows": [dict, ...], "total_rows": int, "total_amount": float}
      mỗi row: invoice_no, invoice_date (datetime), customer_id, country, stock_code,
               description, quantity, unit_price, total_amount
    """
    kw = (keyword or "").strip().lower()
    rows = []
    for r in _transactions():
        if country and r["country"] != country:
            continue
        d = r["invoice_date"].date()
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue
        if kw and not (kw in r["invoice_no"].lower() or kw in str(r["customer_id"])
                       or kw in r["stock_code"].lower() or kw in r["description"].lower()):
            continue
        rows.append(r)
    total_amount = sum(r["total_amount"] for r in rows)
    page_rows, total = _paginate(rows, page, page_size)
    return {"rows": page_rows, "total_rows": total, "total_amount": total_amount}


# ----------------------------------------------------------------------------
# RFM & MODEL
# ----------------------------------------------------------------------------
def get_segments() -> list[dict]:
    """Bảng segments: cluster, segment_name, segment_name_en, description, marketing_strategy, color."""
    return [dict(s) for s in _SEGMENTS]


def get_model_info() -> dict:
    """
    Thông tin mô hình K-Means đang dùng:
      k, silhouette, davies_bouldin, calinski_harabasz, inertia, n_customers, reference_date (date),
      k_search: [{"k": 2, "inertia": ..., "silhouette": ...}, ...]  (cho biểu đồ Elbow / Silhouette)
    """
    p = _model_params()
    return {
        **_MODEL_METRICS,
        "n_customers": len(_rfm()),
        "reference_date": date.fromisoformat(p["reference_date"]),
        "k_search": p["k_search"],
    }


def get_rfm_table(keyword: str = "", cluster: int | None = None,
                  page: int = 1, page_size: int = 50) -> dict:
    """
    RFM của từng khách hàng + phân khúc.
    Trả về: {"rows": [{customer_id, recency, frequency, monetary, cluster,
                       segment_name, segment_name_en}], "total_rows": int}
    """
    kw = (keyword or "").strip()
    rows = []
    for r in _rfm():
        if cluster is not None and r["cluster"] != cluster:
            continue
        if kw and kw not in str(r["customer_id"]):
            continue
        seg = _SEGMENT_BY_CLUSTER[r["cluster"]]
        rows.append({**r, "segment_name": seg["segment_name"], "segment_name_en": seg["segment_name_en"]})
    page_rows, total = _paginate(rows, page, page_size)
    return {"rows": page_rows, "total_rows": total}


def predict_segment(recency: float, frequency: float, monetary: float) -> dict:
    """
    Dự đoán phân khúc cho 1 bộ RFM mới: RFM → log1p → StandardScaler → K-Means (tâm cụm gần nhất).
    Báo ValueError nếu dữ liệu không hợp lệ (giống ràng buộc bảng rfm_profiles).
    Trả về: {cluster, segment_name, segment_name_en, description, marketing_strategy, color,
             distances: {cluster: khoảng cách tới tâm cụm}}
    """
    if recency < 0:
        raise ValueError("Recency must be ≥ 0 days.")
    if frequency < 1:
        raise ValueError("Frequency must be at least 1 invoice.")
    if monetary < 0:
        raise ValueError("Monetary must be ≥ 0.")

    p = _model_params()
    z = [(math.log1p(v) - m) / s
         for v, m, s in zip((recency, frequency, monetary), p["scaler_mean"], p["scaler_scale"])]
    distances = {c: math.dist(z, center) for c, center in enumerate(p["centroids"])}
    cluster = min(distances, key=distances.get)
    return {**_SEGMENT_BY_CLUSTER[cluster], "distances": distances}
