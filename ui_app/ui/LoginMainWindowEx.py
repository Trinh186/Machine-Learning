from PyQt6.QtWidgets import QLineEdit

from auth.auth_service import AuthenticationError
from auth.user_dao import DatabaseError
from ui.LoginMainWindow import Ui_LoginMainWindow


class LoginMainWindowEx(Ui_LoginMainWindow):
    def __init__(self, auth_service, on_login_success):
        self.auth_service = auth_service
        self.on_login_success = on_login_success
        self.MainWindow = None

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.MainWindow = MainWindow
        self.setupSignalAndSlot()
        self.txtPassword.setEchoMode(QLineEdit.EchoMode.Password)
        self.lblError.setText("")
        self.txtUsername.setFocus()

    def showWindow(self):
        self.MainWindow.show()

    def setupSignalAndSlot(self):
        self.btnLogin.clicked.connect(self.process_login)
        self.btnExit.clicked.connect(self.MainWindow.close)
        self.txtUsername.returnPressed.connect(self.process_login)
        self.txtPassword.returnPressed.connect(self.process_login)

    def process_login(self):
        self.lblError.setText("")
        try:
            user = self.auth_service.login(
                self.txtUsername.text(),
                self.txtPassword.text(),
            )
        except (AuthenticationError, DatabaseError) as exc:
            self.lblError.setText(str(exc))
            self.txtPassword.clear()
            self.txtPassword.setFocus()
            return

        self.txtPassword.clear()
        self.on_login_success(user)
