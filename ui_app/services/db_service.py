"""Service dùng DAO MySQL cho dữ liệu nghiệp vụ, giữ model K-Means hiện có."""
from datetime import datetime
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



def get_dashboard_stats():
    sql = """
        SELECT
            (SELECT COUNT(*) FROM customers)
                AS total_customers,
            (SELECT COUNT(*) FROM invoices)
                AS total_invoices,
            (
                SELECT COALESCE(
                    SUM(quantity * unit_price), 0
                )
                FROM invoice_details
            ) AS total_revenue,
            (SELECT COUNT(*) FROM segments)
                AS num_segments,
            (SELECT MIN(invoice_date) FROM invoices)
                AS date_from,
            (SELECT MAX(invoice_date) FROM invoices)
                AS date_to
    """

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        row = cur.fetchone()

        return {
            "total_customers": int(
                row["total_customers"] or 0
            ),
            "total_invoices": int(
                row["total_invoices"] or 0
            ),
            "total_revenue": float(
                row["total_revenue"] or 0
            ),
            "num_segments": int(
                row["num_segments"] or 0
            ),
            "date_from": row["date_from"],
            "date_to": row["date_to"],
        }

    except mysql.connector.Error as exc:
        raise DatabaseError(
            "Không đọc được số liệu Dashboard."
        ) from exc
    finally:
        conn.close()


def get_monthly_revenue():
    sql = """
        SELECT
            DATE_FORMAT(i.invoice_date, '%Y-%m') AS month,
            SUM(d.quantity * d.unit_price) AS revenue
        FROM invoices i
        JOIN invoice_details d
            ON d.invoice_no = i.invoice_no
        GROUP BY DATE_FORMAT(i.invoice_date, '%Y-%m')
        ORDER BY month
    """

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)

        return [
            (row[0], float(row[1] or 0))
            for row in cur.fetchall()
        ]

    except mysql.connector.Error as exc:
        raise DatabaseError(
            "Không đọc được doanh thu theo tháng."
        ) from exc
    finally:
        conn.close()



def get_segment_summary(): return _rfm_dao.get_segment_summary()
def get_countries(): return _transaction_dao.get_countries()
def get_transactions(keyword="", country=None, date_from=None, date_to=None, page=1, page_size=50):
    return _transaction_dao.get_transactions(keyword, country, date_from, date_to, page, page_size)
def get_segments(): return _segment_dao.get_segments()
def get_model_info(): return mock_service.get_model_info()
def get_rfm_table(keyword="", cluster=None, page=1, page_size=50):
    return _rfm_dao.get_rfm_table(keyword, cluster, page, page_size)


def predict_segment(recency, frequency, monetary):
    cluster = _model_service.predict_cluster(recency, frequency, monetary)
    segments = {int(s["cluster"]): s for s in get_segments()}
    if cluster not in segments:
        raise ValueError(f"Không tìm thấy thông tin cho Cluster {cluster} trong MySQL.")
    return dict(segments[cluster])

def get_customers(keyword="", page=1, page_size=50):
    return _customer_dao.list_customers(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


def count_customers():
    return _customer_dao.count_customers()