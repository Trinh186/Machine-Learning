"""
mock_service.py — DỮ LIỆU MẪU để chạy giao diện khi chưa nối MySQL (chế độ Demo).

Cập nhật 07/11 theo dữ liệu sạch mới (data_preprocessor của Hồng) và model K-Means train lại của Thư:
  - Dashboard / Transaction Data: lấy đúng số liệu mà db_service trả về sau khi chạy import_mysql.py
    (4.324 khách có mua, 18.276 hóa đơn, doanh thu £8.294.883,51; 4.000 dòng giao dịch mẫu)
  - RFM / phân khúc: customer_clusters.csv + cluster_profile.csv của Thư (4.320 khách)
  - Model: tâm cụm + scaler + K = 2..10 từ outputs/*.joblib và kmeans_metrics_k2_10.csv

Số hiệu cụm trong file này theo bảng `segments` của MySQL: 0 = High-Value, 1 = Low-Activity.
(Model K-Means đánh số ngược lại; giao diện chỉ hiển thị TÊN phân khúc nên không bị lệch.)

>>> Khi phần thật xong, tạo services/db_service.py có ĐÚNG các hàm dưới đây
>>> (cùng tên, cùng tham số, cùng kiểu trả về) rồi đổi 1 dòng importtrong services/__init__.py.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "mock_data"

from segment_colors import segment_color


# Giống bảng `segments` trong customer_segmentation/database/database.sql
_SEGMENTS = [
    {
        "cluster": 0,
        "segment_name": "Khách hàng giá trị cao",
        "segment_name_en": "High-Value Customers",
        "description": "Mua gần đây (Recency TB 26,13 ngày), mua thường xuyên (Frequency TB 8,38 hóa đơn), "
                       "chi tiêu cao (Monetary TB £4.230,20). Chiếm 38,17% khách hàng nhưng 84,35% doanh thu.",
        "marketing_strategy": "Ưu tiên chăm sóc; chương trình khách hàng thân thiết/VIP và ưu đãi cá nhân hóa "
                              "phù hợp với giá trị mua hàng.",
        "color": segment_color("High-Value Customers"),
    },
    {
        "cluster": 1,
        "segment_name": "Khách hàng ít hoạt động",
        "segment_name_en": "Low-Activity Customers",
        "description": "Lâu chưa quay lại (Recency TB 134,70 ngày), mua ít (Frequency TB 1,66 hóa đơn), "
                       "chi tiêu thấp (Monetary TB £484,48). Chiếm 61,83% khách hàng, 15,65% doanh thu.",
        "marketing_strategy": "Thử nghiệm chiến dịch kích hoạt lại, voucher quay lại và nhắc mua hàng; "
                              "đánh giá hiệu quả theo phản hồi thực tế.",
        "color": segment_color("Low-Activity Customers"),
    },
]
_SEGMENT_BY_CLUSTER = {s["cluster"]: s for s in _SEGMENTS}

# Bảng 3.5.1 – cluster_metrics.csv
_MODEL_METRICS = {
    "k": 2,
    "silhouette": 0.4323,
    "davies_bouldin": 0.8904,
    "calinski_harabasz": 4361.19,
    "inertia": 6447.76,
}

_MONTHLY = {
    "2010-12": 550552.08, "2011-01": 454493.19, "2011-02": 435674.73, "2011-03": 571696.40,
    "2011-04": 447977.99, "2011-05": 647608.16, "2011-06": 639381.57, "2011-07": 581165.78,
    "2011-08": 614117.00, "2011-09": 924834.25, "2011-10": 964727.88, "2011-11": 1120029.96,
    "2011-12": 342624.52,
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
            "country": r["country"],
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
        "total_customers": 4324,             # bảng customers (khách có ít nhất 1 dòng mua)
        "total_invoices": 18276,
        "total_revenue": 8294883.51,         # GBP (£), tổng invoice_details
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
        raise ValueError("Recency không được âm.")
    if frequency < 1:
        raise ValueError("Frequency phải từ 1 trở lên.")
    if monetary < 0:
        raise ValueError("Monetary không được âm.")

    p = _model_params()
    z = [(math.log1p(v) - m) / s
         for v, m, s in zip((recency, frequency, monetary), p["scaler_mean"], p["scaler_scale"])]
    distances = {c: math.dist(z, center) for c, center in enumerate(p["centroids"])}
    cluster = min(distances, key=distances.get)
    return {**_SEGMENT_BY_CLUSTER[cluster], "distances": distances}


# ----------------------------------------------------------------------------
# CUSTOMER SEGMENTATION  (Task 12)
# ----------------------------------------------------------------------------
_SORTS = {
    "monetary_desc": (lambda r: r["monetary"], True),
    "frequency_desc": (lambda r: r["frequency"], True),
    "recency_asc": (lambda r: r["recency"], False),
    "recency_desc": (lambda r: r["recency"], True),
    "customer_id": (lambda r: r["customer_id"], False),
}


def _filter_customers(keyword="", cluster=None, country=None, min_recency=None, max_recency=None,
                      min_frequency=None, max_frequency=None, sort_by="customer_id") -> list[dict]:
    kw = (keyword or "").strip()
    rows = []
    for r in _rfm():
        if cluster is not None and r["cluster"] != cluster:
            continue
        if country and r["country"] != country:
            continue
        if kw and kw not in str(r["customer_id"]):
            continue
        if min_recency is not None and r["recency"] < min_recency:
            continue
        if max_recency is not None and r["recency"] > max_recency:
            continue
        if min_frequency is not None and r["frequency"] < min_frequency:
            continue
        if max_frequency is not None and r["frequency"] > max_frequency:
            continue
        seg = _SEGMENT_BY_CLUSTER[r["cluster"]]
        rows.append({**r, "segment_name": seg["segment_name"], "segment_name_en": seg["segment_name_en"]})
    key, reverse = _SORTS.get(sort_by, _SORTS["customer_id"])
    rows.sort(key=key, reverse=reverse)
    return rows


def get_customer_countries() -> list[str]:
    """Quốc gia của khách hàng (ô lọc trang Customer Segmentation), A–Z."""
    return sorted({r["country"] for r in _rfm()})


def get_segment_customers(keyword: str = "", cluster: int | None = None, country: str | None = None,
                          min_recency: int | None = None, max_recency: int | None = None,
                          min_frequency: int | None = None, max_frequency: int | None = None,
                          sort_by: str = "customer_id", page: int = 1, page_size: int = 50) -> dict:
    """
    Danh sách khách hàng theo phân khúc (có lọc + sắp xếp + phân trang).
      sort_by: "monetary_desc" | "frequency_desc" | "recency_asc" | "recency_desc" | "customer_id"
    Trả về: {"rows": [{customer_id, country, recency, frequency, monetary, cluster,
                       segment_name, segment_name_en}], "total_rows": int, "total_monetary": float}
    """
    rows = _filter_customers(keyword, cluster, country, min_recency, max_recency,
                             min_frequency, max_frequency, sort_by)
    total_monetary = sum(r["monetary"] for r in rows)
    page_rows, total = _paginate(rows, page, page_size)
    return {"rows": page_rows, "total_rows": total, "total_monetary": total_monetary}


def export_customers_csv(file_path: str, **filters) -> int:
    """
    Xuất danh sách khách hàng (cùng bộ lọc như get_segment_customers, không phân trang) ra CSV UTF-8
    (mở được bằng Excel). Trả về số dòng đã xuất.
    """
    filters.pop("page", None)
    filters.pop("page_size", None)
    rows = _filter_customers(**filters)
    columns = ["customer_id", "country", "recency", "frequency", "monetary",
               "cluster", "segment_name", "segment_name_en"]
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ----------------------------------------------------------------------------
# CLUSTER ANALYSIS & MARKETING ACTION CENTER  (Task 12)
# ----------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _cluster_profile_rows() -> list[dict]:
    with open(_DATA_DIR / "cluster_profile.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_cluster_profiles() -> list[dict]:
    """
    Hồ sơ từng cụm (giống outputs/cluster_profile.csv, mục 3.5), sắp theo doanh thu giảm dần.
    Mỗi phần tử: cluster, segment_name, segment_name_en, color, customers, customer_pct, revenue,
      revenue_pct, invoices, recency_mean, recency_median, frequency_mean, frequency_median,
      monetary_mean, monetary_median, one_time_pct, recency_le_30_pct, recency_gt_90_pct,
      recency_gt_180_pct, avg_invoice_value, tenure_median, silhouette_mean
    """
    out = []
    for row in _cluster_profile_rows():
        cluster = int(row["cluster"])
        item = {"cluster": cluster, **{k: _SEGMENT_BY_CLUSTER[cluster][k]
                                       for k in ("segment_name", "segment_name_en", "color")}}
        for k, v in row.items():
            if k not in ("cluster", "segment_name", "segment_name_en"):
                item[k] = float(v)
        item["customers"] = int(item["customers"])
        item["invoices"] = int(item["invoices"])
        out.append(item)
    return out


def get_cluster_centroids() -> dict:
    """Tâm cụm trên thang log1p + StandardScaler (cho snake plot).
    Trả về: {"features": ["Recency", "Frequency", "Monetary"], "centroids": {cluster: [r, f, m]}}"""
    p = _model_params()
    return {"features": ["Recency", "Frequency", "Monetary"],
            "centroids": {c: list(v) for c, v in enumerate(p["centroids"])}}


# Hành động marketing đề xuất cho từng phân khúc. "target" là bộ lọc truyền thẳng vào
# get_segment_customers / export_customers_csv để lấy danh sách khách cần tiếp cận.
_MARKETING_ACTIONS = {
    0: [
        {"title": "Chương trình khách hàng thân thiết VIP",
         "description": "Tích điểm theo hạng, ưu tiên mua sản phẩm mới và chăm sóc riêng cho toàn bộ nhóm.",
         "target": {}, "kpi": "Tỷ lệ giữ chân, tỷ lệ mua lại"},
        {"title": "Ưu đãi cá nhân hóa cho khách mua thường xuyên",
         "description": "Gợi ý sản phẩm và combo theo lịch sử mua cho khách có từ 6 hóa đơn trở lên.",
         "target": {"min_frequency": 6}, "kpi": "Giá trị trung bình mỗi đơn"},
        {"title": "Giữ chân khách VIP có nguy cơ rời bỏ",
         "description": "Khách giá trị cao đã hơn 90 ngày chưa mua: gửi email hoặc gọi điện kèm ưu đãi tri ân.",
         "target": {"min_recency": 91}, "kpi": "Tỷ lệ quay lại trong 30 ngày"},
        {"title": "Chương trình giới thiệu bạn bè",
         "description": "Khách VIP vừa mua trong 30 ngày gần nhất giới thiệu khách mới để nhận thưởng.",
         "target": {"max_recency": 30}, "kpi": "Số khách mới được giới thiệu"},
    ],
    1: [
        {"title": "Khuyến khích mua lần hai",
         "description": "Khách mới mua một lần nhận voucher có thời hạn cho đơn hàng thứ hai.",
         "target": {"max_frequency": 1}, "kpi": "Tỷ lệ mua lần hai"},
        {"title": "Chiến dịch kéo khách quay lại (90–180 ngày)",
         "description": "Khách 3–6 tháng chưa mua: voucher quay lại và chuỗi email nhắc mua hàng.",
         "target": {"min_recency": 91, "max_recency": 180}, "kpi": "Tỷ lệ quay lại, doanh thu mỗi khách quay lại"},
        {"title": "Chăm sóc khách vừa mua",
         "description": "Khách mua trong 30 ngày gần nhất: gửi bản tin và bán chéo để tăng tần suất mua.",
         "target": {"max_recency": 30}, "kpi": "Tần suất mua trong 90 ngày tới"},
        {"title": "Kích hoạt lại chi phí thấp (trên 180 ngày)",
         "description": "Khách lâu không mua: chỉ dùng kênh chi phí thấp (email), ngừng liên hệ khách không phản hồi.",
         "target": {"min_recency": 181}, "kpi": "Chi phí cho mỗi khách quay lại"},
    ],
}


def get_marketing_actions(cluster: int) -> list[dict]:
    """
    Hành động marketing đề xuất cho 1 phân khúc.
    Mỗi phần tử: {"title", "description", "target": dict bộ lọc, "kpi"}
    """
    return [dict(a, target=dict(a["target"])) for a in _MARKETING_ACTIONS.get(cluster, [])]
