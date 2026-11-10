import sys

if "--demo" in sys.argv[1:]:
    print("Che do Demo da bi vo hieu hoa.", file=sys.stderr)
    sys.exit(2)


from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from ui.LoginMainWindowEx import LoginMainWindowEx
from app.main_window import MainWindow
from app import theme
from auth.auth_service import AuthService
from services import service
from dao.database import DatabaseError
from services.db_health import OK


def load_stylesheet(app: QApplication):
    # style.qss + ảnh hoa lá trong ui/assets (xem app/theme.py)
    theme.load_stylesheet(app)
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
        if service.check() != OK:
            self.auth.logout()
            QMessageBox.critical(
                self.login_window,
                "MySQL not ready",
                "Official mode requires MySQL data.\n" + service.message
            )
            return
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

    def handle_gui_error(exc_type, exc_value, exc_tb):
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)

        if issubclass(exc_type, DatabaseError):
            message = (
                "Mat ket noi MySQL. Ung dung se dong de tranh "
                "hien thi du lieu khong day du."
            )
        else:
            message = (
                "Ung dung gap loi. Vui long xem chi tiet "
                "trong terminal."
            )

        QMessageBox.critical(None, "RFM Insight - Loi", message)
        app.quit()

    sys.excepthook = handle_gui_error

    controller = AppController()
    controller.show_login()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
