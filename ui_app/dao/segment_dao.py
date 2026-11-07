
from .database import get_connection, DatabaseError
import mysql.connector

HIGH_VALUE_COLOR = "#1B7A4E"
LOW_ACTIVITY_COLOR = "#767676"


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
                    # Cùng màu với chế độ Demo (mock_service); chọn theo tên để không phụ thuộc số hiệu cụm
                    name_en = (row.get("segment_name_en") or "").lower()
                    row["color"] = HIGH_VALUE_COLOR if "high" in name_en else LOW_ACTIVITY_COLOR

                return rows
            finally:
                cur.close()

        except mysql.connector.Error as exc:
            raise DatabaseError(
                "Không đọc được thông tin phân khúc từ MySQL."
            ) from exc
        finally:
            conn.close()
