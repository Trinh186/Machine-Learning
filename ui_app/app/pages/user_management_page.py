"""Tên lớp tương thích cho MainWindow của nhóm.
Phần xử lý giao diện thật ở ui/pages/UserManagementPageEx.py.
"""
from ui.pages.UserManagementPageEx import UserManagementPageEx


class UserManagementPage(UserManagementPageEx):
    """Giữ API UserManagementPage(auth_service) mà MainWindow đang gọi."""
