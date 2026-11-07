"""Kiểm tra nhanh MySQL: kết nối được không và đã có dữ liệu chưa.

Trả về (trạng thái, thông báo):
    OK       – kết nối được, các bảng giao diện cần đều đã có dữ liệu
    OFFLINE  – không kết nối được (MySQL tắt, sai mật khẩu, sai .env ...)
    EMPTY    – kết nối được nhưng thiếu bảng hoặc bảng còn trống
"""
import os

import mysql.connector

from dao.database import DatabaseError, get_connection

OK, OFFLINE, EMPTY = "ok", "offline", "empty"

# Các bảng giao diện đọc, theo thứ tự database.sql / import_mysql.py tạo và nạp
REQUIRED_TABLES = ("segments", "customers", "invoices", "invoice_details",
                   "rfm_profiles", "customer_segments")
ER_NO_SUCH_TABLE = 1146
ER_BAD_DB = 1049             # chưa tạo database
ER_ACCESS_DENIED = 1045      # sai tài khoản / mật khẩu

RUN_SQL = "Hãy chạy customer_segmentation/database/database.sql."
RUN_IMPORT = "Hãy chạy customer_segmentation/database/import_mysql.py để nạp dữ liệu."


def check_database() -> tuple[str, str]:
    try:
        conn = get_connection()
    except DatabaseError as exc:
        errno = getattr(exc.__cause__, "errno", None)
        if errno == ER_BAD_DB:
            return EMPTY, f"Chưa có database {os.getenv('DB_NAME', 'customer_segmentation')}. {RUN_SQL}"
        if errno == ER_ACCESS_DENIED:
            return OFFLINE, "Sai tài khoản hoặc mật khẩu MySQL (DB_USER / DB_PASSWORD trong ui_app/.env)."
        return OFFLINE, str(exc)

    try:
        cur = conn.cursor(buffered=True)
        try:
            for table in REQUIRED_TABLES:
                try:
                    cur.execute(f"SELECT 1 FROM `{table}` LIMIT 1")
                except mysql.connector.Error as exc:
                    if exc.errno == ER_NO_SUCH_TABLE:
                        return EMPTY, f"Database chưa có bảng {table}. {RUN_SQL}"
                    raise
                if cur.fetchone() is None:
                    hint = RUN_SQL if table == "segments" else RUN_IMPORT
                    return EMPTY, f"Bảng {table} đang trống. {hint}"
        finally:
            cur.close()
    except mysql.connector.Error:
        return OFFLINE, "Mất kết nối MySQL trong lúc kiểm tra dữ liệu."
    finally:
        try:
            conn.close()
        except mysql.connector.Error:
            pass
    return OK, ""
