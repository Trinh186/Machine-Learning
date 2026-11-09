
from pathlib import Path
from datetime import date
import math

import joblib
import numpy as np
import pandas as pd

from . import mock_service
from segment_colors import segment_color


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT / "customer_segmentation" / "outputs"

DATA_DIR = ROOT / "customer_segmentation" / "datasets" / "processed"

MODEL_PATH = OUTPUT_DIR / "kmeans_model.joblib"
SCALER_PATH = OUTPUT_DIR / "rfm_scaler.joblib"
INFO_PATH = OUTPUT_DIR / "model_info.joblib"
KMEANS_METRICS_PATH = OUTPUT_DIR / "kmeans_metrics_k2_10.csv"
CLUSTERS_PATH = DATA_DIR / "customer_clusters.csv"

FEATURES = ["recency", "frequency", "monetary"]


class RFMModelService:

    def __init__(self):
        # Load mô hình K-Means thật
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        self.info = joblib.load(INFO_PATH)

        # Kiểm tra tính tương thích của mô hình
        if self.model.n_clusters != 2:
            raise ValueError("Mô hình phải có K = 2.")

        if self.info.get("features") != FEATURES:
            raise ValueError("Thứ tự đặc trưng RFM không khớp.")

        if self.info.get("transform") != "log1p":
            raise ValueError("Phép biến đổi phải là log1p.")

        if self.scaler.n_features_in_ != 3:
            raise ValueError("Scaler phải có 3 đặc trưng.")

        # Kiểm tra mapping cluster
        self.cluster_mapping = self.info.get("cluster_mapping", {})

        if set(self.cluster_mapping.keys()) != {0, 1}:
            raise ValueError("cluster_mapping phải có cluster 0 và 1.")

        # Đọc kết quả phân cụm thật
        if not CLUSTERS_PATH.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file dữ liệu: {CLUSTERS_PATH}"
            )

        self.customer_clusters = pd.read_csv(CLUSTERS_PATH)

        required_columns = [
            "customer_id",
            "recency",
            "frequency",
            "monetary",
            "cluster"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in self.customer_clusters.columns
        ]

        if missing_columns:
            raise ValueError(
                f"customer_clusters.csv thiếu cột: {missing_columns}"
            )

        self.customer_clusters["cluster"] = (
            self.customer_clusters["cluster"].astype(int)
        )

        # Lấy thông tin mô tả/màu sắc từ mock theo TÊN phân khúc,
        # tuyệt đối không ghép theo cluster ID cũ.
        mock_segments = mock_service.get_segments()

        self.segment_details = {
            s["segment_name_en"]: s
            for s in mock_segments
        }

    # ========================================================
    # TASK 11 - MODEL INFORMATION
    # ========================================================

    
    def get_model_info(self):
        info = dict(self.info)

        # Chuyển reference_date thành date object cho UI
        reference_date = info.get("reference_date")

        if isinstance(reference_date, str):
            info["reference_date"] = date.fromisoformat(reference_date)
        elif isinstance(reference_date, date):
            pass
        else:
            raise ValueError(
                "reference_date trong model_info không hợp lệ."
            )

        # Đọc chỉ số đánh giá K-Means thật từ CSV
        if not KMEANS_METRICS_PATH.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {KMEANS_METRICS_PATH}"
            )

        metrics_df = pd.read_csv(KMEANS_METRICS_PATH)

        required_columns = ["k", "inertia", "silhouette"]

        missing_columns = [
            col for col in required_columns
            if col not in metrics_df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"kmeans_metrics_k2_10.csv thiếu cột: {missing_columns}"
            )

        metrics_df = metrics_df.sort_values("k")

        info["k_search"] = [
            {
                "k": int(row["k"]),
                "inertia": float(row["inertia"]),
                "silhouette": float(row["silhouette"])
            }
            for _, row in metrics_df.iterrows()
        ]

        return info


    # ========================================================
    # TASK 11 - REAL SEGMENT INFORMATION
    # ========================================================

    
    def get_segments(self):
        """Lấy thông tin phân khúc từ model thật và thống kê RFM mới."""

        segments = []

        # Tính thống kê trực tiếp từ customer_clusters.csv
        grouped = self.customer_clusters.groupby("cluster").agg(
            customers=("customer_id", "count"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            revenue=("monetary", "sum")
        )

        total_customers = len(self.customer_clusters)
        total_revenue = self.customer_clusters["monetary"].sum()

        # Định dạng số theo cách viết tiếng Việt
        def format_vi(value):
            return (
                f"{value:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        for cluster in sorted(self.cluster_mapping.keys()):

            mapping = self.cluster_mapping[cluster]

            segment_name = mapping["segment_name_vi"]
            segment_name_en = mapping["segment_name_en"]

            if cluster not in grouped.index:
                continue

            stats = grouped.loc[cluster]

            customer_pct = (
                stats["customers"] / total_customers * 100
            )

            revenue_pct = (
                stats["revenue"] / total_revenue * 100
                if total_revenue > 0 else 0
            )

            # Lấy màu sắc và chiến lược marketing theo tên phân khúc
            details = self.segment_details.get(
                segment_name_en, {}
            )

            # Tạo mô tả dựa trên dữ liệu mới
            if segment_name_en == "High-Value Customers":
                behavior = "Mua gần đây, thường xuyên và có giá trị chi tiêu cao"
            else:
                behavior = "Lâu chưa quay lại, mua ít và có giá trị chi tiêu thấp"

            description = (
                f"{behavior} "
                f"(Recency TB {format_vi(stats['avg_recency'])} ngày), "
                f"(Frequency TB {format_vi(stats['avg_frequency'])} hóa đơn), "
                f"(Monetary TB £{format_vi(stats['avg_monetary'])}). "
                f"Chiếm {format_vi(customer_pct)}% khách hàng, "
                f"{format_vi(revenue_pct)}% doanh thu."
            )

            segments.append({
                "cluster": int(cluster),
                "segment_name": segment_name,
                "segment_name_en": segment_name_en,
                "description": description,
                "marketing_strategy": details.get(
                    "marketing_strategy",
                    "Theo dõi hành vi mua hàng và xây dựng chiến dịch phù hợp."
                ),
                "color": details.get("color", segment_color(segment_name_en))
            })

        return segments


    # ========================================================
    # TASK 11 - REAL RFM CUSTOMER TABLE
    # ========================================================

    def get_rfm_table(
        self,
        keyword="",
        cluster=None,
        page=1,
        page_size=50
    ):
        df = self.customer_clusters.copy()

        # Lọc theo cluster
        if cluster is not None:
            df = df[df["cluster"] == int(cluster)]

        # Tìm kiếm theo Customer ID
        keyword = str(keyword or "").strip()

        if keyword:
            df = df[
                df["customer_id"].astype(str).str.contains(
                    keyword,
                    case=False,
                    regex=False
                )
            ]

        total_rows = len(df)

        # Phân trang
        page = max(1, int(page))
        page_size = max(1, int(page_size))

        start = (page - 1) * page_size
        end = start + page_size

        page_df = df.iloc[start:end]

        # Mapping tên phân khúc từ model_info thật
        segments = {
            s["cluster"]: s
            for s in self.get_segments()
        }

        rows = []

        for _, row in page_df.iterrows():
            cluster_id = int(row["cluster"])
            segment = segments[cluster_id]

            rows.append({
                "customer_id": int(row["customer_id"]),
                "recency": float(row["recency"]),
                "frequency": float(row["frequency"]),
                "monetary": float(row["monetary"]),
                "cluster": cluster_id,
                "segment_name": segment["segment_name"],
                "segment_name_en": segment["segment_name_en"]
            })

        return {
            "rows": rows,
            "total_rows": total_rows
        }

    # ========================================================
    # TASK 11 - K-MEANS PREDICTION
    # ========================================================

    def predict_cluster(self, recency, frequency, monetary):

        if recency < 0:
            raise ValueError("Recency không được âm.")

        if frequency < 1:
            raise ValueError("Frequency phải từ 1 trở lên.")

        if monetary < 0:
            raise ValueError("Monetary không được âm.")

        rfm = pd.DataFrame(
            [[recency, frequency, monetary]],
            columns=FEATURES
        )

        rfm_log = np.log1p(rfm)

        rfm_scaled = self.scaler.transform(rfm_log)

        cluster = self.model.predict(rfm_scaled)[0]

        return int(cluster)

    def predict_segment(self, recency, frequency, monetary):

        cluster = self.predict_cluster(
            recency,
            frequency,
            monetary
        )

        segments = {
            s["cluster"]: s
            for s in self.get_segments()
        }

        if cluster not in segments:
            raise ValueError(
                f"Không tìm thấy thông tin cho cluster {cluster}."
            )

        # Khoảng cách từ khách hàng đến tâm từng cluster
        rfm = pd.DataFrame(
            [[recency, frequency, monetary]],
            columns=FEATURES
        )

        rfm_log = np.log1p(rfm)
        rfm_scaled = self.scaler.transform(rfm_log)

        distances_array = self.model.transform(rfm_scaled)[0]

        distances = {
            int(i): float(distance)
            for i, distance in enumerate(distances_array)
        }

        return {
            **segments[cluster],
            "distances": distances
        }
