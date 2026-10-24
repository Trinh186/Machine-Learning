"""Trang quản lý tài khoản. Mọi lệnh nhạy cảm đều qua AuthService."""
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QMessageBox, QTableWidgetItem, QWidget,
)
from app.paths import UI_DIR
from auth.auth_service import AuthorizationError
from auth.user_dao import DatabaseError


class UserManagementPage(QWidget):
    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.auth_service.require_admin()
        uic.loadUi(UI_DIR / "pages" / "user_management.ui", self)
        self.cboNewRole.addItem("Admin", "admin")
        self.cboNewRole.addItem("User", "user")
        self.cboNewRole.setCurrentIndex(1)

        self.tblUsers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tblUsers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tblUsers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tblUsers.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tblUsers.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        self.btnRefresh.clicked.connect(self.refresh)
        self.btnAddUser.clicked.connect(self.add_user)
        self.btnLockUser.clicked.connect(lambda: self.change_status(False))
        self.btnUnlockUser.clicked.connect(lambda: self.change_status(True))
        self.tblUsers.itemSelectionChanged.connect(self._update_buttons)
        self.refresh()

    def refresh(self):
        try:
            rows = self.auth_service.list_users()
        except (AuthorizationError, DatabaseError) as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
            return
        self.tblUsers.setRowCount(len(rows))
        for i, user in enumerate(rows):
            values = [
                str(user["user_id"]), user["username"], user["full_name"],
                user["role"].title(),
                "Hoạt động" if user["is_active"] else "Đã khóa",
                str(user["created_at"]),
            ]
            for j, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if j == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, user["user_id"])
                self.tblUsers.setItem(i, j, cell)
        self.tblUsers.clearSelection()
        self._update_buttons()

    def _selected_user(self):
        row = self.tblUsers.currentRow()
        if row < 0:
            return None
        id_item = self.tblUsers.item(row, 0)
        status_item = self.tblUsers.item(row, 4)
        if id_item is None or status_item is None or not self.tblUsers.selectedItems():
            return None
        return int(id_item.data(Qt.ItemDataRole.UserRole)), status_item.text() == "Hoạt động"

    def _update_buttons(self):
        selection = self._selected_user()
        self.btnLockUser.setEnabled(bool(selection and selection[1]))
        self.btnUnlockUser.setEnabled(bool(selection and not selection[1]))

    def add_user(self):
        try:
            self.auth_service.add_user(
                self.txtNewUsername.text(),
                self.txtNewFullName.text(),
                self.txtNewPassword.text(),
                self.cboNewRole.currentData(),
            )
        except (AuthorizationError, DatabaseError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể thêm tài khoản", str(exc))
            return
        self.txtNewUsername.clear()
        self.txtNewFullName.clear()
        self.txtNewPassword.clear()
        self.cboNewRole.setCurrentIndex(1)
        self.refresh()
        QMessageBox.information(self, "Thành công", "Đã thêm tài khoản mới.")

    def change_status(self, is_active):
        selection = self._selected_user()
        if selection is None:
            return
        user_id, current_active = selection
        if current_active == is_active:
            return
        action = "mở khóa" if is_active else "khóa"
        answer = QMessageBox.question(
            self, "Xác nhận",
            f"Bạn có chắc muốn {action} tài khoản ID {user_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.auth_service.set_user_active(user_id, is_active)
        except (AuthorizationError, DatabaseError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể cập nhật tài khoản", str(exc))
            return
        self.refresh()
        QMessageBox.information(self, "Thành công", f"Đã {action} tài khoản.")
