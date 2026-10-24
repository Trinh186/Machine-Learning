"""Chạy thủ công riêng giao diện Login theo cấu trúc Ui -> Ui*.py -> *Ex.py.

Từ thư mục ui_app chạy:
    python -m tests.test_login

Không thay thế ui_app/main.py và không được tự chạy khi unittest discover import file.
"""
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from app.paths import UI_DIR
from auth.auth_service import AuthService
from ui.LoginMainWindowEx import LoginMainWindowEx


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet((UI_DIR / "style.qss").read_text(encoding="utf-8"))

    window = QMainWindow()

    def on_login_success(user: dict):
        QMessageBox.information(
            window,
            "Đăng nhập thành công",
            f"Xin chào {user['full_name']}!\nVai trò: {user['role']}",
        )
        window.close()

    login_form = LoginMainWindowEx(AuthService(), on_login_success)
    login_form.setupUi(window)
    login_form.showWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
