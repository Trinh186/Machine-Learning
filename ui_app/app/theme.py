"""
Theme hồng – tím: nạp style.qss (thay @ASSETS@ bằng đường dẫn thật) và gắn icon cho nút.

- Màu & hình nền hoa lá: ui/style.qss  (ảnh trong ui/assets/)
- Icon: ui/assets/icons/<tên>_<light|white|accent>.svg
    light  = trên sidebar tối,  white = trên nút chính (primary),  accent = trên nút phụ (secondary)
"""
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget

from app.paths import UI_DIR

ASSET_DIR = UI_DIR / "assets"
ICON_DIR = ASSET_DIR / "icons"

# Màu dùng chung cho code (biểu đồ, thẻ...) — giữ khớp với style.qss
ACCENT = "#A23E9C"
ACCENT_DARK = "#7E2E7E"
PINK = "#E0559B"
LAVENDER = "#8E5CC4"

NAV_ICONS = {
    "btnNavDashboard": "dashboard",
    "btnNavTransactions": "transactions",
    "btnNavRfmModel": "rfm_model",
    "btnNavSegmentation": "segmentation",
    "btnNavMarketing": "marketing",
    "btnNavUsers": "users",
    "btnLogout": "logout",
}

# objectName của nút -> (icon, biến thể màu)
BUTTON_ICONS = {
    "btnSearch": ("search", "white"),
    "btnRfmSearch": ("search", "white"),
    "btnPredict": ("sparkle", "white"),
    "btnExportTarget": ("download", "white"),
    "btnExportCsv": ("download", "accent"),
    "btnReset": ("reset", "accent"),
    "btnClearPredict": ("reset", "accent"),
    "btnViewTarget": ("segmentation", "accent"),
    # User Management (Trinh)
    "btnAddUser": ("user_plus", "accent"),
    "btnRefresh": ("reset", "accent"),
    "btnLockUser": ("lock", "accent"),
    "btnUnlockUser": ("unlock", "accent"),
}


def icon(name: str, variant: str = "accent") -> QIcon:
    return QIcon(str(ICON_DIR / f"{name}_{variant}.svg"))


def load_stylesheet(app: QApplication):
    qss = (UI_DIR / "style.qss").read_text(encoding="utf-8")
    app.setStyleSheet(qss.replace("@ASSETS@", ASSET_DIR.as_posix()))


def apply_icons(root: QWidget):
    """Gắn icon cho menu và các nút đã biết tên (gọi sau khi tạo xong các trang)."""
    for button in root.findChildren(QPushButton):
        name = button.objectName()
        if name in NAV_ICONS:
            button.setIcon(icon(NAV_ICONS[name], "light"))
            button.setIconSize(QSize(17, 17))
        elif name in BUTTON_ICONS:
            ic, variant = BUTTON_ICONS[name]
            button.setIcon(icon(ic, variant))
            button.setIconSize(QSize(16, 16))


def logo_html(text: str) -> str:
    """Tên app kèm bông hoa nhỏ (QLabel rich text)."""
    return (f'<img src="{(ASSET_DIR / "logo_flower.svg").as_posix()}" width="26" height="26" '
            f'style="vertical-align: middle;">&nbsp;{text}')
