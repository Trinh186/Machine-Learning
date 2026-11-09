"""
MainWindow: khung chính + menu điều hướng + phân quyền hiển thị menu.

Cách Login (Task 7) mở cửa sổ này sau khi đăng nhập thành công:
    win = MainWindow(user={"username": "admin", "full_name": "Nguyễn Văn A", "role": "Admin"},
                     service=service)
    win.logout_requested.connect(<hàm quay lại màn Login>)
    win.show()
"""

from datetime import datetime

from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QButtonGroup, QMainWindow, QMessageBox

from app.pages.cluster_marketing_page import ClusterMarketingPage
from app.pages.dashboard_page import DashboardPage
from app.pages.placeholder_page import PlaceholderPage
from app.pages.rfm_model_page import RfmModelPage
from app.pages.segmentation_page import SegmentationPage
from app.pages.transaction_page import TransactionDataPage
from app.pages.user_management_page import UserManagementPage
from app.paths import UI_DIR
from app.theme import apply_icons, logo_html
from services.db_health import DEMO, EMPTY, OK

# Các trang đọc dữ liệu qua service: tạo lại khi MySQL kết nối lại được
DATA_PAGES = ("dashboard", "transactions", "rfm_model", "segmentation", "marketing")

# key, nút trên menu, tiêu đề, mô tả, chỉ Admin?
PAGES = [
    ("dashboard", "btnNavDashboard", "Tổng quan",
     "Tổng quan khách hàng, doanh thu và phân khúc", False),
    ("transactions", "btnNavTransactions", "Dữ liệu giao dịch",
     "Xem, tìm kiếm và lọc các dòng giao dịch", False),
    ("rfm_model", "btnNavRfmModel", "RFM & Mô hình",
     "Giá trị RFM, đánh giá K-Means và dự đoán phân khúc", False),
    ("segmentation", "btnNavSegmentation", "Phân khúc khách hàng",
     "Danh sách khách hàng theo từng phân khúc", False),
    ("marketing", "btnNavMarketing", "Phân tích cụm & Trung tâm hành động Marketing",
     "Hồ sơ cụm và các hành động marketing đề xuất", False),
    ("users", "btnNavUsers", "Quản lý tài khoản",
     "Xem, thêm, khóa và mở khóa tài khoản", True),
]


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user: dict, service, parent=None, auth_service=None):
        super().__init__(parent)
        uic.loadUi(UI_DIR / "main_window.ui", self)
        self.user = user
        self.service = service
        self.auth_service = auth_service
        self.is_admin = str(user.get("role", "")).lower() == "admin"
        self._setup_db_status()

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

        apply_icons(self)                      # icon menu + nút (theme hồng – tím)
        self.lblAppName.setText(logo_html("RFM Insight"))
        self._fill_user_box()
        self._fill_data_range()
        self.btnLogout.clicked.connect(self._confirm_logout)
        self.show_page("dashboard")

    # ---------- thanh cảnh báo MySQL ----------
    def _setup_db_status(self):
        self.hostDbStatus.hide()
        self.btnDbRetry.clicked.connect(self._retry_database)
        if hasattr(self.service, "add_listener"):
            self.service.add_listener(self._on_db_status)
            self._show_db_status(self.service.status, self.service.message)

    def _on_db_status(self, status, message):
        """Trạng thái MySQL đổi trong lúc dùng app: cập nhật thanh cảnh báo, tạo lại các trang
        để toàn bộ dữ liệu trên màn hình lấy từ cùng một nguồn."""
        self._show_db_status(status, message)
        if status != OK and getattr(self, "_pages", None):   # trở lại OK thì _retry_database tự tải lại
            QTimer.singleShot(0, self._reload_data_pages)

    def _show_db_status(self, status, message):
        if status in (OK, DEMO):
            self.hostDbStatus.hide()
            return
        if status == EMPTY:
            head = "Database MySQL chưa có dữ liệu – đang hiển thị dữ liệu mẫu."
        else:
            head = "Không kết nối được MySQL – đang hiển thị dữ liệu mẫu."
        self.lblDbStatus.setText(f"{head}  {message}".strip())
        self.frameDbStatus.setProperty("state", status)
        self.frameDbStatus.style().unpolish(self.frameDbStatus)
        self.frameDbStatus.style().polish(self.frameDbStatus)
        self.hostDbStatus.show()

    def _retry_database(self):
        self.btnDbRetry.setEnabled(False)
        self.btnDbRetry.setText("Đang kiểm tra...")
        QApplication.processEvents()
        try:
            status = self.service.check()
        finally:
            self.btnDbRetry.setText("Thử lại")
            self.btnDbRetry.setEnabled(True)
        if status == OK:
            self._reload_data_pages()
        else:
            self._show_db_status(status, self.service.message)
            self.lblDbStatus.setText(self.lblDbStatus.text()
                                     + f"  (Kiểm tra lúc {datetime.now():%H:%M:%S})")

    def _reload_data_pages(self):
        """Tạo lại các trang dữ liệu để đọc lại từ MySQL, giữ nguyên trang đang xem."""
        current = next((k for k, w in self._pages.items() if w is self.stackPages.currentWidget()), "dashboard")
        for key in DATA_PAGES:
            old = self._pages.get(key)
            if old is None:
                continue
            index = self.stackPages.indexOf(old)
            new = self._create_page(key, self._meta[key][0])
            self.stackPages.insertWidget(index, new)
            self.stackPages.removeWidget(old)
            old.deleteLater()
            self._pages[key] = new
        apply_icons(self)
        self._fill_data_range()
        self.show_page(current)

    def closeEvent(self, event):
        if hasattr(self.service, "remove_listener"):
            self.service.remove_listener(self._on_db_status)
        super().closeEvent(event)

    # ---------- tạo trang ----------
    def _create_page(self, key, title):
        if key == "dashboard":
            return DashboardPage(self.service)
        if key == "transactions":
            return TransactionDataPage(self.service)
        if key == "rfm_model":
            return RfmModelPage(self.service)
        if key == "segmentation":
            return SegmentationPage(self.service)
        if key == "marketing":
            page = ClusterMarketingPage(self.service)
            page.view_customers_requested.connect(self._open_action_customers)
            return page
        if key == "users" and self.is_admin and self.auth_service is not None:
            return UserManagementPage(self.auth_service)
        return PlaceholderPage(title, "Màn hình này đang được xây dựng.")

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

    def _open_action_customers(self, cluster, target, title):
        """Marketing Action Center → mở Customer Segmentation, lọc đúng nhóm khách của hành động."""
        self._pages["segmentation"].apply_action_target(cluster, target, title)
        self.show_page("segmentation")

    # ---------- thông tin người dùng / dữ liệu ----------
    def _fill_user_box(self):
        self.lblUserName.setText(self.user.get("full_name") or self.user.get("username", ""))
        self.lblUserRole.setText("Quản trị viên" if self.is_admin else "Người dùng")

    def _fill_data_range(self):
        stats = self.service.get_dashboard_stats()
        self.lblDataRange.setText(
            f"Dữ liệu: {stats['date_from']:%d/%m/%Y} – {stats['date_to']:%d/%m/%Y}")

    # ---------- Đăng xuất ----------
    def _confirm_logout(self):
        reply = QMessageBox.question(
            self, 'Đăng xuất', 'Bạn muốn đăng xuất khỏi hệ thống?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()
