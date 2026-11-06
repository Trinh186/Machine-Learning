# -*- coding: utf-8 -*-
"""
import_mysql.py — Nạp dữ liệu sạch và kết quả phân cụm vào MySQL (Task 5).

Nguồn dữ liệu (đều nằm trong customer_segmentation/):
    datasets/processed/Online Retail_cleaned.xlsx   dữ liệu sạch của data_preprocessor.py (Task 1-2)
    datasets/processed/rfm_customers.csv            RFM của rfm/rfm_analyzer.py (Task 4)
    customer_clusters.csv                           nhãn cụm của models/clustering_model.py --k 2,
                                                    tìm ở outputs/ rồi datasets/processed/
    outputs/kmeans_model.joblib, rfm_scaler.joblib  chỉ dùng khi chưa có customer_clusters.csv khớp
                                                    với rfm_customers.csv

Bảng đích (database/database.sql): customers, products, invoices, invoice_details,
rfm_profiles, customer_segments. Bảng segments và users KHÔNG bị thay đổi.

Quy tắc ánh xạ:
  - invoice_details có CHECK quantity > 0 nên chỉ nhận các dòng mua (Quantity > 0).
    Dòng hoàn hàng chưa khớp (Quantity < 0) vẫn được tính vào Monetary ròng của rfm_profiles
    nhưng không được ghi thành dòng hóa đơn; số dòng và số tiền được in ra để đối chiếu.
  - customers, products, invoices được rút ra từ chính các dòng mua đó:
      customers.country      = quốc gia xuất hiện nhiều nhất của khách hàng
      products.description   = mô tả xuất hiện nhiều nhất của mã hàng
      invoices.invoice_date  = thời điểm sớm nhất của hóa đơn
  - customer_segments.cluster được khớp với bảng segments theo hồ sơ cụm: cụm có trung vị
    Monetary cao hơn ứng với phân khúc "High-Value Customers", nhờ đó số hiệu cụm của
    K-Means có đổi sau khi huấn luyện lại thì vẫn ghi đúng phân khúc.

Toàn bộ thao tác ghi chạy trong MỘT giao dịch: lỗi ở bất kỳ bước nào thì rollback, dữ liệu cũ giữ nguyên.
Thông tin kết nối đọc từ ui_app/.env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME),
giống ui_app/dao/database.py.

Chạy từ thư mục customer_segmentation:
    python database/import_mysql.py --dry-run     # chỉ chuẩn bị và kiểm tra, không ghi MySQL
    python database/import_mysql.py               # kiểm tra rồi nạp vào MySQL
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rfm.rfm_analyzer import RFM_COLUMNS, RFMAnalyzer, load_transactions  # noqa: E402

PROCESSED_DIR = ROOT / "datasets" / "processed"
OUTPUT_DIR = ROOT / "outputs"
ENV_PATH = ROOT.parent / "ui_app" / ".env"
DEFAULT_INPUT = PROCESSED_DIR / "Online Retail_cleaned.xlsx"
DEFAULT_RFM = PROCESSED_DIR / "rfm_customers.csv"
CLUSTER_FILES = [OUTPUT_DIR / "customer_clusters.csv", PROCESSED_DIR / "customer_clusters.csv"]
HIGH_VALUE_NAME_EN = "High-Value Customers"
BATCH_SIZE = 5000

# Thứ tự ghi bảo đảm khóa ngoại luôn trỏ tới bản ghi đã tồn tại; xóa theo thứ tự ngược lại.
INSERT_ORDER = ["customers", "products", "invoices", "invoice_details", "rfm_profiles", "customer_segments"]
DELETE_ORDER = list(reversed(INSERT_ORDER))
TABLE_COLUMNS = {
    "customers": ["customer_id", "country"],
    "products": ["stock_code", "description"],
    "invoices": ["invoice_no", "customer_id", "invoice_date"],
    "invoice_details": ["invoice_no", "stock_code", "quantity", "unit_price", "total_amount"],
    "rfm_profiles": ["customer_id", "recency", "frequency", "monetary", "reference_date"],
    "customer_segments": ["customer_id", "cluster"],
}
VARCHAR_LIMITS = {("customers", "country"): 100, ("products", "stock_code"): 20,
                  ("products", "description"): 255, ("invoices", "invoice_no"): 20,
                  ("invoice_details", "invoice_no"): 20, ("invoice_details", "stock_code"): 20}


# ============================================================== chuẩn bị dữ liệu
def _mode(series: pd.Series):
    """Giá trị xuất hiện nhiều nhất; hòa thì lấy giá trị nhỏ nhất theo thứ tự chữ cái."""
    counts = series.value_counts()
    return sorted(counts[counts == counts.max()].index)[0]


def split_sales_tables(transactions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Tách các dòng mua của dữ liệu sạch thành 4 bảng giao dịch theo database.sql."""
    sales = transactions[transactions["quantity"] > 0].copy()
    customers = sales.groupby("customer_id")["country"].agg(_mode).reset_index()
    products = sales.groupby("stock_code")["description"].agg(_mode).reset_index()
    invoices = (sales.groupby("invoice_no")
                .agg(customer_id=("customer_id", "first"), invoice_date=("invoice_date", "min"))
                .reset_index())
    details = sales[TABLE_COLUMNS["invoice_details"]].copy()
    details["unit_price"] = details["unit_price"].round(4)
    details["total_amount"] = (details["quantity"] * details["unit_price"]).round(4)
    return {"customers": customers, "products": products, "invoices": invoices,
            "invoice_details": details.reset_index(drop=True)}


def load_rfm(transactions: pd.DataFrame, rfm_path: Path) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Đọc rfm_customers.csv của Task 4 và kiểm tra lại bằng RFMAnalyzer trên cùng dữ liệu sạch."""
    analyzer = RFMAnalyzer(transactions)
    expected = analyzer.calculate_rfm()
    if not rfm_path.is_file():
        print(f"  ! Chưa có {rfm_path.name}, dùng RFM vừa tính bằng RFMAnalyzer.")
        return expected, analyzer.reference_date
    rfm = pd.read_csv(rfm_path)[["customer_id"] + RFM_COLUMNS].sort_values("customer_id")
    same = (len(rfm) == len(expected)
            and rfm["customer_id"].to_numpy().tolist() == expected["customer_id"].tolist()
            and np.allclose(rfm[RFM_COLUMNS].to_numpy(float), expected[RFM_COLUMNS].to_numpy(float)))
    if not same:
        raise ValueError(f"{rfm_path.name} không khớp dữ liệu sạch hiện tại. "
                         "Hãy chạy lại: python rfm/rfm_analyzer.py")
    return rfm.reset_index(drop=True), analyzer.reference_date


def load_cluster_labels(rfm: pd.DataFrame) -> tuple[pd.Series, str]:
    """Nhãn cụm cho từng customer_id: ưu tiên customer_clusters.csv khớp RFM, nếu không thì dự đoán."""
    for path in CLUSTER_FILES:
        if not path.is_file():
            continue
        clusters = pd.read_csv(path)
        merged = rfm.merge(clusters, on="customer_id", how="left", suffixes=("", "_file"))
        matches = (len(clusters) == len(rfm) and merged["cluster"].notna().all()
                   and all(np.allclose(merged[c], merged[f"{c}_file"]) for c in RFM_COLUMNS
                           if f"{c}_file" in merged))
        if matches:
            return merged.set_index("customer_id")["cluster"].astype(int), str(path.relative_to(ROOT))
        print(f"  ! {path.relative_to(ROOT)} không khớp rfm_customers.csv hiện tại, bỏ qua.")

    model = joblib.load(OUTPUT_DIR / "kmeans_model.joblib")
    analyzer = RFMAnalyzer()
    analyzer.load_scaler(OUTPUT_DIR / "rfm_scaler.joblib")
    labels = model.predict(analyzer.transform_new(rfm[RFM_COLUMNS]))
    source = "dự đoán bằng outputs/kmeans_model.joblib + rfm_scaler.joblib"
    current_mean = np.log1p(rfm[RFM_COLUMNS].to_numpy(float)).mean(axis=0)
    if not np.allclose(analyzer.scaler.mean_, current_mean, atol=1e-6):
        source += " (CẢNH BÁO: mô hình chưa được huấn luyện lại trên RFM hiện tại)"
    return pd.Series(labels.astype(int), index=rfm["customer_id"]), source


def align_to_segments(rfm: pd.DataFrame, labels: pd.Series, segments: pd.DataFrame) -> pd.Series:
    """Đổi nhãn K-Means sang số hiệu cluster của bảng segments theo hồ sơ cụm."""
    seg_ids = set(segments["cluster"].astype(int))
    if len(seg_ids) != labels.nunique() or len(seg_ids) != 2:
        return labels
    high_seg = segments.loc[segments["segment_name_en"] == HIGH_VALUE_NAME_EN, "cluster"]
    if len(high_seg) != 1:
        return labels
    high_seg = int(high_seg.iloc[0])
    low_seg = (seg_ids - {high_seg}).pop()
    medians = rfm.set_index("customer_id")["monetary"].groupby(labels).median()
    high_label = int(medians.idxmax())
    return labels.map(lambda k: high_seg if k == high_label else low_seg).astype(int)


def prepare_frames(input_path: Path, rfm_path: Path, segments: pd.DataFrame) -> tuple[dict, dict]:
    print("• Đọc dữ liệu sạch (khoảng 1 phút)...", flush=True)
    transactions = load_transactions(input_path)
    print("• Tách bảng customers, products, invoices, invoice_details...", flush=True)
    frames = split_sales_tables(transactions)
    print("• Đọc và kiểm tra rfm_customers.csv...", flush=True)
    rfm, reference_date = load_rfm(transactions, rfm_path)
    print("• Lấy nhãn cụm...", flush=True)
    labels, label_source = load_cluster_labels(rfm)
    clusters = align_to_segments(rfm, labels, segments)

    frames["rfm_profiles"] = rfm.assign(reference_date=reference_date.date())
    frames["customer_segments"] = pd.DataFrame({"customer_id": clusters.index, "cluster": clusters.to_numpy()})
    frames = {t: frames[t][TABLE_COLUMNS[t]].reset_index(drop=True) for t in INSERT_ORDER}

    returns = transactions[transactions["quantity"] < 0]
    info = {
        "label_source": label_source,
        "reference_date": reference_date,
        "clean_rows": len(transactions),
        "clean_customers": transactions["customer_id"].nunique(),
        "net_revenue": round(float(transactions["total_amount"].sum()), 2),
        "sales_revenue": round(float(transactions.loc[transactions["quantity"] > 0, "total_amount"].sum()), 2),
        "return_rows": len(returns),
        "return_amount": round(float(returns["total_amount"].sum()), 2),
        "return_only_customers": sorted(set(transactions["customer_id"]) - set(frames["customers"]["customer_id"])),
        "segments": segments,
    }
    return frames, info


# ====================================================================== kiểm tra
def validate(frames: dict, info: dict) -> list[dict]:
    checks = []

    def check(name, expected, actual, passed):
        checks.append({"Kiểm tra": name, "Kỳ vọng": expected, "Thực tế": actual, "Đạt": bool(passed)})

    for table, key in [("customers", "customer_id"), ("products", "stock_code"), ("invoices", "invoice_no"),
                       ("rfm_profiles", "customer_id"), ("customer_segments", "customer_id")]:
        dup = int(frames[table][key].duplicated().sum())
        check(f"PK {table}.{key} không trùng", 0, dup, dup == 0)

    segment_ids = info["segments"]["cluster"]
    fks = [("invoices", "customer_id", frames["customers"]["customer_id"]),
           ("invoice_details", "invoice_no", frames["invoices"]["invoice_no"]),
           ("invoice_details", "stock_code", frames["products"]["stock_code"]),
           ("rfm_profiles", "customer_id", frames["customers"]["customer_id"]),
           ("customer_segments", "customer_id", frames["customers"]["customer_id"]),
           ("customer_segments", "cluster", segment_ids)]
    for table, col, parent in fks:
        orphans = int((~frames[table][col].isin(parent)).sum())
        check(f"FK {table}.{col}", 0, orphans, orphans == 0)

    d, r = frames["invoice_details"], frames["rfm_profiles"]
    check("CHECK quantity > 0", 0, int((d["quantity"] <= 0).sum()), (d["quantity"] > 0).all())
    check("CHECK unit_price > 0", 0, int((d["unit_price"] <= 0).sum()), (d["unit_price"] > 0).all())
    check("CHECK recency >= 0", 0, int((r["recency"] < 0).sum()), (r["recency"] >= 0).all())
    check("CHECK frequency >= 1", 0, int((r["frequency"] < 1).sum()), (r["frequency"] >= 1).all())
    check("CHECK monetary >= 0", 0, int((r["monetary"] < 0).sum()), (r["monetary"] >= 0).all())
    nulls = sum(int(frames[t].isna().sum().sum()) for t in INSERT_ORDER)
    check("Không có giá trị NULL", 0, nulls, nulls == 0)
    for (table, col), limit in VARCHAR_LIMITS.items():
        longest = int(frames[table][col].astype(str).str.len().max())
        check(f"Độ dài {table}.{col} <= {limit}", f"<= {limit}", longest, longest <= limit)

    sales = round(float(d["total_amount"].sum()), 2)
    check("Tổng invoice_details.total_amount = doanh thu dòng mua", info["sales_revenue"], sales,
          abs(sales - info["sales_revenue"]) < 0.01)
    invoices_per_customer = frames["invoices"].groupby("customer_id").size()
    same_freq = r.set_index("customer_id")["frequency"].eq(invoices_per_customer.reindex(r["customer_id"])).all()
    check("frequency = số hóa đơn của khách hàng trong invoices", "khớp", "khớp" if same_freq else "lệch", same_freq)
    check("rfm_profiles và customer_segments cùng tập khách hàng", len(r), len(frames["customer_segments"]),
          set(r["customer_id"]) == set(frames["customer_segments"]["customer_id"]))
    return checks


# ======================================================================= MySQL
def db_config() -> dict:
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass
    user = os.getenv("DB_USER", "").strip()
    if not user:
        raise SystemExit(f"Chưa cấu hình DB_USER trong {ENV_PATH}")
    return {"host": os.getenv("DB_HOST", "127.0.0.1").strip(), "port": int(os.getenv("DB_PORT", "3306")),
            "user": user, "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "customer_segmentation").strip(),
            "charset": "utf8mb4", "use_unicode": True, "connection_timeout": 10}


def _py(value):
    """Đổi kiểu NumPy/pandas sang kiểu Python mà mysql-connector hiểu được."""
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return round(value, 4)
    return value


def read_segments(conn) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute("SELECT cluster, segment_name_en FROM segments ORDER BY cluster")
    rows = cur.fetchall()
    cur.close()
    if not rows:
        raise SystemExit("Bảng segments đang trống. Hãy chạy database/database.sql trước khi nạp dữ liệu.")
    return pd.DataFrame(rows, columns=["cluster", "segment_name_en"])


def load_into_mysql(conn, frames: dict) -> dict:
    """Thay toàn bộ dữ liệu của 6 bảng trong một giao dịch."""
    import mysql.connector

    conn.autocommit = False
    cur = conn.cursor()
    try:
        for table in DELETE_ORDER:
            cur.execute(f"DELETE FROM {table}")
        for table in INSERT_ORDER:
            cols = TABLE_COLUMNS[table]
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
            rows = [tuple(_py(v) for v in row) for row in frames[table].itertuples(index=False, name=None)]
            for start in range(0, len(rows), BATCH_SIZE):
                cur.executemany(sql, rows[start:start + BATCH_SIZE])
            print(f"  {table:<18} {len(rows):>9,} dòng", flush=True)
        conn.commit()
    except mysql.connector.Error:
        conn.rollback()
        raise
    finally:
        cur.close()

    cur = conn.cursor()
    counts = {}
    for table in INSERT_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = int(cur.fetchone()[0])
    cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoice_details")
    counts["revenue"] = float(cur.fetchone()[0])
    cur.close()
    return counts


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Nạp dữ liệu sạch, RFM và phân khúc vào MySQL.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Tệp dữ liệu sạch (.xlsx/.csv)")
    parser.add_argument("--rfm", default=str(DEFAULT_RFM), help="Tệp rfm_customers.csv")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ chuẩn bị và kiểm tra, không ghi MySQL")
    args = parser.parse_args(argv)

    conn = None
    if args.dry_run:
        segments = pd.DataFrame({"cluster": [0, 1], "segment_name_en": [HIGH_VALUE_NAME_EN, "Low-Activity Customers"]})
    else:
        import mysql.connector
        conn = mysql.connector.connect(**db_config())
        segments = read_segments(conn)

    try:
        frames, info = prepare_frames(Path(args.input), Path(args.rfm), segments)
        checks = pd.DataFrame(validate(frames, info))
        pd.set_option("display.width", 160)
        print("\nNGUỒN NHÃN CỤM:", info["label_source"])
        print(f"Reference Date : {info['reference_date']:%d/%m/%Y}")
        print(f"Dữ liệu sạch   : {info['clean_rows']:,} dòng, {info['clean_customers']:,} khách hàng, "
              f"doanh thu ròng {info['net_revenue']:,.2f}")
        print(f"Dòng mua       : {len(frames['invoice_details']):,} dòng, doanh thu {info['sales_revenue']:,.2f}")
        print(f"Hoàn hàng chưa khớp (không ghi vào invoice_details): {info['return_rows']:,} dòng, "
              f"{info['return_amount']:,.2f}")
        print(f"Khách hàng chỉ có dòng hoàn hàng (không có trong customers): {len(info['return_only_customers'])}")
        print("Quy mô phân khúc:", frames["customer_segments"]["cluster"].value_counts().sort_index().to_dict())
        print("\nKIỂM TRA TRƯỚC KHI NẠP")
        print(checks.to_string(index=False))
        if not checks["Đạt"].all():
            raise SystemExit("\nCó kiểm tra không đạt, KHÔNG nạp dữ liệu.")
        if args.dry_run:
            print("\nDry run: dữ liệu hợp lệ, chưa ghi vào MySQL.")
            return

        print("\nĐANG NẠP VÀO MYSQL (một giao dịch)...", flush=True)
        counts = load_into_mysql(conn, frames)
        expected = {t: len(frames[t]) for t in INSERT_ORDER}
        ok = all(counts[t] == expected[t] for t in INSERT_ORDER) \
            and abs(counts["revenue"] - info["sales_revenue"]) < 0.01
        print(f"Doanh thu trong MySQL: {counts['revenue']:,.2f}")
        print("HOÀN TẤT: số dòng trong MySQL khớp dữ liệu đã chuẩn bị." if ok
              else "CẢNH BÁO: số dòng trong MySQL không khớp, hãy kiểm tra lại.")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
