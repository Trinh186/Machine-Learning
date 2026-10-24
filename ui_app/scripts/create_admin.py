"""Chạy một lần sau khi import database.sql: python -m scripts.create_admin"""
from getpass import getpass

import bcrypt

from auth.user_dao import UserDAO, DatabaseError


def main():
    username = input("Tên đăng nhập Admin: ").strip()
    full_name = input("Họ tên: ").strip()
    if not username or len(username) > 50 or not full_name or len(full_name) > 120:
        print("Tên đăng nhập hoặc họ tên không hợp lệ.")
        return
    pwd = getpass("Mật khẩu Admin (>= 8 ký tự): ")
    pwd2 = getpass("Nhập lại mật khẩu: ")
    if pwd != pwd2 or len(pwd) < 8 or len(pwd.encode("utf-8")) > 72:
        print("Mật khẩu không khớp hoặc độ dài không hợp lệ.")
        return
    dao = UserDAO()
    try:
        if dao.find_by_username(username):
            print("Username đã tồn tại. Không ghi đè.")
            return
        h = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt(rounds=12))
        dao.create_user(username, full_name, h.decode("utf-8"), "admin")
    except (DatabaseError, ValueError) as exc:
        print(f"Không tạo được Admin: {exc}")
    else:
        print("Tạo Admin thành công. Mật khẩu không được ghi ra màn hình.")


if __name__ == "__main__":
    main()
