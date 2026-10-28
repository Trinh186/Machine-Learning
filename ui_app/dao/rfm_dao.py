from .database import get_connection, DatabaseError
import mysql.connector


class RFMDAO:
    """Truy vấn RFM từng khách hàng và thống kê theo cụm."""

    def get_rfm_table(self, keyword="", cluster=None, page=1, page_size=50):
        where = []
        params = []
        keyword = (keyword or "").strip()
        if keyword:
            where.append("CAST(r.customer_id AS CHAR) LIKE %s")
            params.append(f"%{keyword}%")
        if cluster is not None:
            where.append("cs.cluster = %s")
            params.append(int(cluster))
        clause = " WHERE " + " AND ".join(where) if where else ""
        join_sql = """ FROM rfm_profiles r
                       LEFT JOIN customer_segments cs ON cs.customer_id = r.customer_id
                       LEFT JOIN segments s ON s.cluster = cs.cluster """
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) AS total" + join_sql + clause, tuple(params))
            total = int(cur.fetchone()["total"])
            page = max(1, int(page)); page_size = max(1, int(page_size))
            sql = """SELECT r.customer_id, r.recency, r.frequency, r.monetary,
                            cs.cluster, s.segment_name, s.segment_name_en""" + join_sql + clause + \
                  " ORDER BY r.customer_id LIMIT %s OFFSET %s"
            cur.execute(sql, tuple(params + [page_size, (page - 1) * page_size]))
            rows = cur.fetchall()
            return {"rows": rows, "total_rows": total}
        except mysql.connector.Error as exc:
            raise DatabaseError("Không truy vấn được dữ liệu RFM.") from exc
        finally:
            conn.close()

    def get_segment_summary(self):
        sql = """SELECT s.cluster, s.segment_name, s.segment_name_en,
                        COUNT(DISTINCT r.customer_id) AS customers,
                        AVG(r.recency) AS avg_recency,
                        AVG(r.frequency) AS avg_frequency,
                        AVG(r.monetary) AS avg_monetary,
                        COALESCE(SUM(r.monetary), 0) AS revenue
                 FROM segments s
                 LEFT JOIN customer_segments cs ON cs.cluster = s.cluster
                 LEFT JOIN rfm_profiles r ON r.customer_id = cs.customer_id
                 GROUP BY s.cluster, s.segment_name, s.segment_name_en
                 ORDER BY s.cluster"""
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql)
            rows = cur.fetchall()
            total_customers = sum(int(r["customers"] or 0) for r in rows)
            total_revenue = sum(float(r["revenue"] or 0) for r in rows)
            for row in rows:
                row["customers"] = int(row["customers"] or 0)
                row["avg_recency"] = float(row["avg_recency"] or 0)
                row["avg_frequency"] = float(row["avg_frequency"] or 0)
                row["avg_monetary"] = float(row["avg_monetary"] or 0)
                row["revenue"] = float(row["revenue"] or 0)
                row["customer_share"] = (row["customers"] / total_customers * 100) if total_customers else 0
                row["revenue_share"] = (row["revenue"] / total_revenue * 100) if total_revenue else 0
            return rows
        except mysql.connector.Error as exc:
            raise DatabaseError("Không tổng hợp được chỉ số RFM theo phân khúc.") from exc
        finally:
            conn.close()
