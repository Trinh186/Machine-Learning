"""
Chạy thử giao diện (chưa cần MySQL):
    python main.py              -> đăng nhập giả với quyền Admin
    python main.py --role user  -> đăng nhập giả với quyền User (ẩn User Management)

Khi màn Login của Trinh xong, Login sẽ tạo MainWindow(user, service) thay cho FAKE_USER bên dưới.
"""

import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.paths import UI_DIR
from services import service

FAKE_USERS = {
    "admin": {"username": "admin", "full_name": "Admin Demo", "role": "Admin"},
    "user": {"username": "user01", "full_name": "User Demo", "role": "User"},
}


def load_stylesheet(app: QApplication):
    app.setStyleSheet((UI_DIR / "style.qss").read_text(encoding="utf-8"))


def main():
    role = "user" if "--role" in sys.argv and sys.argv[-1].lower() == "user" else "admin"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_stylesheet(app)

    window = MainWindow(user=FAKE_USERS[role], service=service)
    window.logout_requested.connect(app.quit)   # tạm thời: thoát app; sau này quay về màn Login
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
