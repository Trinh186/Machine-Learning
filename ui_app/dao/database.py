"""Single MySQL connection factory and shared DatabaseError for ui_app."""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

UI_APP_DIR = Path(__file__).resolve().parents[1]
# Environment variables already set by the operating system take precedence.
load_dotenv(UI_APP_DIR / ".env", override=False)


class DatabaseError(Exception):
    """Database failure that may be displayed by the UI."""


def get_connection():
    user = os.getenv("DB_USER", "").strip()
    if not user:
        raise DatabaseError("Chưa cấu hình DB_USER trong ui_app/.env.")
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as exc:
        raise DatabaseError("DB_PORT phải là số nguyên từ 1 đến 65535.") from exc
    if not 1 <= port <= 65535:
        raise DatabaseError("DB_PORT phải là số nguyên từ 1 đến 65535.")
    config = {
        "host": os.getenv("DB_HOST", "127.0.0.1").strip(),
        "port": port,
        "user": user,
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "customer_segmentation").strip(),
        "charset": "utf8mb4",
        "use_unicode": True,
        "connection_timeout": 5,
    }
    if not config["host"] or not config["database"]:
        raise DatabaseError("DB_HOST và DB_NAME không được để trống trong ui_app/.env.")
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as exc:
        raise DatabaseError(
            "Không thể kết nối MySQL. Kiểm tra MySQL Server và cấu hình ui_app/.env."
        ) from exc
