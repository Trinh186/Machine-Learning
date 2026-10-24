import sys

from PyQt6.QtWidgets import QApplication, QMainWindow

from ui.LoginMainWindowEx import LoginMainWindowEx
from app.main_window import MainWindow
from app.paths import UI_DIR
from auth.auth_service import AuthService
from services import service


def load_stylesheet(app: QApplication):
    app.setStyleSheet((UI_DIR / "style.qss").read_text(encoding="utf-8"))
class AppController:
    def __init__(self):
        self.auth = AuthService()
        self.login_window = None
        self.main_window = None

    def show_login(self):
        self.login_window = QMainWindow()
        self.login_form = LoginMainWindowEx(self.auth, self.open_main)
        self.login_form.setupUi(self.login_window)
        self.login_form.showWindow()

    def open_main(self, user):
        self.main_window = MainWindow(
            user=user, service=service, auth_service=self.auth,
        )
        self.main_window.logout_requested.connect(self.logout)
        self.main_window.show()
        old = self.login_window
        self.login_window = None
        self.login_form = None
        if old:
            old.close()

    def logout(self):
        self.auth.logout()
        old = self.main_window
        self.show_login()
        self.main_window = None
        if old:
            old.close()
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_stylesheet(app)

    if "--demo" in sys.argv:
        role = "user" if "--role" in sys.argv else "admin"
        fake = {
            "username": "demo", "full_name": "Demo " + role.title(),
            "role": role,
        }
        window = MainWindow(user=fake, service=service)
        window.logout_requested.connect(app.quit)
        window.show()
    else:
        controller = AppController()
        controller.show_login()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
