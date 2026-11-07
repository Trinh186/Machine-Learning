"""
Lớp dịch vụ (service layer): giao diện CHỈ gọi dữ liệu qua đây, không gọi MySQL trực tiếp.

Hiện tại dùng hybrid_service (dữ liệu mẫu + model K-Means thật). Khi phần DAO xong,
chỉ cần đổi dòng import bên dưới thành:
    from . import db_service as _data_service

SafeService bọc ngoài để lỗi MySQL (mất kết nối, database rỗng) không làm văng app:
giao diện chuyển sang dữ liệu mẫu và MainWindow hiện thanh cảnh báo có nút "Thử lại".
"""

from . import hybrid_service as _data_service
from . import mock_service as _fallback_service
from .safe_service import SafeService

service = SafeService(_data_service, fallback=_fallback_service)