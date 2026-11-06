# -*- coding: utf-8 -*-
"""
rfm_analyzer.py — Xây dựng, phân tích và chuẩn hóa RFM (mục 3.3, thiết kế lớp ở mục 4.5.1).

Đầu vào : datasets/processed/Online Retail_cleaned.xlsx (kết quả data_preprocessor.py của Task 1-2)
Đầu ra  : datasets/processed/rfm_customers.csv   RFM gốc: customer_id, recency, frequency, monetary
          datasets/processed/rfm_scaled.csv      customer_id, 3 cột *_log, 3 cột *_scaled
          outputs/rfm_excluded_customers.csv     khách hàng không đủ điều kiện tính RFM và lý do
          outputs/rfm_analysis_tables.xlsx       (tùy chọn --tables) các bảng số liệu của mục 3.3

Quy tắc RFM thống nhất với data_preprocessor.py (bản cập nhật hoàn hàng):
  - Dữ liệu sạch giữ cả dòng hoàn hàng chưa khớp được (Quantity < 0, TotalAmount < 0).
  - Recency và Frequency chỉ tính trên dòng mua (total_amount > 0, tương đương Quantity > 0
    vì UnitPrice luôn > 0).
  - Monetary là tổng total_amount của mọi dòng, kể cả hoàn hàng chưa khớp (doanh thu ròng).
  - Chỉ khách hàng có ít nhất 1 hóa đơn mua và Monetary > 0 được đưa vào RFM
    (trùng cột RFMEligible trong customer_net_summary.csv).
  - Reference Date = ngày của giao dịch cuối cùng + 1 ngày (10/12/2011).

Chạy từ thư mục customer_segmentation:
    python rfm/rfm_analyzer.py
    python rfm/rfm_analyzer.py --tables
    python rfm/rfm_analyzer.py --input "datasets/processed/Online Retail_cleaned.xlsx"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "datasets" / "processed"
OUTPUT_DIR = ROOT / "outputs"
DEFAULT_INPUT = PROCESSED_DIR / "Online Retail_cleaned.xlsx"

RFM_COLUMNS = ["recency", "frequency", "monetary"]
LOG_COLUMNS = [f"{c}_log" for c in RFM_COLUMNS]
SCALED_COLUMNS = [f"{c}_scaled" for c in RFM_COLUMNS]
REQUIRED_COLUMNS = ["customer_id", "invoice_no", "invoice_date", "total_amount"]
IQR_FACTOR = 1.5

# Tên cột trong tệp dữ liệu sạch -> tên cột theo quy ước của nhóm.
COLUMN_MAPPING = {
    "InvoiceNo": "invoice_no", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "UnitPrice": "unit_price",
    "CustomerID": "customer_id", "Country": "country", "TotalAmount": "total_amount",
}


def load_transactions(file_path: str | Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Đọc tệp dữ liệu sạch (.xlsx/.csv), giữ mã dạng chuỗi và đổi tên cột theo quy ước."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp dữ liệu sạch: {path}")
    dtype = {"InvoiceNo": str, "StockCode": str}
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=dtype)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=dtype)
    else:
        raise ValueError(f"Định dạng tệp không được hỗ trợ: {path.suffix}")
    df = df.rename(columns=COLUMN_MAPPING)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    return df


class RFMAnalyzer:
    """Tổng hợp giao dịch sạch thành RFM theo customer_id, phân tích, log1p và StandardScaler."""

    def __init__(self, transactions: pd.DataFrame | None = None, reference_date=None):
        self.transactions = transactions
        self.reference_date: pd.Timestamp | None = (
            pd.Timestamp(reference_date).normalize() if reference_date is not None else None
        )
        self.rfm_df: pd.DataFrame | None = None
        self.rfm_log_df: pd.DataFrame | None = None
        self.rfm_scaled_df: pd.DataFrame | None = None
        self.excluded_df: pd.DataFrame | None = None
        self.scaler: StandardScaler | None = None

    # ------------------------------------------------------------ xây dựng RFM
    def _validate_input(self) -> None:
        if self.transactions is None or self.transactions.empty:
            raise ValueError("Chưa có dữ liệu giao dịch để tính RFM.")
        missing = [c for c in REQUIRED_COLUMNS if c not in self.transactions.columns]
        if missing:
            raise ValueError(f"Dữ liệu thiếu cột bắt buộc: {', '.join(missing)}")

    def determine_reference_date(self) -> pd.Timestamp:
        """Ngày của giao dịch cuối cùng + 1 ngày; không dùng ngày hệ thống (mục 3.3.1a)."""
        if self.reference_date is None:
            last = pd.to_datetime(self.transactions["invoice_date"]).max()
            self.reference_date = last.normalize() + pd.Timedelta(days=1)
        return self.reference_date

    def calculate_rfm(self) -> pd.DataFrame:
        """Recency, Frequency từ dòng mua; Monetary là doanh thu ròng của mọi dòng."""
        self._validate_input()
        ref = self.determine_reference_date()
        df = self.transactions[REQUIRED_COLUMNS].copy()
        df["invoice_date"] = pd.to_datetime(df["invoice_date"])
        purchases = df[df["total_amount"] > 0]
        g = purchases.groupby("customer_id")

        rfm = pd.DataFrame({
            "last_purchase": g["invoice_date"].max(),
            "frequency": g["invoice_no"].nunique(),
        }).reindex(df["customer_id"].unique())
        rfm.index.name = "customer_id"
        rfm["monetary"] = df.groupby("customer_id")["total_amount"].sum().round(2)
        rfm["frequency"] = rfm["frequency"].fillna(0).astype("int64")

        no_purchase = rfm["frequency"].eq(0)
        non_positive = ~no_purchase & rfm["monetary"].le(0)
        self.excluded_df = rfm.loc[no_purchase | non_positive, ["frequency", "monetary"]].reset_index()
        self.excluded_df["reason"] = np.where(
            self.excluded_df["frequency"].eq(0),
            "Chỉ có dòng hoàn hàng, không có hóa đơn mua",
            "Monetary ròng <= 0 (đã hoàn toàn bộ hoặc nhiều hơn giá trị mua)")
        self.excluded_df = self.excluded_df.sort_values("customer_id").reset_index(drop=True)

        rfm = rfm.loc[~(no_purchase | non_positive)].copy()
        rfm["recency"] = (ref - rfm["last_purchase"].dt.normalize()).dt.days.astype("int64")
        self.rfm_df = rfm.reset_index()[["customer_id"] + RFM_COLUMNS] \
            .sort_values("customer_id").reset_index(drop=True)
        return self.rfm_df

    # ---------------------------------------------------------------- phân tích
    def describe_rfm(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        """Trung bình, độ lệch chuẩn, min, Q1, trung vị, Q3, P95, P99, max (Bảng 3.3.3)."""
        data = self.rfm_df[RFM_COLUMNS] if data is None else data
        return data.describe(percentiles=[0.25, 0.5, 0.75, 0.95, 0.99]).T

    @staticmethod
    def analyze_distribution(data: pd.DataFrame) -> pd.DataFrame:
        """Skewness, kurtosis, ngưỡng IQR và số outlier cho từng cột (Bảng 3.3.4, 3.3.6)."""
        rows = []
        for col in data.columns:
            s = data[col]
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            low, high = q1 - IQR_FACTOR * iqr, q3 + IQR_FACTOR * iqr
            n_out = int(((s < low) | (s > high)).sum())
            rows.append((col, s.skew(), s.kurt(), low, high, n_out, n_out / len(s) * 100))
        return pd.DataFrame(rows, columns=["feature", "skewness", "kurtosis",
                                           "lower_bound", "upper_bound", "outliers", "outlier_pct"])

    def get_top_customers(self, n: int = 5, by: str = "monetary") -> pd.DataFrame:
        return self.rfm_df.nlargest(n, by).reset_index(drop=True)

    def compute_correlation(self, use_log: bool = False) -> pd.DataFrame:
        data = self.rfm_log_df[LOG_COLUMNS] if use_log else self.rfm_df[RFM_COLUMNS]
        return data.corr(method="pearson")

    def compute_histogram(self, feature: str, bin_edges: list[float]) -> pd.DataFrame:
        """Số khách hàng theo khoảng; khoảng đầu và khoảng cuối để mở, tổng phải đủ số khách hàng."""
        source = self.rfm_log_df if feature.endswith("_log") else self.rfm_df
        s = source[feature]
        edges = [-np.inf] + list(bin_edges[1:-1]) + [np.inf]
        counts = pd.cut(s, bins=edges, right=False).value_counts(sort=False)
        labels = ([f"< {bin_edges[1]:g}"]
                  + [f"{a:g}–{b:g}" for a, b in zip(bin_edges[1:-2], bin_edges[2:-1])]
                  + [f">= {bin_edges[-2]:g}"])
        table = pd.DataFrame({"bin": labels, "customers": counts.to_numpy()})
        if table["customers"].sum() != len(s):
            raise ValueError(f"Histogram {feature} không phủ đủ {len(s)} khách hàng.")
        return table

    # ------------------------------------------------------ biến đổi, chuẩn hóa
    def apply_log_transform(self) -> pd.DataFrame:
        """x' = ln(1 + x) cho cả ba đặc trưng (mục 3.3.4)."""
        self.rfm_log_df = self.rfm_df[["customer_id"]].copy()
        self.rfm_log_df[LOG_COLUMNS] = np.log1p(self.rfm_df[RFM_COLUMNS].to_numpy(dtype=float))
        return self.rfm_log_df

    def compare_scalers(self) -> pd.DataFrame:
        """Fit thử StandardScaler và RobustScaler trên dữ liệu sau log (Bảng 3.3.7)."""
        x = self.rfm_log_df[LOG_COLUMNS].to_numpy()
        rows = []
        for name, sc in (("StandardScaler", StandardScaler()), ("RobustScaler", RobustScaler())):
            z = sc.fit_transform(x)
            for i, col in enumerate(RFM_COLUMNS):
                rows.append((name, col, z[:, i].mean(), z[:, i].std(), z[:, i].min(), z[:, i].max()))
        return pd.DataFrame(rows, columns=["scaler", "feature", "mean", "std", "min", "max"])

    def fit_scaler(self) -> pd.DataFrame:
        """Fit StandardScaler trên toàn bộ khách hàng và tạo ba cột *_scaled (mục 3.3.5)."""
        self.scaler = StandardScaler()
        z = self.scaler.fit_transform(self.rfm_log_df[LOG_COLUMNS].to_numpy())
        self.rfm_scaled_df = self.rfm_log_df.copy()
        self.rfm_scaled_df[SCALED_COLUMNS] = z
        return self.rfm_scaled_df

    def transform_new(self, rfm_values: pd.DataFrame) -> np.ndarray:
        """Biến đổi RFM gốc của khách hàng mới bằng scaler đã fit, không fit lại."""
        if self.scaler is None:
            raise RuntimeError("Scaler chưa được fit hoặc tải.")
        data = rfm_values[RFM_COLUMNS].astype(float)
        if (data["recency"] < 0).any() or (data["frequency"] < 1).any() or (data["monetary"] < 0).any():
            raise ValueError("Giá trị RFM không hợp lệ: recency >= 0, frequency >= 1, monetary >= 0.")
        return self.scaler.transform(np.log1p(data.to_numpy()))

    def get_model_input(self) -> np.ndarray:
        """Ma trận n × 3 đã chuẩn hóa, đầu vào của K-Means."""
        return self.rfm_scaled_df[SCALED_COLUMNS].to_numpy()

    # --------------------------------------------------------------- lưu, xuất
    def save_scaler(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.scaler, path)
        return path

    def load_scaler(self, file_path: str | Path) -> StandardScaler:
        self.scaler = joblib.load(file_path)
        return self.scaler

    def export_rfm(self, rfm_path: str | Path, scaled_path: str | Path) -> None:
        """Xuất rfm_customers.csv (RFM gốc) và rfm_scaled.csv (*_log, *_scaled)."""
        for path in (rfm_path, scaled_path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.rfm_df.to_csv(rfm_path, index=False)
        self.rfm_scaled_df.to_csv(scaled_path, index=False)

    def export_analysis_tables(self, file_path: str | Path) -> Path:
        """Xuất các bảng số liệu của mục 3.3 thành một workbook Excel."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        stats = self.describe_rfm()
        stats["skewness"] = self.rfm_df[RFM_COLUMNS].skew()
        stats["kurtosis"] = self.rfm_df[RFM_COLUMNS].kurt()
        outliers = pd.concat([
            self.analyze_distribution(self.rfm_df[RFM_COLUMNS]).assign(data="raw"),
            self.analyze_distribution(self.rfm_log_df[LOG_COLUMNS]).assign(data="log1p"),
        ])
        with pd.ExcelWriter(path) as writer:
            self.rfm_df.to_excel(writer, sheet_name="RFM_Customers", index=False)
            self.rfm_scaled_df.to_excel(writer, sheet_name="RFM_Scaled", index=False)
            stats.T.to_excel(writer, sheet_name="Thong_ke_mo_ta")
            outliers.to_excel(writer, sheet_name="Outlier_IQR", index=False)
            self.compare_scalers().to_excel(writer, sheet_name="So_sanh_Scaler", index=False)
            self.get_top_customers().to_excel(writer, sheet_name="Top5_Monetary", index=False)
            pd.concat({"raw": self.compute_correlation(), "log1p": self.compute_correlation(True)}) \
                .to_excel(writer, sheet_name="Tuong_quan")
            self.excluded_df.to_excel(writer, sheet_name="Khach_hang_loai", index=False)
        return path

    def to_rfm_profiles(self) -> pd.DataFrame:
        """RFM gốc kèm reference_date theo cấu trúc bảng rfm_profiles."""
        out = self.rfm_df.copy()
        out["reference_date"] = self.reference_date.date()
        return out

    def run_pipeline(self) -> pd.DataFrame:
        self.calculate_rfm()
        self.apply_log_transform()
        self.fit_scaler()
        return self.rfm_scaled_df


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Tính RFM từ dữ liệu sạch và xuất rfm_customers.csv, rfm_scaled.csv.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Tệp dữ liệu sạch (.xlsx/.csv)")
    parser.add_argument("--out-dir", default=str(PROCESSED_DIR), help="Thư mục ghi hai tệp RFM")
    parser.add_argument("--tables", action="store_true", help="Xuất thêm outputs/rfm_analysis_tables.xlsx")
    args = parser.parse_args(argv)

    print("Đang đọc dữ liệu sạch, vui lòng chờ...", flush=True)
    transactions = load_transactions(args.input)
    analyzer = RFMAnalyzer(transactions)
    analyzer.run_pipeline()

    out_dir = Path(args.out_dir)
    analyzer.export_rfm(out_dir / "rfm_customers.csv", out_dir / "rfm_scaled.csv")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    analyzer.excluded_df.to_csv(OUTPUT_DIR / "rfm_excluded_customers.csv", index=False, encoding="utf-8-sig")
    if args.tables:
        analyzer.export_analysis_tables(OUTPUT_DIR / "rfm_analysis_tables.xlsx")

    n_all = transactions["customer_id"].nunique()
    print(f"Reference Date        : {analyzer.reference_date:%d/%m/%Y}")
    print(f"Khách hàng trong dữ liệu sạch: {n_all:,}")
    print(f"Khách hàng có RFM     : {len(analyzer.rfm_df):,}")
    print(f"Khách hàng bị loại    : {len(analyzer.excluded_df):,} (xem outputs/rfm_excluded_customers.csv)")
    print(analyzer.describe_rfm().round(2).to_string())
    print("μ sau log :", np.round(analyzer.scaler.mean_, 3))
    print("σ sau log :", np.round(analyzer.scaler.scale_, 3))
    print(f"Đã ghi: {out_dir / 'rfm_customers.csv'}")
    print(f"Đã ghi: {out_dir / 'rfm_scaled.csv'}")


if __name__ == "__main__":
    main()
