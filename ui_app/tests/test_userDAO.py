"""Kiểm tra UserDAO và AuthService với MySQL thật; không ghi cứng mật khẩu.

Từ thư mục ui_app chạy:
    python -m tests.test_userDAO

Không in password_hash, không lưu mật khẩu vào code.
"""
from getpass import getpass

from auth.auth_service import AuthService, AuthenticationError
from auth.user_dao import DatabaseError, UserDAO


def main():
    username = input("Username cần kiểm tra: ").strip()
    if not username:
        print("Chưa nhập username.")
        return

    dao = UserDAO()
    try:
        record = dao.find_by_username(username)
        if record is None:
            print("Không tìm thấy tài khoản.")
            return

        print("Đã đọc tài khoản từ MySQL:")
        print("  Username:", record["username"])
        print("  Vai trò:", record["role"])
        print("  Trạng thái:", "Hoạt động" if record["is_active"] else "Đã khóa")

        # Việc so mật khẩu đã băm thuộc AuthService, không thực hiện trong câu SQL.
        password = getpass("Mật khẩu để thử đăng nhập: ")
        auth = AuthService(dao)
        user = auth.login(username, password)
        print("Login thành công. Welcome:", user["full_name"])
        auth.logout()
    except (DatabaseError, AuthenticationError) as exc:
        print("Không đăng nhập được:", exc)


if __name__ == "__main__":
    main()
