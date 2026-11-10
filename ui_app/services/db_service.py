"""Service dùng DAO MySQL cho dữ liệu nghiệp vụ, giữ model K-Means hiện có.

Số hiệu cụm trả về giao diện là số hiệu của bảng `segments` trong MySQL (0 = High-Value,
1 = Low-Activity). Model K-Means đánh số khác, nên mọi kết quả lấy từ model (dự đoán, tâm cụm)
được đổi sang số hiệu MySQL theo tên phân khúc lưu trong model_info.joblib.
"""
import csv

import mysql.connector
import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_samples

from dao.database import get_connection, DatabaseError
from dao.transaction_dao import TransactionDAO
from dao.customer_dao import CustomerDAO
from dao.rfm_dao import RFMDAO
from dao.segment_dao import SegmentDAO
from . import mock_service
from .rfm_model_service import FEATURES, RFMModelService
from segment_colors import segment_color

_transaction_dao = TransactionDAO()
_customer_dao = CustomerDAO()
_rfm_dao = RFMDAO()
_segment_dao = SegmentDAO()
_model_service = RFMModelService()



# ---------------------------------------------------------------- Dashboard (Task 6)
# Doanh thu tính trên invoice_details.total_amount (= quantity × unit_price, DECIMAL 4 chữ số),
# cùng cột mà trang Transaction Data dùng để tính tổng tiền, nên hai màn hình luôn khớp nhau.
# invoice_details chỉ chứa dòng mua (CHECK quantity > 0); hoàn hàng chưa khớp của dữ liệu sạch
# không có trong bảng này (xem customer_segmentation/database/import_mysql.py).
DASHBOARD_STATS_SQL = """
    SELECT
        (SELECT COUNT(DISTINCT customer_id) FROM invoices)          AS total_customers,
        (SELECT COUNT(*) FROM invoices)                              AS total_invoices,
        (SELECT COALESCE(SUM(total_amount), 0) FROM invoice_details) AS total_revenue,
        (SELECT COUNT(*) FROM segments)                              AS num_segments,
        (SELECT MIN(invoice_date) FROM invoices)                     AS date_from,
        (SELECT MAX(invoice_date) FROM invoices)                     AS date_to
"""

MONTHLY_REVENUE_SQL = """
    SELECT DATE_FORMAT(i.invoice_date, '%Y-%m') AS month,
           SUM(d.total_amount)                  AS revenue
    FROM invoice_details d
    JOIN invoices i ON i.invoice_no = d.invoice_no
    GROUP BY month
    ORDER BY month
"""


def get_dashboard_stats():
    """4 thẻ KPI và khoảng ngày của dữ liệu giao dịch trong MySQL."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(DASHBOARD_STATS_SQL)
            row = cur.fetchone()
        finally:
            cur.close()
    except mysql.connector.Error as exc:
        raise DatabaseError("Không đọc được số liệu Dashboard.") from exc
    finally:
        conn.close()

    if row["date_from"] is None:
        raise DatabaseError("MySQL chưa có dữ liệu giao dịch. Hãy chạy "
                            "customer_segmentation/database/import_mysql.py trước.")
    return {
        "total_customers": int(row["total_customers"] or 0),
        "total_invoices": int(row["total_invoices"] or 0),
        "total_revenue": round(float(row["total_revenue"] or 0), 2),
        "num_segments": int(row["num_segments"] or 0),
        "date_from": row["date_from"],
        "date_to": row["date_to"],
    }


def get_monthly_revenue():
    """[("2010-12", 550552.08), ...]: doanh thu theo tháng của ngày lập hóa đơn, tăng dần."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(MONTHLY_REVENUE_SQL)
            rows = cur.fetchall()
        finally:
            cur.close()
    except mysql.connector.Error as exc:
        raise DatabaseError("Không đọc được doanh thu theo tháng.") from exc
    finally:
        conn.close()
    return [(month, round(float(revenue or 0), 2)) for month, revenue in rows]


def get_segment_summary():
    """Chỉ số RFM theo phân khúc kèm màu nhận diện (DashboardPage cần khóa "color")."""
    colors = {int(s["cluster"]): s["color"] for s in _segment_dao.get_segments()}
    rows = _rfm_dao.get_segment_summary()
    for row in rows:
        row["color"] = colors.get(int(row["cluster"]), segment_color(row.get("segment_name_en")))
    return rows


def get_countries(): return _transaction_dao.get_countries()
def get_transactions(keyword="", country=None, date_from=None, date_to=None, page=1, page_size=50):
    return _transaction_dao.get_transactions(keyword, country, date_from, date_to, page, page_size)
def get_segments(): return _segment_dao.get_segments()
def get_model_info():
    """Task 11: đọc metrics K=2..10 và metrics mô hình cuối từ file kết quả thật."""
    return _model_service.get_model_info()
def get_rfm_table(keyword="", cluster=None, page=1, page_size=50):
    result = _rfm_dao.get_rfm_table(keyword, cluster, page, page_size)
    for row in result["rows"]:
        row["recency"] = int(row["recency"])
        row["frequency"] = int(row["frequency"])
        row["monetary"] = float(row["monetary"])
        row["cluster"] = None if row["cluster"] is None else int(row["cluster"])
    return result


# Tên hàm trang RFM & Model gọi (giống hybrid_service)
get_real_model_info = get_model_info
get_real_rfm_table = get_rfm_table


def get_model_segments():
    """Phân khúc cho trang RFM & Model: lấy từ bảng segments (số hiệu, tên, màu, chiến lược)."""
    return get_segments()


# ---------------------------------------------------------------- đổi số hiệu cụm model -> MySQL
def _model_to_db_cluster():
    """{số hiệu cụm của model: số hiệu cụm trong bảng segments}, khớp theo tên tiếng Anh."""
    by_name = {s["segment_name_en"]: int(s["cluster"]) for s in get_segments()}
    mapping = {}
    for model_cluster, info in _model_service.cluster_mapping.items():
        name = info.get("segment_name_en")
        if name not in by_name:
            raise ValueError(f"Không tìm thấy phân khúc {name} trong bảng segments của MySQL.")
        mapping[int(model_cluster)] = by_name[name]
    return mapping


def predict_segment(recency, frequency, monetary):
    """Model dự đoán; tên, mô tả, chiến lược và màu lấy từ bảng segments (giống trang Marketing)."""
    prediction = _model_service.predict_segment(recency, frequency, monetary)
    segments = {s["segment_name_en"]: s for s in get_segments()}
    details = segments.get(prediction["segment_name_en"])
    if details is None:
        raise ValueError(
            "Không tìm thấy phân khúc "
            f"{prediction['segment_name_en']} trong bảng segments của MySQL."
        )
    to_db = _model_to_db_cluster()
    distances = {to_db[c]: d for c, d in prediction.get("distances", {}).items() if c in to_db}
    return {**prediction, **details, "distances": distances}


def get_customers(keyword="", page=1, page_size=50):
    return _customer_dao.list_customers(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


def count_customers():
    return _customer_dao.count_customers()


# ---------------------------------------------------------------- Customer Segmentation (Task 12)
_SEGMENT_CUSTOMERS_FROM = """
    FROM rfm_profiles r
    JOIN customer_segments cs ON cs.customer_id = r.customer_id
    JOIN segments s ON s.cluster = cs.cluster
    LEFT JOIN customers c ON c.customer_id = r.customer_id
"""
_SEGMENT_CUSTOMERS_COLUMNS = """
    SELECT r.customer_id, c.country, r.recency, r.frequency, r.monetary,
           cs.cluster, s.segment_name, s.segment_name_en
"""
_SORTS = {
    "monetary_desc": "r.monetary DESC, r.customer_id",
    "frequency_desc": "r.frequency DESC, r.customer_id",
    "recency_asc": "r.recency ASC, r.customer_id",
    "recency_desc": "r.recency DESC, r.customer_id",
    "customer_id": "r.customer_id",
}
_EXPORT_COLUMNS = ["customer_id", "country", "recency", "frequency", "monetary",
                   "cluster", "segment_name", "segment_name_en"]


def _segment_filters(keyword="", cluster=None, country=None, min_recency=None, max_recency=None,
                     min_frequency=None, max_frequency=None):
    where, params = [], []
    keyword = (keyword or "").strip()
    if keyword:
        where.append("CAST(r.customer_id AS CHAR) LIKE %s")
        params.append(f"%{keyword}%")
    for value, sql in ((cluster, "cs.cluster = %s"), (country, "c.country = %s"),
                       (min_recency, "r.recency >= %s"), (max_recency, "r.recency <= %s"),
                       (min_frequency, "r.frequency >= %s"), (max_frequency, "r.frequency <= %s")):
        if value is not None and value != "":
            where.append(sql)
            params.append(value)
    return (" WHERE " + " AND ".join(where) if where else ""), params


def _clean_customer_row(row):
    row["customer_id"] = int(row["customer_id"])
    row["recency"] = int(row["recency"])
    row["frequency"] = int(row["frequency"])
    row["monetary"] = float(row["monetary"])
    row["cluster"] = int(row["cluster"])
    row["country"] = row["country"] or ""
    return row


def _query(sql, params=(), error="Không truy vấn được dữ liệu khách hàng từ MySQL."):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, tuple(params))
            return cur.fetchall()
        finally:
            cur.close()
    except mysql.connector.Error as exc:
        raise DatabaseError(error) from exc
    finally:
        conn.close()


def get_customer_countries():
    """Quốc gia của các khách hàng đã được phân khúc, A–Z."""
    rows = _query("SELECT DISTINCT c.country FROM customers c "
                  "JOIN customer_segments cs ON cs.customer_id = c.customer_id "
                  "WHERE c.country IS NOT NULL AND c.country <> '' ORDER BY c.country")
    return [r["country"] for r in rows]


def get_segment_customers(keyword="", cluster=None, country=None, min_recency=None, max_recency=None,
                          min_frequency=None, max_frequency=None, sort_by="customer_id",
                          page=1, page_size=50):
    """Danh sách khách hàng theo phân khúc (lọc + sắp xếp + phân trang), cùng định dạng mock_service."""
    clause, params = _segment_filters(keyword, cluster, country, min_recency, max_recency,
                                      min_frequency, max_frequency)
    summary = _query("SELECT COUNT(*) AS total, COALESCE(SUM(r.monetary), 0) AS monetary"
                     + _SEGMENT_CUSTOMERS_FROM + clause, params)[0]
    page = max(1, int(page))
    page_size = max(1, int(page_size))
    rows = _query(_SEGMENT_CUSTOMERS_COLUMNS + _SEGMENT_CUSTOMERS_FROM + clause
                  + " ORDER BY " + _SORTS.get(sort_by, _SORTS["customer_id"]) + " LIMIT %s OFFSET %s",
                  params + [page_size, (page - 1) * page_size])
    return {"rows": [_clean_customer_row(r) for r in rows],
            "total_rows": int(summary["total"]),
            "total_monetary": float(summary["monetary"])}


def export_customers_csv(file_path, **filters):
    """Xuất khách hàng (cùng bộ lọc get_segment_customers, không phân trang) ra CSV UTF-8 cho Excel."""
    sort_by = filters.pop("sort_by", "customer_id")
    filters.pop("page", None)
    filters.pop("page_size", None)
    clause, params = _segment_filters(**filters)
    rows = _query(_SEGMENT_CUSTOMERS_COLUMNS + _SEGMENT_CUSTOMERS_FROM + clause
                  + " ORDER BY " + _SORTS.get(sort_by, _SORTS["customer_id"]), params)
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_EXPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_clean_customer_row(r) for r in rows)
    return len(rows)


# ---------------------------------------------------------------- Cluster Analysis & Marketing (Task 12)
_PROFILE_SQL = """
    SELECT r.customer_id, r.recency, r.frequency, r.monetary, r.reference_date, cs.cluster,
           MIN(i.invoice_date) AS first_purchase
    FROM rfm_profiles r
    JOIN customer_segments cs ON cs.customer_id = r.customer_id
    LEFT JOIN invoices i ON i.customer_id = r.customer_id
    GROUP BY r.customer_id, r.recency, r.frequency, r.monetary, r.reference_date, cs.cluster
"""


def _pct(mask):
    return float(mask.mean() * 100) if len(mask) else 0.0


def get_cluster_profiles():
    """Hồ sơ từng cụm (như outputs/cluster_profile.csv, mục 3.5) tính từ dữ liệu trong MySQL."""
    rows = _query(_PROFILE_SQL, error="Không tổng hợp được hồ sơ cụm từ MySQL.")
    if not rows:
        return []
    cluster = np.array([int(r["cluster"]) for r in rows])
    rfm = np.array([[float(r["recency"]), float(r["frequency"]), float(r["monetary"])] for r in rows])
    tenure = np.array([(r["reference_date"] - r["first_purchase"].date()).days
                       if r["first_purchase"] is not None else np.nan for r in rows], dtype=float)
    # Silhouette tính trên đúng thang của model: log1p -> StandardScaler đã lưu
    scaled = _model_service.scaler.transform(
        pd.DataFrame(np.log1p(rfm), columns=FEATURES))
    silhouette = (silhouette_samples(scaled, cluster) if len(set(cluster)) > 1
                  else np.zeros(len(cluster)))

    total_customers = len(rows)
    total_revenue = float(rfm[:, 2].sum()) or 1.0
    segments = {int(s["cluster"]): s for s in get_segments()}
    profiles = []
    for c in sorted(set(cluster)):
        m = cluster == c
        recency, frequency, monetary = rfm[m, 0], rfm[m, 1], rfm[m, 2]
        seg = segments.get(int(c), {})
        revenue = float(monetary.sum())
        invoices = int(frequency.sum())
        profiles.append({
            "cluster": int(c),
            "segment_name": seg.get("segment_name", f"Cụm {c}"),
            "segment_name_en": seg.get("segment_name_en", f"Cluster {c}"),
            "color": seg.get("color", segment_color(seg.get("segment_name_en"))),
            "customers": int(m.sum()),
            "customer_pct": float(m.sum() / total_customers * 100),
            "revenue": revenue,
            "revenue_pct": revenue / total_revenue * 100,
            "invoices": invoices,
            "recency_mean": float(recency.mean()),
            "recency_median": float(np.median(recency)),
            "frequency_mean": float(frequency.mean()),
            "frequency_median": float(np.median(frequency)),
            "monetary_mean": float(monetary.mean()),
            "monetary_median": float(np.median(monetary)),
            "one_time_pct": _pct(frequency == 1),
            "recency_le_30_pct": _pct(recency <= 30),
            "recency_gt_90_pct": _pct(recency > 90),
            "recency_gt_180_pct": _pct(recency > 180),
            "avg_invoice_value": revenue / invoices if invoices else 0.0,
            "tenure_median": float(np.nanmedian(tenure[m])) if np.isfinite(tenure[m]).any() else 0.0,
            "silhouette_mean": float(silhouette[m].mean()),
            "negative_silhouette_pct": _pct(silhouette[m] < 0),
        })
    profiles.sort(key=lambda p: p["revenue"], reverse=True)
    return profiles


def get_cluster_centroids():
    """Tâm cụm của model (thang log1p + StandardScaler), đánh số theo bảng segments."""
    to_db = _model_to_db_cluster()
    centers = _model_service.model.cluster_centers_
    return {"features": ["Recency", "Frequency", "Monetary"],
            "centroids": {to_db[i]: [float(v) for v in center]
                          for i, center in enumerate(centers) if i in to_db}}


# Hành động marketing là quy tắc của ứng dụng (định nghĩa trong mock_service), gắn theo tên phân khúc
_ACTIONS_BY_SEGMENT = {
    mock_service._SEGMENT_BY_CLUSTER[c]["segment_name_en"]: actions
    for c, actions in mock_service._MARKETING_ACTIONS.items()
}


def get_marketing_actions(cluster):
    """Hành động marketing đề xuất cho 1 phân khúc (cluster theo bảng segments)."""
    seg = next((s for s in get_segments() if int(s["cluster"]) == int(cluster)), None)
    actions = _ACTIONS_BY_SEGMENT.get(seg["segment_name_en"], []) if seg else []
    return [dict(a, target=dict(a["target"])) for a in actions]
