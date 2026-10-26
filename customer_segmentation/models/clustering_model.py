# -*- coding: utf-8 -*-
"""
clustering_model.py — Phân cụm khách hàng bằng K-Means trên dữ liệu RFM (mục 3.4).

Quy trình: rfm_customers.csv -> log1p -> StandardScaler -> thử K = 2..10
           -> K-Means với K đã chọn -> gán cluster -> lưu model/scaler.

Chạy dòng lệnh:
    python clustering_model.py --rfm rfm_customers.csv                # chỉ chạy K = 2..10 và vẽ biểu đồ
    python clustering_model.py --rfm rfm_customers.csv --k 4          # chạy thêm K-Means cuối với K = 4

Dùng lại trong ứng dụng (khách hàng mới):
    from clustering_model import predict_cluster
    predict_cluster(df_new, model_dir="outputs")     # df_new có cột recency, frequency, monetary
"""
import argparse
import os

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
K_RANGE = range(2, 11)
FEATURES = ["recency", "frequency", "monetary"]
REFERENCE_DATE = "2011-12-10"     # mục 3.3.1a


def load_and_scale(rfm_path):
    """Đọc bảng RFM (mục 3.3), log1p, StandardScaler. Trả về (rfm, scaler, X)."""
    rfm = pd.read_csv(rfm_path)
    assert rfm["customer_id"].is_unique and rfm[FEATURES].notna().all().all()
    scaler = StandardScaler()
    X = scaler.fit_transform(np.log1p(rfm[FEATURES]))
    return rfm, scaler, X


def evaluate_k(X, k_range=K_RANGE):
    """Chạy K-Means cho từng K, trả về bảng Inertia / Silhouette / Davies-Bouldin."""
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        rows.append({"K": k,
                     "Inertia": km.inertia_,
                     "Silhouette": silhouette_score(X, km.labels_),
                     "Davies_Bouldin": davies_bouldin_score(X, km.labels_),
                     "Cum_nho_nhat_pct": np.bincount(km.labels_).min() / len(X) * 100})
    m = pd.DataFrame(rows)
    m["Inertia_giam_pct"] = -m["Inertia"].pct_change() * 100
    return m


def plot_metrics(metrics, out_dir, k_chosen=None):
    """Lưu elbow_curve.png và silhouette_dbi_chart.png."""
    def mark(ax):
        if k_chosen:
            ax.axvline(k_chosen, color="gray", linestyle="--", label=f"K chọn = {k_chosen}")
            ax.legend()
        ax.set_xlabel("Số cụm K"); ax.set_xticks(list(metrics["K"])); ax.grid(alpha=0.3)

    plt.figure(figsize=(7, 4.5))
    plt.plot(metrics["K"], metrics["Inertia"], marker="o")
    plt.title("Elbow Method – Inertia (WCSS) theo K"); plt.ylabel("Inertia (WCSS)")
    mark(plt.gca()); plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "elbow_curve.png"), dpi=150); plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].plot(metrics["K"], metrics["Silhouette"], marker="o", color="green")
    axes[0].set_title("Silhouette Score (càng cao càng tốt)"); axes[0].set_ylabel("Silhouette")
    axes[1].plot(metrics["K"], metrics["Davies_Bouldin"], marker="o", color="red")
    axes[1].set_title("Davies–Bouldin Index (càng thấp càng tốt)"); axes[1].set_ylabel("Davies–Bouldin")
    for ax in axes:
        mark(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "silhouette_dbi_chart.png"), dpi=150); plt.close()


def fit_final(rfm, scaler, X, k, out_dir):
    """K-Means cuối với K đã chọn, gán cluster, lưu customer_clusters.csv + model/scaler."""
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
    out = rfm[["customer_id"] + FEATURES].copy()
    out["cluster"] = km.labels_
    out.to_csv(os.path.join(out_dir, "customer_clusters.csv"), index=False)

    joblib.dump(km, os.path.join(out_dir, "kmeans_model.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "rfm_scaler.joblib"))
    joblib.dump({"k": k, "features": FEATURES, "transform": "log1p", "scaler": "StandardScaler",
                 "reference_date": REFERENCE_DATE, "random_state": RANDOM_STATE},
                os.path.join(out_dir, "model_info.joblib"))
    return km, out


def predict_cluster(df_new, model_dir="outputs"):
    """Gán cụm cho khách hàng mới: log1p -> scaler -> predict (Recency tính tới REFERENCE_DATE)."""
    model = joblib.load(os.path.join(model_dir, "kmeans_model.joblib"))
    scaler = joblib.load(os.path.join(model_dir, "rfm_scaler.joblib"))
    return model.predict(scaler.transform(np.log1p(df_new[FEATURES])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rfm", default="rfm_customers.csv")
    ap.add_argument("--k", type=int, default=None, help="K đã chọn; bỏ trống để chỉ chạy K = 2..10")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rfm, scaler, X = load_and_scale(args.rfm)
    metrics = evaluate_k(X)
    metrics.to_csv(os.path.join(args.out, "kmeans_metrics_k2_10.csv"), index=False)
    plot_metrics(metrics, args.out, args.k)
    print(metrics.round(4).to_string(index=False))

    if args.k:
        km, out = fit_final(rfm, scaler, X, args.k, args.out)
        print(f"\nK = {args.k} | Inertia = {km.inertia_:,.1f} | "
              f"Silhouette = {silhouette_score(X, km.labels_):.4f} | "
              f"Davies-Bouldin = {davies_bouldin_score(X, km.labels_):.4f}")
        print(out["cluster"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
