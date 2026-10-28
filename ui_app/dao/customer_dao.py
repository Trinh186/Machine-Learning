from .database import get_connection, DatabaseError
import mysql.connector


class CustomerDAO:
    """Truy vấn danh sách và số lượng khách hàng."""

    def count_customers(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM customers")
            return int(cur.fetchone()[0])
        except mysql.connector.Error as exc:
            raise DatabaseError("Không đếm được số lượng khách hàng.") from exc
        finally:
            conn.close()

    def list_customers(self, keyword="", page=1, page_size=50):
        keyword = (keyword or "").strip()
        where = " WHERE CAST(customer_id AS CHAR) LIKE %s OR COALESCE(country, '') LIKE %s" if keyword else ""
        params = [f"%{keyword}%", f"%{keyword}%"] if keyword else []
        page = max(1, int(page)); page_size = max(1, int(page_size))
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) AS total FROM customers" + where, tuple(params))
            total = int(cur.fetchone()["total"])
            cur.execute("SELECT customer_id, country, created_at FROM customers" + where +
                        " ORDER BY customer_id LIMIT %s OFFSET %s",
                        tuple(params + [page_size, (page - 1) * page_size]))
            return {"rows": cur.fetchall(), "total_rows": total}
        except mysql.connector.Error as exc:
            raise DatabaseError("Không truy vấn được danh sách khách hàng.") from exc
        finally:
            conn.close()
