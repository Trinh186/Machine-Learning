
from . import mock_service
from .rfm_model_service import RFMModelService


# ==================================================
# 1. DASHBOARD - GIỮ NGUYÊN DỮ LIỆU MOCK
# ==================================================

get_dashboard_stats = mock_service.get_dashboard_stats
get_monthly_revenue = mock_service.get_monthly_revenue
get_segment_summary = mock_service.get_segment_summary


# ==================================================
# 2. TRANSACTION DATA - GIỮ NGUYÊN DỮ LIỆU MOCK
# ==================================================

get_countries = mock_service.get_countries
get_transactions = mock_service.get_transactions


# ==================================================
# 3. CLUSTER MARKETING / TASK 12
# GIỮ NGUYÊN DỮ LIỆU MOCK ĐỂ KHÔNG ẢNH HƯỞNG
# ==================================================

get_segments = mock_service.get_segments
get_customer_countries = mock_service.get_customer_countries
get_segment_customers = mock_service.get_segment_customers
export_customers_csv = mock_service.export_customers_csv
get_cluster_profiles = mock_service.get_cluster_profiles
get_cluster_centroids = mock_service.get_cluster_centroids
get_marketing_actions = mock_service.get_marketing_actions


# ==================================================
# 4. TASK 11 - SỬ DỤNG K-MEANS MODEL THẬT
# ==================================================

_model_service = RFMModelService()


def get_real_model_info():
    """Lấy thông tin và metrics từ K-Means model thật."""
    return _model_service.get_model_info()


def get_model_segments():
    """Lấy tên phân khúc theo Cluster ID của model thật."""
    return _model_service.get_segments()


def get_real_rfm_table(
    keyword="",
    cluster=None,
    page=1,
    page_size=50
):
    """Lấy RFM table từ kết quả phân cụm thật."""
    return _model_service.get_rfm_table(
        keyword=keyword,
        cluster=cluster,
        page=page,
        page_size=page_size
    )


def predict_segment(recency, frequency, monetary):
    """Dự đoán phân khúc bằng K-Means model thật."""
    return _model_service.predict_segment(
        recency,
        frequency,
        monetary
    )
