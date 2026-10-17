"""Mục 3.5 - Đánh giá và diễn giải kết quả phân cụm (K-Means, K = 2).

Đầu vào (theo cấu trúc thư mục chung của nhóm):
    datasets/processed/Online Retail_cleaned.xlsx  dữ liệu giao dịch sạch (mục 3.2), dùng để tính RFM và thâm niên
    datasets/processed/rfm_customers.csv           RFM giá trị gốc của mục 3.3 (nếu có thì dùng thay cho bước tính lại)
    datasets/processed/customer_clusters.csv       nhãn cụm của mục 3.4 (nếu có, dùng để đối chiếu)

Đầu ra:
    outputs/cluster_profile.csv        hồ sơ từng cụm (Bảng 3.5.4 - 3.5.7)
    outputs/cluster_metrics.csv        chỉ số đánh giá mô hình (Bảng 3.5.1 - 3.5.3)
    outputs/figures/h351 ... h355      biểu đồ dùng trong báo cáo

Chạy từ thư mục gốc customer_segmentation/:
    python models/cluster_evaluation.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy.stats import kruskal
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "datasets" / "processed"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"

RFM_COLUMNS = ["recency", "frequency", "monetary"]
N_CLUSTERS = 2
N_INIT = 10
RANDOM_STATE = 42
REFERENCE_DATE = pd.Timestamp("2011-12-10")  # ngày liền sau giao dịch cuối, như mục 3.3.1

# Tên phân khúc gán theo hồ sơ RFM (mục 3.5.3), không theo số hiệu cụm
SEGMENT_NAMES = {
    "high_value": ("Khách hàng giá trị cao", "High-Value Customers"),
    "low_activity": ("Khách hàng ít hoạt động", "Low-Activity Customers"),
}
CLUSTER_COLORS = {"High-Value Customers": "#1b7a4e", "Low-Activity Customers": "#8c8c8c"}
LIGHT_COLORS = {"High-Value Customers": "#9ac5ae", "Low-Activity Customers": "#d0d0d0"}


def load_transactions() -> pd.DataFrame:
    """Dữ liệu giao dịch sạch của mục 3.2 (data_preprocessor.py), đổi tên cột theo quy ước chung."""
    path = DATA_DIR / "Online Retail_cleaned.xlsx"
    if not path.exists():
        return None
    df = pd.read_excel(path, dtype={"InvoiceNo": str})
    df = df.rename(columns={"CustomerID": "customer_id", "InvoiceNo": "invoice_no",
                            "InvoiceDate": "invoice_date", "TotalAmount": "total_amount"})
    df["customer_id"] = df["customer_id"].astype(int)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    if "total_amount" not in df.columns:
        df["total_amount"] = df["Quantity"] * df["UnitPrice"]
    return df


def load_rfm(transactions: pd.DataFrame) -> pd.DataFrame:
    """Ưu tiên rfm_customers.csv của mục 3.3; nếu chưa có thì tính lại đúng công thức mục 3.3.1."""
    path = DATA_DIR / "rfm_customers.csv"
    if path.exists():
        return pd.read_csv(path)[["customer_id"] + RFM_COLUMNS]
    if transactions is None:
        raise FileNotFoundError("Cần datasets/processed/rfm_customers.csv hoặc Online Retail_cleaned.xlsx")
    g = transactions.groupby("customer_id")
    return pd.DataFrame({
        "recency": (REFERENCE_DATE - g["invoice_date"].max().dt.normalize()).dt.days,
        "frequency": g["invoice_no"].nunique(),
        "monetary": g["total_amount"].sum().round(2),
    }).reset_index()


def scale_rfm(rfm: pd.DataFrame) -> np.ndarray:
    """log1p + StandardScaler, đúng quy trình mục 3.3."""
    return StandardScaler().fit_transform(np.log1p(rfm[RFM_COLUMNS]))


def fit_kmeans(x_scaled: np.ndarray, random_state: int = RANDOM_STATE) -> KMeans:
    return KMeans(n_clusters=N_CLUSTERS, n_init=N_INIT, random_state=random_state).fit(x_scaled)


def name_segments(rfm: pd.DataFrame) -> dict:
    """Cụm có trung vị Monetary cao hơn là nhóm giá trị cao."""
    medians = rfm.groupby("cluster")["monetary"].median()
    high = medians.idxmax()
    return {c: SEGMENT_NAMES["high_value" if c == high else "low_activity"] for c in medians.index}


def evaluate_model(x_scaled, labels, kmeans) -> pd.DataFrame:
    sil = silhouette_samples(x_scaled, labels)
    aris = [adjusted_rand_score(labels, fit_kmeans(x_scaled, s).labels_) for s in range(10)]
    rows = [
        ("inertia", kmeans.inertia_),
        ("silhouette", silhouette_score(x_scaled, labels)),
        ("davies_bouldin", davies_bouldin_score(x_scaled, labels)),
        ("calinski_harabasz", calinski_harabasz_score(x_scaled, labels)),
        ("negative_silhouette_count", int((sil < 0).sum())),
        ("negative_silhouette_pct", (sil < 0).mean() * 100),
        ("n_iter", kmeans.n_iter_),
        ("ari_mean_seed_0_9", np.mean(aris)),
        ("ari_min_seed_0_9", np.min(aris)),
        ("ari_max_seed_0_9", np.max(aris)),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def feature_separation(rfm, x_log, labels) -> pd.DataFrame:
    """η² trên thang log1p và kiểm định Kruskal-Wallis trên giá trị gốc (Bảng 3.5.3)."""
    rows = []
    for col in RFM_COLUMNS:
        y = x_log[col].to_numpy()
        grand = y.mean()
        ss_between = sum((labels == c).sum() * (y[labels == c].mean() - grand) ** 2 for c in np.unique(labels))
        ss_total = ((y - grand) ** 2).sum()
        h_stat, p_value = kruskal(*[rfm.loc[labels == c, col] for c in np.unique(labels)])
        rows.append((col, ss_between / ss_total, h_stat, p_value))
    return pd.DataFrame(rows, columns=["feature", "eta_squared", "kruskal_h", "p_value"])


def add_tenure(rfm: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """Thâm niên = số ngày từ lần mua đầu tiên đến Reference Date."""
    if transactions is None:
        rfm["tenure"] = np.nan
        return rfm
    first = transactions.groupby("customer_id")["invoice_date"].min().dt.normalize()
    rfm["tenure"] = (REFERENCE_DATE - rfm["customer_id"].map(first)).dt.days
    return rfm


def build_profile(rfm: pd.DataFrame, x_scaled, labels) -> pd.DataFrame:
    sil = silhouette_samples(x_scaled, labels)
    total_revenue = rfm["monetary"].sum()
    profile = (
        rfm.assign(silhouette=sil)
        .groupby(["cluster", "segment_name", "segment_name_en"])
        .agg(
            customers=("customer_id", "count"),
            recency_mean=("recency", "mean"),
            recency_median=("recency", "median"),
            frequency_mean=("frequency", "mean"),
            frequency_median=("frequency", "median"),
            monetary_mean=("monetary", "mean"),
            monetary_median=("monetary", "median"),
            one_time_pct=("frequency", lambda s: (s == 1).mean() * 100),
            recency_le_30_pct=("recency", lambda s: (s <= 30).mean() * 100),
            recency_gt_90_pct=("recency", lambda s: (s > 90).mean() * 100),
            recency_gt_180_pct=("recency", lambda s: (s > 180).mean() * 100),
            invoices=("frequency", "sum"),
            revenue=("monetary", "sum"),
            tenure_median=("tenure", "median"),
            silhouette_mean=("silhouette", "mean"),
            negative_silhouette_pct=("silhouette", lambda s: (s < 0).mean() * 100),
        )
        .reset_index()
    )
    profile["customer_pct"] = profile["customers"] / len(rfm) * 100
    profile["revenue_pct"] = profile["revenue"] / total_revenue * 100
    profile["avg_invoice_value"] = profile["revenue"] / profile["invoices"]
    return profile.sort_values("revenue", ascending=False).round(4)


def plot_figures(rfm, x_scaled, kmeans):
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 200})
    labels = kmeans.labels_
    seg = dict(zip(rfm["cluster"], rfm["segment_name_en"]))
    order = sorted(seg, key=lambda c: seg[c] != "High-Value Customers")  # nhóm giá trị cao trước
    sil = silhouette_samples(x_scaled, labels)

    # h351: Silhouette theo cụm
    fig, ax = plt.subplots(figsize=(8, 4.6))
    y = 10
    for c in reversed(order):
        v = np.sort(sil[labels == c])
        ax.fill_betweenx(np.arange(y, y + len(v)), 0, v, color=CLUSTER_COLORS[seg[c]], alpha=0.85, lw=0)
        ax.text(-0.09, y + len(v) / 2, f"C{c}", va="center", fontsize=11)
        y += len(v) + 60
    ax.axvline(sil.mean(), color="crimson", ls="--")
    ax.text(sil.mean() + 0.01, y - 40, f"Silhouette TB = {sil.mean():.3f}".replace(".", ","), color="crimson")
    ax.set_yticks([])
    ax.set_xlim(-0.15, 0.8)
    ax.set_xlabel("Hệ số Silhouette của từng khách hàng")
    ax.set_title(f"Biểu đồ Silhouette theo cụm (K = {N_CLUSTERS})")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "h351_silhouette_k2.png")
    plt.close(fig)

    # h352: snake plot tâm cụm
    centers = kmeans.cluster_centers_
    fig, ax = plt.subplots(figsize=(8, 4.6))
    x = np.arange(3)
    for c in order:
        col = CLUSTER_COLORS[seg[c]]
        ax.plot(x, centers[c], "-o", color=col, lw=2.5, label=f"Cluster {c} – {seg[c]}")
        for i in range(3):
            offset = 0.06 if centers[c][i] >= 0 else -0.12
            ax.text(x[i] + 0.04, centers[c][i] + offset, f"{centers[c][i]:+.2f}", color=col, fontsize=10)
    ax.axhline(0, color="grey", ls="--", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(["Recency", "Frequency", "Monetary"], fontsize=11)
    ax.set_ylabel("Giá trị centroid (log1p + StandardScaler)")
    ax.set_title("Snake plot: vị trí centroid của các cụm")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "h352_snake_plot_k2.png")
    plt.close(fig)

    # h353: PCA và Recency - Monetary
    pca = PCA(2).fit(x_scaled)
    z, cz, ev = pca.transform(x_scaled), pca.transform(centers), pca.explained_variance_ratio_ * 100
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.8))
    for c in reversed(order):
        m = labels == c
        axs[0].scatter(z[m, 0], z[m, 1], s=6, alpha=0.5, color=CLUSTER_COLORS[seg[c]], label=f"Cluster {c} – {seg[c]}")
        axs[1].scatter(rfm.loc[m, "recency"], rfm.loc[m, "monetary"], s=6, alpha=0.5, color=CLUSTER_COLORS[seg[c]])
    axs[0].scatter(cz[:, 0], cz[:, 1], marker="X", s=220, color="black", label="Centroid")
    leg = axs[0].legend(loc="lower right", fontsize=9)
    for handle in leg.legend_handles[:-1]:
        handle.set_sizes([30])
        handle.set_alpha(1)
    leg.legend_handles[-1].set_sizes([80])
    axs[0].set_xlabel(f"PC1 ({ev[0]:.1f}%)")
    axs[0].set_ylabel(f"PC2 ({ev[1]:.1f}%)")
    axs[0].set_title("a) Không gian PCA của RFM đã chuẩn hóa")
    axs[1].set_yscale("log")
    axs[1].set_xlabel("Recency (ngày)")
    axs[1].set_ylabel("Monetary (thang log)")
    axs[1].set_title("b) Recency – Monetary (giá trị gốc)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "h353_pca_recency_monetary_k2.png")
    plt.close(fig)

    # h354: phân phối RFM theo cụm
    fig, axs = plt.subplots(1, 3, figsize=(12, 4.4))
    short = {"High-Value Customers": "High-Value", "Low-Activity Customers": "Low-Activity"}
    for ax, (col, title, log) in zip(
        axs,
        [("recency", "Recency (ngày)", False), ("frequency", "Frequency (số hóa đơn, log)", True), ("monetary", "Monetary (log)", True)],
    ):
        box = ax.boxplot([rfm.loc[labels == c, col] for c in order], showfliers=False, patch_artist=True,
                         widths=0.55, medianprops=dict(color="black"))
        for patch, c in zip(box["boxes"], order):
            patch.set_facecolor(CLUSTER_COLORS[seg[c]])
            patch.set_alpha(0.85)
        ax.set_xticks(range(1, len(order) + 1))
        ax.set_xticklabels([f"C{c}\n{short[seg[c]]}" for c in order], fontsize=9)
        ax.set_title(title)
        if log:
            ax.set_yscale("log")
    fig.suptitle("Phân phối Recency, Frequency, Monetary theo cụm (không hiển thị outlier)")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "h354_rfm_distribution_k2.png")
    plt.close(fig)

    # h355: tỷ lệ khách hàng và tỷ trọng doanh thu
    total = rfm["monetary"].sum()
    fig, ax = plt.subplots(figsize=(8, 4.4))
    w = 0.38
    for i, c in enumerate(order):
        cust = (labels == c).mean() * 100
        rev = rfm.loc[labels == c, "monetary"].sum() / total * 100
        ax.bar(i - w / 2, cust, w, color=LIGHT_COLORS[seg[c]])
        ax.bar(i + w / 2, rev, w, color=CLUSTER_COLORS[seg[c]])
        for xx, v in [(i - w / 2, cust), (i + w / 2, rev)]:
            ax.text(xx, v + 1, f"{v:.1f}%".replace(".", ","), ha="center", fontsize=10)
    ax.legend(handles=[Patch(color="#c4c4c4", label="Tỷ lệ khách hàng (%)"),
                       Patch(color="#7a7a7a", label="Tỷ trọng doanh thu (%)")], loc="upper right")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"C{c}\n{seg[c]}" for c in order])
    ax.set_ylabel("%")
    ax.set_ylim(0, 100)
    ax.set_title("Quy mô khách hàng và tỷ trọng doanh thu theo cụm")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "h355_size_revenue_k2.png")
    plt.close(fig)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transactions = load_transactions()
    rfm = load_rfm(transactions)
    x_log = np.log1p(rfm[RFM_COLUMNS])
    x_scaled = scale_rfm(rfm)
    kmeans = fit_kmeans(x_scaled)
    labels = kmeans.labels_
    rfm["cluster"] = labels

    clusters_path = DATA_DIR / "customer_clusters.csv"
    if clusters_path.exists():
        ref = pd.read_csv(clusters_path)
        if "cluster" in ref.columns:
            merged = rfm[["customer_id", "cluster"]].merge(ref[["customer_id", "cluster"]], on="customer_id")
            ari = adjusted_rand_score(merged["cluster_x"], merged["cluster_y"])
            print(f"ARI so với customer_clusters.csv của mục 3.4: {ari:.4f}")

    names = name_segments(rfm)
    rfm["segment_name"] = rfm["cluster"].map(lambda c: names[c][0])
    rfm["segment_name_en"] = rfm["cluster"].map(lambda c: names[c][1])
    rfm = add_tenure(rfm, transactions)

    metrics = evaluate_model(x_scaled, labels, kmeans)
    separation = feature_separation(rfm, x_log, labels)
    profile = build_profile(rfm, x_scaled, labels)

    metrics.to_csv(OUTPUT_DIR / "cluster_metrics.csv", index=False)
    separation.to_csv(OUTPUT_DIR / "cluster_feature_separation.csv", index=False)
    profile.to_csv(OUTPUT_DIR / "cluster_profile.csv", index=False, encoding="utf-8-sig")
    plot_figures(rfm, x_scaled, kmeans)

    print(metrics.to_string(index=False))
    print(separation.to_string(index=False))
    print(profile.T.to_string())


if __name__ == "__main__":
    main()
