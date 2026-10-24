"""Authentication + Authorization + Logout."""
import re
from dataclasses import dataclass

import bcrypt

from auth.user_dao import UserDAO

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


@dataclass(frozen=True)
class SessionUser:
    user_id: int
    username: str
    full_name: str
    role: str

    def to_dict(self):
        # MainWindow của Hằng nhận dict.
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
        }


class AuthService:
    def __init__(self, user_dao=None):
        self.user_dao = user_dao if user_dao is not None else UserDAO()
        self._current_user: SessionUser | None = None

    @property
    def current_user(self):
        return self._current_user

    def login(self, username: str, password: str) -> dict:
        # Mọi lần thử đăng nhập đều bắt đầu từ trạng thái chưa xác thực.
        self.logout()
        username = username.strip()
        if not username or not password:
            raise AuthenticationError("Vui lòng nhập tên đăng nhập và mật khẩu.")

        # Giao diện không so sánh password trong SQL: lấy hash từ DB để xác minh.
        record = self.user_dao.find_by_username(username)
        if not record:
            raise AuthenticationError("Tên đăng nhập hoặc mật khẩu không đúng.")
        try:
            matched = bcrypt.checkpw(
                password.encode("utf-8"),
                record["password_hash"].encode("utf-8"),
            )
        except (ValueError, TypeError):
            matched = False
        if not matched:
            raise AuthenticationError("Tên đăng nhập hoặc mật khẩu không đúng.")
        if not bool(record["is_active"]):
            raise AuthenticationError("Tài khoản đã bị khóa. Liên hệ Admin.")
        role = str(record["role"]).lower()
        if role not in ("admin", "user"):
            raise AuthenticationError("Vai trò tài khoản không hợp lệ.")

        self._current_user = SessionUser(
            user_id=int(record["user_id"]),
            username=record["username"],
            full_name=record["full_name"],
            role=role,
        )
        return self._current_user.to_dict()

    def logout(self):
        self._current_user = None

    def require_admin(self):
        session = self._current_user
        if session is None or session.role != "admin":
            raise AuthorizationError("Chức năng này chỉ dành cho Admin.")
        # Kiểm tra lại trạng thái và vai trò ngay trước mỗi thao tác quản trị.
        latest = self.user_dao.find_by_id(session.user_id)
        if not latest or not bool(latest["is_active"]) or latest["role"] != "admin":
            self.logout()
            raise AuthorizationError("Phiên Admin không còn hợp lệ. Vui lòng đăng nhập lại.")
        return session

    def list_users(self):
        self.require_admin()
        return self.user_dao.list_users()

    def add_user(self, username, full_name, password, role):
        self.require_admin()
        username = username.strip()
        full_name = full_name.strip()
        role = role.strip().lower()
        if not _USERNAME.fullmatch(username):
            raise ValueError("Tên đăng nhập dài 3–50 ký tự, chỉ gồm chữ, số, _, . hoặc -.")
        if not full_name or len(full_name) > 120:
            raise ValueError("Họ tên phải có từ 1 đến 120 ký tự.")
        if role not in ("admin", "user"):
            raise ValueError("Vai trò phải là Admin hoặc User.")
        pw_bytes = password.encode("utf-8")
        if len(password) < 8 or len(pw_bytes) > 72:
            raise ValueError("Mật khẩu cần ít nhất 8 ký tự và tối đa 72 byte UTF-8.")
        if self.user_dao.find_by_username(username) is not None:
            raise ValueError("Tên đăng nhập đã tồn tại.")
        password_hash = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")
        return self.user_dao.create_user(username, full_name, password_hash, role)

    def set_user_active(self, user_id, is_active):
        session = self.require_admin()
        self.user_dao.set_active(int(user_id), bool(is_active), session.user_id)
