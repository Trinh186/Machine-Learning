"""
MainWindow: khung chính + menu điều hướng + phân quyền hiển thị menu.

Cách Login (Task 7) mở cửa sổ này sau khi đăng nhập thành công:
    win = MainWindow(user={"username": "admin", "full_name": "Nguyễn Văn A", "role": "Admin"},
                     service=service)
    win.logout_requested.connect(<hàm quay lại màn Login>)
    win.show()
"""

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QMainWindow

from app.pages.dashboard_page import DashboardPage
from app.pages.placeholder_page import PlaceholderPage
from app.paths import UI_DIR

# key, nút trên menu, tiêu đề, mô tả, chỉ Admin?
PAGES = [
    ("dashboard", "btnNavDashboard", "Dashboard",
     "Overview of customers, revenue and segments", False),
    ("transactions", "btnNavTransactions", "Transaction Data",
     "Browse, search and filter transaction records", False),
    ("rfm_model", "btnNavRfmModel", "RFM & Model",
     "RFM values, K-Means evaluation and segment prediction", False),
    ("segmentation", "btnNavSegmentation", "Customer Segmentation",
     "Customers grouped by segment", False),
    ("marketing", "btnNavMarketing", "Cluster Analysis & Marketing Action Center",
     "Cluster profiles and recommended marketing actions", False),
    ("users", "btnNavUsers", "User Management",
     "View, add, lock and unlock user accounts", True),
]


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user: dict, service, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_DIR / "main_window.ui", self)
        self.user = user
        self.service = service
        self.is_admin = str(user.get("role", "")).lower() == "admin"

        self._pages = {}          # key -> widget trong stackPages
        self._meta = {}           # key -> (title, subtitle)
        self.navGroup = QButtonGroup(self)
        self.navGroup.setExclusive(True)

        for key, btn_name, title, subtitle, admin_only in PAGES:
            button = getattr(self, btn_name)
            if admin_only and not self.is_admin:
                button.hide()
                continue
            page = self._create_page(key, title)
            self.stackPages.addWidget(page)
            self._pages[key] = page
            self._meta[key] = (title, subtitle)
            self.navGroup.addButton(button)
            button.clicked.connect(lambda _checked, k=key: self.show_page(k))

        if not self.is_admin:
            self.lblAdminSection.hide()

        self._fill_user_box()
        self._fill_data_range()
        self.btnLogout.clicked.connect(self.logout_requested.emit)
        self.show_page("dashboard")

    # ---------- tạo trang ----------
    def _create_page(self, key, title):
        if key == "dashboard":
            return DashboardPage(self.service)
        # Các trang còn lại sẽ thay bằng trang thật khi làm Task 11, 12 (Hằng) và Task 9 (Trinh)
        return PlaceholderPage(title, "This screen is under construction.")

    # ---------- điều hướng ----------
    def show_page(self, key: str):
        if key not in self._pages:
            return
        self.stackPages.setCurrentWidget(self._pages[key])
        title, subtitle = self._meta[key]
        self.lblPageTitle.setText(title)
        self.lblPageSubtitle.setText(subtitle)
        for k, btn_name, *_ in PAGES:
            if k == key:
                getattr(self, btn_name).setChecked(True)

    # ---------- thông tin người dùng / dữ liệu ----------
    def _fill_user_box(self):
        self.lblUserName.setText(self.user.get("full_name") or self.user.get("username", ""))
        self.lblUserRole.setText("Administrator" if self.is_admin else "User")

    def _fill_data_range(self):
        stats = self.service.get_dashboard_stats()
        self.lblDataRange.setText(
            f"Data: {stats['date_from']:%d/%m/%Y} – {stats['date_to']:%d/%m/%Y}")
