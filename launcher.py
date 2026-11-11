"""
Khởi chạy RFM Insight chỉ với 1 lần bấm (được gọi từ CHAY_APP.bat).

Lần đầu:  tạo môi trường .venv  ->  cài thư viện theo ui_app/requirements.txt  ->  mở app
Lần sau:  mở app ngay (chỉ cài lại khi requirements.txt thay đổi)

Hai chế độ:
  1. Đầy đủ  — có màn Đăng nhập, cần MySQL Server (tự tạo .env, database, tài khoản Admin lần đầu)
  2. Demo    — xem toàn bộ giao diện với dữ liệu mẫu, KHÔNG cần MySQL

Chạy trực tiếp:  python launcher.py            (hiện menu chọn chế độ)
                 python launcher.py --demo     (vào thẳng chế độ demo)
                 python launcher.py --full     (vào thẳng chế độ đầy đủ)
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
    say("[1/3] Tao moi truong Python rieng cho app (.venv) ...")
    venv.EnvBuilder(with_pip=True, clear=False).create(VENV)


def ensure_packages():
    wanted = requirements_hash()
    if MARKER.exists() and MARKER.read_text().strip() == wanted:
        return
    say("[2/3] Cai thu vien (chi lan dau, can Internet, mat khoang 3-5 phut) ...")
    cmd = [str(VENV_PY), "-m", "pip", "install", "--disable-pip-version-check",
           "--progress-bar", "on", "-r", str(REQ)]
    if subprocess.call(cmd) != 0:
        say("\n*** Cai thu vien that bai. Kiem tra ket noi Internet roi chay lai. ***")
        sys.exit(1)
    MARKER.write_text(wanted)


def run_in_ui(args):
    """Chạy python của .venv trong thư mục ui_app (ẩn cảnh báo phiên bản scikit-learn)."""
    return subprocess.call([str(VENV_PY), "-W", "ignore", *args], cwd=UI_DIR)


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
    say("\nDang mo ung dung chinh thuc ...")
    code = run_in_ui(["main.py"])
    return 0 if code in (0, None) else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
