"""
Khởi chạy RFM Insight chỉ với 1 lần bấm (được gọi từ CHAY_APP.bat).

App chỉ chạy với dữ liệu thật trong MySQL (không còn chế độ Demo). Cần MySQL Server đang chạy.

Lần đầu:  tạo môi trường .venv -> cài thư viện theo ui_app/requirements.txt
          -> thiết lập MySQL (tạo .env, database, các bảng, tài khoản Admin)
          -> nạp dữ liệu vào MySQL nếu database còn trống (import_mysql.py, khoảng 1–2 phút)
          -> mở app
Lần sau:  các bước đã xong được bỏ qua, app mở ngay.

Chạy trực tiếp:  python launcher.py
Chỉ dùng thư viện chuẩn của Python, chạy được trước khi cài gì.
"""
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

MIN_PY = (3, 11)
ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui_app"
CS_DIR = ROOT / "customer_segmentation"
REQ = UI_DIR / "requirements.txt"
VENV = ROOT / ".venv"
MARKER = VENV / ".requirements.sha256"
IS_WIN = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def say(msg=""):
    print(msg, flush=True)


def ask(prompt, choices):
    while True:
        try:
            ans = input(prompt).strip().lower()
        except EOFError:
            return choices[0]
        if ans in choices:
            return ans
        say(f"   Vui long nhap: {' / '.join(choices)}")


def requirements_hash():
    return hashlib.sha256(REQ.read_bytes()).hexdigest()


def ensure_venv():
    if VENV_PY.exists():
        return
    say("[1/4] Tao moi truong Python rieng cho app (.venv) ...")
    venv.EnvBuilder(with_pip=True, clear=False).create(VENV)


def ensure_packages():
    wanted = requirements_hash()
    if MARKER.exists() and MARKER.read_text().strip() == wanted:
        return
    say("[2/4] Cai thu vien (chi lan dau, can Internet, mat khoang 3-5 phut) ...")
    cmd = [str(VENV_PY), "-m", "pip", "install", "--disable-pip-version-check",
           "--progress-bar", "on", "-r", str(REQ)]
    if subprocess.call(cmd) != 0:
        say("\n*** Cai thu vien that bai. Kiem tra ket noi Internet roi chay lai. ***")
        sys.exit(1)
    MARKER.write_text(wanted)


def run_in_ui(args):
    """Chạy python của .venv trong thư mục ui_app (ẩn cảnh báo phiên bản scikit-learn)."""
    return subprocess.call([str(VENV_PY), "-W", "ignore", *args], cwd=UI_DIR)


def database_is_empty():
    """True nếu MySQL kết nối được nhưng chưa có dữ liệu (cần chạy import_mysql.py)."""
    code = run_in_ui(["-c", "import sys; from services.db_health import check_database, EMPTY; "
                            "sys.exit(3 if check_database()[0] == EMPTY else 0)"])
    return code == 3


def ensure_mysql():
    say("\n[3/4] Kiem tra MySQL, database va tai khoan Admin ...")
    if run_in_ui(["-m", "scripts.setup_db"]) != 0:
        say("\n*** Khong thiet lap duoc MySQL (xem thong bao phia tren). "
            "App can MySQL Server dang chay. ***")
        return False
    if database_is_empty():
        say("\n[4/4] Nap du lieu vao MySQL (chi lan dau, khoang 1-2 phut) ...")
        code = subprocess.call([str(VENV_PY), "-W", "ignore", "database/import_mysql.py"], cwd=CS_DIR)
        if code != 0:
            say("\n*** Nap du lieu that bai (xem thong bao phia tren). ***")
            return False
    return True


def main(argv):
    if "--demo" in argv:
        say("Che do Demo da bi vo hieu hoa.")
        return 2
    if sys.version_info < MIN_PY:
        say(f"Can Python {MIN_PY[0]}.{MIN_PY[1]} tro len (dang dung {sys.version.split()[0]}).")
        return 1
    if not REQ.exists():
        say(f"Khong tim thay {REQ}. Hay dat file nay o thu muc goc Machine-Learning.")
        return 1

    ensure_venv()
    ensure_packages()
    if not ensure_mysql():
        return 1
    say("\nDang mo ung dung ...")
    code = run_in_ui(["main.py"])
    return 0 if code in (0, None) else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
