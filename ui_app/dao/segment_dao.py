
from .database import get_connection, DatabaseError
import mysql.connector


class SegmentDAO:
    """Truy vấn phân khúc và chiến lược marketing từ MySQL."""

    def get_segments(self):
        sql = """
            SELECT
                cluster,
                segment_name,
                segment_name_en,
                description,
                marketing_strategy
            FROM segments
            ORDER BY cluster
        """

        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(sql)
                rows = cur.fetchall()

                for row in rows:
                    cluster = int(row["cluster"])
                    row["color"] = (
                        "#3B5BDB"
                        if cluster == 0
                        else "#0CA6A6"
                    )

                return rows
            finally:
                cur.close()

        except mysql.connector.Error as exc:
            raise DatabaseError(
                "Không đọc được thông tin phân khúc từ MySQL."
            ) from exc
        finally:
            conn.close()
