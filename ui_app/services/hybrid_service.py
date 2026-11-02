from . import mock_service
from .rfm_model_service import RFMModelService


# Giữ các chức năng cũ của Dashboard,
# Transaction Data và RFM Table.
get_dashboard_stats = mock_service.get_dashboard_stats
get_monthly_revenue = mock_service.get_monthly_revenue
get_segment_summary = mock_service.get_segment_summary

get_countries = mock_service.get_countries
get_transactions = mock_service.get_transactions

get_segments = mock_service.get_segments
get_model_info = mock_service.get_model_info
get_rfm_table = mock_service.get_rfm_table

# Trang Customer Segmentation và Cluster Analysis & Marketing (dữ liệu mẫu)
get_customer_countries = mock_service.get_customer_countries
get_segment_customers = mock_service.get_segment_customers
export_customers_csv = mock_service.export_customers_csv
get_cluster_profiles = mock_service.get_cluster_profiles
get_cluster_centroids = mock_service.get_cluster_centroids
get_marketing_actions = mock_service.get_marketing_actions


# Mô hình K-Means thật
_model_service = RFMModelService()


def predict_segment(recency, frequency, monetary):
    cluster = _model_service.predict_cluster(
        recency,
        frequency,
        monetary
    )

    segments = {
        s["cluster"]: s
        for s in get_segments()
    }

    if cluster not in segments:
        raise ValueError(
            f"Không tìm thấy thông tin cho Cluster {cluster}"
        )

    return {
        **segments[cluster]
    }