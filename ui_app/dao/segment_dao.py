from .database import get_connection, DatabaseError
import mysql.connector

from segment_colors import segment_color


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
                    row["color"] = segment_color(row.get("segment_name_en"))

                return rows
            finally:
                cur.close()

        except mysql.connector.Error as exc:
            raise DatabaseError(
                "Không đọc được thông tin phân khúc từ MySQL."
            ) from exc
        finally:
            conn.close()
