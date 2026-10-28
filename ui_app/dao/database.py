"""Shared MySQL connection helper for DAO classes."""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

UI_APP_DIR = Path(__file__).resolve().parents[1]
load_dotenv(UI_APP_DIR / ".env")


class DatabaseError(Exception):
    """Database error suitable for displaying in the UI."""


def get_connection():
    user = os.getenv("DB_USER", "").strip()
    if not user:
        raise DatabaseError("Chưa cấu hình DB_USER trong ui_app/.env.")

    config = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": user,
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "customer_segmentation"),
        "charset": "utf8mb4",
        "use_unicode": True,
        "connection_timeout": 5,
    }
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as exc:
        raise DatabaseError(
            "Không thể kết nối MySQL. Kiểm tra MySQL Server và cấu hình ui_app/.env."
        ) from exc
