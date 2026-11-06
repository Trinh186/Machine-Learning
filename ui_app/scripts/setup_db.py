"""Thiết lập MySQL cho app lần đầu: tạo .env, tạo database, nạp database.sql, tạo Admin.

Chạy từ thư mục ui_app:  python -m scripts.setup_db
Chạy lại nhiều lần vẫn an toàn: bước nào đã xong thì bỏ qua, không xóa dữ liệu cũ.
"""
import re
import sys
from getpass import getpass
from pathlib import Path

import mysql.connector

UI_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = UI_DIR / ".env"
SQL_PATH = UI_DIR.parent / "customer_segmentation" / "database" / "database.sql"
N_TABLES = 8


def read_env():
    cfg = {"DB_HOST": "127.0.0.1", "DB_PORT": "3306", "DB_USER": "root",
           "DB_PASSWORD": "", "DB_NAME": "customer_segmentation"}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    return cfg


def write_env(cfg):
    ENV_PATH.write_text("".join(f"{k}={v}\n" for k, v in cfg.items()), encoding="utf-8")


def connect(cfg, database=None):
    return mysql.connector.connect(
        host=cfg["DB_HOST"], port=int(cfg["DB_PORT"]), user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"], database=database,
        charset="utf8mb4", use_unicode=True, connection_timeout=5,
    )


def ask_login(cfg):
    user = input(f"Tài khoản MySQL [{cfg['DB_USER']}]: ").strip()
    if user:
        cfg["DB_USER"] = user
    cfg["DB_PASSWORD"] = getpass("Mật khẩu MySQL (gõ xong nhấn Enter, màn hình không hiện ký tự): ")


def get_connection(cfg):
    if not ENV_PATH.exists():
        print("Chưa có file .env, nhập thông tin MySQL của máy bạn (thường là root và mật khẩu đặt lúc cài MySQL).")
        ask_login(cfg)
    for _ in range(3):
        try:
            conn = connect(cfg)
            write_env(cfg)
            return conn
        except mysql.connector.Error as exc:
            if exc.errno == 1045:
                print("Sai tài khoản hoặc mật khẩu MySQL, nhập lại.")
                ask_login(cfg)
                continue
            print(f"Không kết nối được MySQL ở {cfg['DB_HOST']}:{cfg['DB_PORT']} ({exc}).")
            print("Kiểm tra MySQL Server đã cài và đang chạy: mở Services, tìm MySQL80 (hoặc MySQL...), bấm Start.")
            sys.exit(1)
    print("Nhập sai mật khẩu 3 lần, dừng lại.")
    sys.exit(1)


def sql_statements(text):
    for chunk in re.split(r";[ \t]*\r?\n", text):
        lines = [ln for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip().rstrip(";")
        if stmt:
            yield stmt


def main():
    cfg = read_env()
    conn = get_connection(cfg)
    db = cfg["DB_NAME"]
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (db,))
    n_tables = cur.fetchone()[0]
    conn.database = db

    if n_tables < N_TABLES:
        print(f"Đang nạp {SQL_PATH.name} vào database {db} ...")
        for stmt in sql_statements(SQL_PATH.read_text(encoding="utf-8")):
            cur.execute(stmt)
        conn.commit()
        print("Đã tạo các bảng.")
    else:
        print(f"Database {db} đã có đủ bảng, bỏ qua bước nạp.")

    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
    n_admin = cur.fetchone()[0]
    cur.close()
    conn.close()

    if n_admin == 0:
        print("\nChưa có tài khoản Admin, tạo tài khoản để đăng nhập app:")
        from scripts import create_admin   # import sau khi .env đã có
        create_admin.main()
    else:
        print(f"Đã có {n_admin} tài khoản Admin.")


if __name__ == "__main__":
    main()
