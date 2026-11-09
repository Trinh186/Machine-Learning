"""
Lớp dịch vụ (service layer): giao diện CHỈ gọi dữ liệu qua đây, không gọi MySQL trực tiếp.

Dữ liệu đọc từ MySQL qua db_service (DAO + model K-Means đã lưu).

SafeService bọc ngoài để lỗi MySQL (mất kết nối, database rỗng) không làm văng app:
giao diện chuyển sang hybrid_service (dữ liệu mẫu + model K-Means) và MainWindow hiện
thanh cảnh báo có nút "Thử lại". Chế độ Demo (main.py --demo) chỉ dùng hybrid_service.
"""

from . import db_service as _data_service
from . import hybrid_service as _fallback_service
from .safe_service import SafeService

service = SafeService(_data_service, fallback=_fallback_service)