
from .database import get_connection, DatabaseError
import mysql.connector


class TransactionDAO:
    """Truy vấn dữ liệu hóa đơn và chi tiết hóa đơn."""

    def get_countries(self):
        sql = """
            SELECT DISTINCT c.country
            FROM customers c
            WHERE c.country IS NOT NULL
              AND c.country <> ''
            ORDER BY c.country
        """

        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute(sql)
                return [row[0] for row in cur.fetchall()]
            finally:
                cur.close()

        except mysql.connector.Error as exc:
            raise DatabaseError(
                "Không đọc được danh sách quốc gia."
            ) from exc
        finally:
            conn.close()

    def get_transactions(
        self,
        keyword="",
        country=None,
        date_from=None,
        date_to=None,
        page=1,
        page_size=50,
    ):
        where = []
        params = []

        kw = (keyword or "").strip()

        if kw:
            where.append("""
                (
                    i.invoice_no LIKE %s
                    OR CAST(i.customer_id AS CHAR) LIKE %s
                    OR d.stock_code LIKE %s
                    OR COALESCE(p.description, '') LIKE %s
                )
            """)
            like = f"%{kw}%"
            params.extend([like, like, like, like])

        if country:
            where.append("c.country = %s")
            params.append(country)

        if date_from:
            where.append("i.invoice_date >= %s")
            params.append(date_from)

        if date_to:
            where.append(
                "i.invoice_date < DATE_ADD(%s, INTERVAL 1 DAY)"
            )
            params.append(date_to)

        clause = (
            " WHERE " + " AND ".join(where)
            if where else ""
        )

        from_sql = """
            FROM invoices i
            JOIN invoice_details d
                ON d.invoice_no = i.invoice_no
            JOIN customers c
                ON c.customer_id = i.customer_id
            LEFT JOIN products p
                ON p.stock_code = d.stock_code
        """

        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            try:
                # Thống kê trên cùng tập dữ liệu đã lọc.
                count_sql = """
                    SELECT
                        COUNT(*) AS total_rows,
                        COALESCE(SUM(d.total_amount), 0)
                            AS total_amount
                """ + from_sql + clause

                cur.execute(count_sql, tuple(params))
                totals = cur.fetchone()

                page = max(1, int(page))
                page_size = max(1, int(page_size))
                offset = (page - 1) * page_size

                sql = """
                    SELECT
                        i.invoice_no,
                        i.invoice_date,
                        i.customer_id,
                        c.country,
                        d.stock_code,
                        p.description,
                        d.quantity,
                        d.unit_price,
                        d.total_amount
                """ + from_sql + clause + """
                    ORDER BY
                        i.invoice_date DESC,
                        i.invoice_no DESC,
                        d.invoice_detail_id DESC
                    LIMIT %s OFFSET %s
                """

                cur.execute(
                    sql,
                    tuple(params + [page_size, offset]),
                )
                rows = cur.fetchall()

                return {
                    "rows": rows,
                    "total_rows": int(
                        totals["total_rows"] or 0
                    ),
                    "total_amount": float(
                        totals["total_amount"] or 0
                    ),
                }

            finally:
                cur.close()

        except mysql.connector.Error as exc:
            raise DatabaseError(
                "Không truy vấn được dữ liệu giao dịch."
            ) from exc
        finally:
            conn.close()
