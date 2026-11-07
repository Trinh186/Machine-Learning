"""Service dùng DAO MySQL cho dữ liệu nghiệp vụ, giữ model K-Means hiện có."""
import mysql.connector

from dao.database import get_connection, DatabaseError
from dao.transaction_dao import TransactionDAO
from dao.customer_dao import CustomerDAO
from dao.rfm_dao import RFMDAO
from dao.segment_dao import SegmentDAO
from . import mock_service
from .rfm_model_service import RFMModelService

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
        row["color"] = colors.get(int(row["cluster"]), "#6B7280")
    return rows


def get_countries(): return _transaction_dao.get_countries()
def get_transactions(keyword="", country=None, date_from=None, date_to=None, page=1, page_size=50):
    return _transaction_dao.get_transactions(keyword, country, date_from, date_to, page, page_size)
def get_segments(): return _segment_dao.get_segments()
def get_model_info():
    """Task 11: đọc metrics K=2..10 và metrics mô hình cuối từ file kết quả thật."""
    return _model_service.get_model_info()
def get_rfm_table(keyword="", cluster=None, page=1, page_size=50):
    return _rfm_dao.get_rfm_table(keyword, cluster, page, page_size)


def predict_segment(recency, frequency, monetary):
    """Task 8: dùng mapping được lưu trong model_info.joblib, không hardcode cluster ID."""
    prediction = _model_service.predict_segment(recency, frequency, monetary)
    segments = {s["segment_name_en"]: s for s in get_segments()}
    details = segments.get(prediction["segment_name_en"])
    if details is None:
        raise ValueError(
            "Không tìm thấy phân khúc "
            f"{prediction['segment_name_en']} trong bảng segments của MySQL."
        )
    return {**details, **prediction}

def get_customers(keyword="", page=1, page_size=50):
    return _customer_dao.list_customers(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


def count_customers():
    return _customer_dao.count_customers()


# Các trang Customer Segmentation và Cluster Analysis & Marketing chưa có DAO MySQL;
# tạm dùng dữ liệu mẫu như hybrid_service để có thể chuyển services/__init__.py sang db_service
# mà các trang này không bị lỗi thiếu hàm.
get_customer_countries = mock_service.get_customer_countries
get_segment_customers = mock_service.get_segment_customers
export_customers_csv = mock_service.export_customers_csv
get_cluster_profiles = mock_service.get_cluster_profiles
get_cluster_centroids = mock_service.get_cluster_centroids
get_marketing_actions = mock_service.get_marketing_actions
