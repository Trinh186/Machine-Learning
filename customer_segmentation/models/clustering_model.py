
# -*- coding: utf-8 -*-
"""
clustering_model.py
Task 8: Huấn luyện K-Means K=2 trên dữ liệu RFM.
Task 9: Lưu kết quả phân cụm customer_clusters.csv.
Task 11: Lưu chỉ số đánh giá phục vụ giao diện.

Quy trình:
RFM -> log1p -> StandardScaler -> K-Means
"""

import argparse
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score,
    silhouette_samples,
    davies_bouldin_score,
    calinski_harabasz_score,
)
from sklearn.preprocessing import StandardScaler


# =========================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "datasets" / "processed"
OUTPUT_DIR = ROOT / "outputs"

RFM_PATH = DATA_DIR / "rfm_customers.csv"

CLUSTERS_PATH = DATA_DIR / "customer_clusters.csv"

RANDOM_STATE = 42

K_RANGE = range(2, 11)

FINAL_K = 2

FEATURES = ["recency", "frequency", "monetary"]

REFERENCE_DATE = "2011-12-10"


# =========================================================
# 2. ĐỌC VÀ CHUẨN HÓA DỮ LIỆU RFM
# =========================================================

def load_and_scale(rfm_path=RFM_PATH):

    rfm = pd.read_csv(rfm_path)

    required_columns = ["customer_id"] + FEATURES

    missing = [
        col for col in required_columns
        if col not in rfm.columns
    ]

    if missing:
        raise ValueError(
            f"Thiếu cột dữ liệu RFM: {missing}"
        )

    if rfm["customer_id"].duplicated().any():
        raise ValueError(
            "customer_id bị trùng."
        )

    if rfm[FEATURES].isna().any().any():
        raise ValueError(
            "Dữ liệu RFM có giá trị thiếu."
        )

    if (rfm[FEATURES] < 0).any().any():
        raise ValueError(
            "Dữ liệu RFM không được có giá trị âm."
        )

    if (rfm["frequency"] < 1).any():
        raise ValueError(
            "Frequency phải lớn hơn hoặc bằng 1."
        )

    scaler = StandardScaler()

    X = scaler.fit_transform(
        np.log1p(rfm[FEATURES])
    )

    return rfm, scaler, X


# =========================================================
# 3. ĐÁNH GIÁ K-MEANS VỚI K TỪ 2 ĐẾN 10
# =========================================================

def evaluate_k(X):

    rows = []

    for k in K_RANGE:

        model = KMeans(
            n_clusters=k,
            n_init=10,
            random_state=RANDOM_STATE
        )

        labels = model.fit_predict(X)

        sil_samples = silhouette_samples(
            X,
            labels
        )

        rows.append({

            "k": k,

            "inertia": float(model.inertia_),

            "silhouette": float(
                silhouette_score(X, labels)
            ),

            "davies_bouldin": float(
                davies_bouldin_score(X, labels)
            ),

            "calinski_harabasz": float(
                calinski_harabasz_score(X, labels)
            ),

            "negative_silhouette_count": int(
                (sil_samples < 0).sum()
            ),

            "min_cluster_pct": float(
                np.bincount(labels).min()
                / len(labels) * 100
            )
        })

    metrics = pd.DataFrame(rows)

    metrics["inertia_drop_pct"] = (
        -metrics["inertia"].pct_change() * 100
    )

    return metrics


# =========================================================
# 4. VẼ BIỂU ĐỒ ĐÁNH GIÁ
# =========================================================

def plot_metrics(metrics, out_dir, k_chosen=FINAL_K):

    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Elbow Method

    plt.figure(figsize=(8, 5))

    plt.plot(
        metrics["k"],
        metrics["inertia"],
        marker="o"
    )

    plt.axvline(
        k_chosen,
        linestyle="--",
        label=f"K = {k_chosen}"
    )

    plt.xlabel("Number of clusters (K)")
    plt.ylabel("Inertia")

    plt.title("Elbow Method")

    plt.xticks(metrics["k"])

    plt.grid(alpha=0.3)

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        out_dir / "elbow_curve.png",
        dpi=150
    )

    plt.close()

    # Silhouette và Davies-Bouldin

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(13, 5)
    )

    axes[0].plot(
        metrics["k"],
        metrics["silhouette"],
        marker="o"
    )

    axes[0].set_title("Silhouette Score")

    axes[0].set_xlabel("K")

    axes[0].set_ylabel("Silhouette")

    axes[1].plot(
        metrics["k"],
        metrics["davies_bouldin"],
        marker="o"
    )

    axes[1].set_title("Davies-Bouldin Index")

    axes[1].set_xlabel("K")

    axes[1].set_ylabel("Davies-Bouldin")

    for ax in axes:

        ax.set_xticks(metrics["k"])

        ax.grid(alpha=0.3)

        ax.axvline(
            k_chosen,
            linestyle="--"
        )

    plt.tight_layout()

    plt.savefig(
        out_dir / "silhouette_dbi_chart.png",
        dpi=150
    )

    plt.close()


# =========================================================
# 5. XÁC ĐỊNH TÊN PHÂN KHÚC
# =========================================================

def create_cluster_mapping(rfm, labels):

    temp = rfm[["monetary"]].copy()

    temp["cluster"] = labels

    medians = temp.groupby(
        "cluster"
    )["monetary"].median()

    high_value_cluster = int(
        medians.idxmax()
    )

    mapping = {}

    for cluster in sorted(medians.index):

        cluster = int(cluster)

        if cluster == high_value_cluster:

            mapping[cluster] = {
                "segment_name_vi": "Khách hàng giá trị cao",
                "segment_name_en": "High-Value Customers"
            }

        else:

            mapping[cluster] = {
                "segment_name_vi": "Khách hàng ít hoạt động",
                "segment_name_en": "Low-Activity Customers"
            }

    return mapping


# =========================================================
# 6. HUẤN LUYỆN MÔ HÌNH K-MEANS CUỐI CÙNG
# =========================================================

def fit_final(
    rfm,
    scaler,
    X,
    k=FINAL_K,
    out_dir=OUTPUT_DIR,
    clusters_path=CLUSTERS_PATH,
    metrics=None
):

    if k < 2 or k >= len(rfm):
        raise ValueError("K không hợp lệ.")

    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    clusters_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    model = KMeans(
        n_clusters=k,
        n_init=10,
        random_state=RANDOM_STATE
    )

    labels = model.fit_predict(X)

    # Tạo bảng kết quả phân cụm

    result = rfm[
        ["customer_id"] + FEATURES
    ].copy()

    result["cluster"] = labels

    # Lưu đúng vị trí để cluster_evaluation.py đọc được

    result.to_csv(
        clusters_path,
        index=False
    )

    # Xác định tên phân khúc

    cluster_mapping = create_cluster_mapping(
        rfm,
        labels
    )

    # Tính các chỉ số đánh giá K cuối cùng

    sil_samples = silhouette_samples(
        X,
        labels
    )

    model_metrics = {

        "inertia": float(model.inertia_),

        "silhouette": float(
            silhouette_score(X, labels)
        ),

        "davies_bouldin": float(
            davies_bouldin_score(X, labels)
        ),

        "calinski_harabasz": float(
            calinski_harabasz_score(X, labels)
        ),

        "negative_silhouette_count": int(
            (sil_samples < 0).sum()
        )
    }

    # Lưu model

    joblib.dump(
        model,
        out_dir / "kmeans_model.joblib"
    )

    # Lưu scaler

    joblib.dump(
        scaler,
        out_dir / "rfm_scaler.joblib"
    )

    # Tạo thông tin model

    model_info = {

        "k": k,

        "n_customers": len(rfm),

        "features": FEATURES,

        "transform": "log1p",

        "scaler": "StandardScaler",

        "reference_date": REFERENCE_DATE,

        "random_state": RANDOM_STATE,

        "cluster_mapping": cluster_mapping,

        **model_metrics
    }

    # Thêm dữ liệu K=2..10 phục vụ Task 11

    if metrics is not None:

        model_info["k_search"] = [

            {
                "k": int(row["k"]),

                "inertia": float(row["inertia"]),

                "silhouette": float(
                    row["silhouette"]
                )
            }

            for _, row in metrics.iterrows()
        ]

    joblib.dump(
        model_info,
        out_dir / "model_info.joblib"
    )

    # Lưu chỉ số theo định dạng metric/value
    # Giữ tương thích với file cluster_metrics.csv hiện tại

    metric_rows = [

        {
            "metric": key,
            "value": value
        }

        for key, value in model_metrics.items()

    ]


    pd.DataFrame(
        metric_rows
    ).to_csv(
        out_dir / "kmeans_model_metrics.csv",
        index=False
    )

    return model, result, model_info


# =========================================================
# 7. DỰ ĐOÁN CLUSTER CHO KHÁCH HÀNG MỚI
# =========================================================

def predict_cluster(
    df_new,
    model_dir=OUTPUT_DIR
):

    model = joblib.load(
        model_dir / "kmeans_model.joblib"
    )

    scaler = joblib.load(
        model_dir / "rfm_scaler.joblib"
    )

    missing = [
        col for col in FEATURES
        if col not in df_new.columns
    ]

    if missing:
        raise ValueError(
            f"Thiếu cột RFM: {missing}"
        )

    if df_new[FEATURES].isna().any().any():
        raise ValueError(
            "Dữ liệu dự đoán có giá trị thiếu."
        )

    if (df_new[FEATURES] < 0).any().any():
        raise ValueError(
            "Dữ liệu RFM không được âm."
        )

    if (df_new["frequency"] < 1).any():
        raise ValueError(
            "Frequency phải >= 1."
        )

    X_new = scaler.transform(
        np.log1p(df_new[FEATURES])
    )

    return model.predict(X_new)


# =========================================================
# 8. CHƯƠNG TRÌNH CHÍNH
# =========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--rfm",
        default=str(RFM_PATH)
    )

    parser.add_argument(
        "--k",
        type=int,
        default=FINAL_K
    )

    parser.add_argument(
        "--out",
        default=str(OUTPUT_DIR)
    )

    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Bước 1: Đọc và chuẩn hóa RFM

    print("\n[1/5] Loading RFM data...")

    rfm, scaler, X = load_and_scale(
        Path(args.rfm)
    )

    print(
        f"So khach hang: {len(rfm):,}"
    )

    # Bước 2: Đánh giá K=2..10

    print("\n[2/5] Evaluating K-Means K=2..10...")

    metrics = evaluate_k(X)

    metrics.to_csv(
        out_dir / "kmeans_metrics_k2_10.csv",
        index=False
    )

    print(
        metrics.round(4).to_string(index=False)
    )

    # Bước 3: Vẽ biểu đồ

    print("\n[3/5] Creating evaluation charts...")

    plot_metrics(
        metrics,
        out_dir,
        args.k
    )

    # Bước 4: Huấn luyện K cuối cùng

    print("\n[4/5] Training final K-Means model...")

    model, result, info = fit_final(
        rfm=rfm,
        scaler=scaler,
        X=X,
        k=args.k,
        out_dir=out_dir,
        clusters_path=CLUSTERS_PATH,
        metrics=metrics
    )

    # Bước 5: Hiển thị kết quả

    print("\n[5/5] Training completed!")

    print("\nModel metrics:")

    for key in [
        "inertia",
        "silhouette",
        "davies_bouldin",
        "calinski_harabasz"
    ]:

        print(
            f"{key}: {info[key]:.4f}"
        )

    print("\nCluster mapping:")

    for cluster, segment in info[
        "cluster_mapping"
    ].items():

        print(
            f"Cluster {cluster}: "
            f"{segment['segment_name_en']}"
        )

    print("\nCustomer count by cluster:")

    print(
        result["cluster"]
        .value_counts()
        .sort_index()
    )

    print("\nSaved files:")

    print(
        f"Model artifacts: {out_dir}"
    )

    print(
        f"Customer clusters: {CLUSTERS_PATH}"
    )


if __name__ == "__main__":

    main()
