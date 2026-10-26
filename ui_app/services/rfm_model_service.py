from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Thư mục gốc Machine-Learning-main
ROOT = Path(__file__).resolve().parents[2]

# Thư mục chứa mô hình K-Means
OUTPUT_DIR = ROOT / "customer_segmentation" / "outputs"

FEATURES = ["recency", "frequency", "monetary"]


class RFMModelService:
    def __init__(self):
        self.model = joblib.load(
            OUTPUT_DIR / "kmeans_model.joblib"
        )

        self.scaler = joblib.load(
            OUTPUT_DIR / "rfm_scaler.joblib"
        )

        self.info = joblib.load(
            OUTPUT_DIR / "model_info.joblib"
        )

        if self.model.n_clusters != 2:
            raise ValueError("Mô hình phải có K = 2.")

        if self.info.get("features") != FEATURES:
            raise ValueError("Thứ tự đặc trưng RFM không khớp.")

        if self.info.get("transform") != "log1p":
            raise ValueError("Phép biến đổi phải là log1p.")

        if self.scaler.n_features_in_ != 3:
            raise ValueError("Scaler phải có 3 đặc trưng.")

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