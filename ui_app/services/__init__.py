"""Production service: real MySQL data only. No demo fallback."""

from . import db_service as _data_service
from .safe_service import SafeService

service = SafeService(_data_service, fallback=None)
