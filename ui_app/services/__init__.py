"""
Lớp dịch vụ (service layer): giao diện CHỈ gọi dữ liệu qua đây, không gọi MySQL trực tiếp.

Hiện tại dùng dữ liệu giả. Khi phần DAO / model của các bạn xong:
    from . import db_service as service
"""

from . import hybrid_service as service