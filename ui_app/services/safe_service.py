"""Bọc lớp service để lỗi MySQL không làm văng app.

Giao diện vẫn gọi self.service.get_xxx(...) như cũ. Khác biệt:
  - Hàm báo lỗi MySQL (mất kết nối giữa chừng) -> trả kết quả của hàm cùng tên trong service
    dự phòng (hybrid_service: dữ liệu mẫu + model K-Means) và chuyển sang trạng thái OFFLINE.
  - Đang OFFLINE hoặc database rỗng (EMPTY) -> các hàm đọc dữ liệu dùng luôn dữ liệu mẫu,
    không chờ MySQL nữa (tránh mỗi lần bấm lại treo vài giây).
  - Mỗi lần trạng thái đổi, MainWindow được báo để hiện / ẩn thanh cảnh báo có nút "Thử lại".
  - check() kiểm tra lại MySQL (gọi khi mở app sau đăng nhập và khi bấm "Thử lại").
  - use_demo() cho chế độ Demo: chỉ dùng service dự phòng, không chạm MySQL, không cảnh báo.
"""
import functools

import mysql.connector

from dao.database import DatabaseError
from . import db_health

DB_ERRORS = (DatabaseError, mysql.connector.Error)


class SafeService:
    def __init__(self, service, fallback):
        self._service = service
        self._fallback = fallback
        self.status = db_health.OK
        self.message = ""
        self._listeners = []

    # ---------- trạng thái ----------
    def add_listener(self, callback):
        """callback(status, message) được gọi mỗi khi trạng thái MySQL thay đổi."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    @property
    def using_fallback(self) -> bool:
        return self.status != db_health.OK

    def _set_status(self, status, message):
        if (status, message) == (self.status, self.message):
            return
        self.status, self.message = status, message
        for callback in list(self._listeners):
            callback(status, message)

    def use_demo(self):
        """Chế độ Demo: mọi hàm dùng service dự phòng (không cần MySQL)."""
        self._set_status(db_health.DEMO, "")

    def check(self) -> str:
        """Kiểm tra lại MySQL, cập nhật trạng thái và trả về OK / OFFLINE / EMPTY."""
        self._set_status(*db_health.check_database())
        return self.status

    # ---------- bọc từng hàm ----------
    def __getattr__(self, name):
        target = getattr(self._service, name)
        if not callable(target):
            return target
        fallback = getattr(self._fallback, name, None)

        @functools.wraps(target)
        def call(*args, **kwargs):
            if self.using_fallback and fallback is not None:
                return fallback(*args, **kwargs)
            try:
                return target(*args, **kwargs)
            except DB_ERRORS as exc:
                message = str(exc) if isinstance(exc, DatabaseError) else "Mất kết nối MySQL."
                self._set_status(db_health.OFFLINE, message)
                if fallback is None:
                    raise DatabaseError(message) from exc
                return fallback(*args, **kwargs)

        return call
