"""Màu dùng chung cho từng phân khúc (MySQL, Demo và hình mục 3.5 trong cluster_evaluation.py)."""

SEGMENT_COLORS = {
    "high-value customers": "#1B7A4E",
    "low-activity customers": "#8C8C8C",
}
DEFAULT_SEGMENT_COLOR = "#8C8C8C"


def segment_color(segment_name_en: str | None) -> str:
    name = (segment_name_en or "").strip().casefold()
    return SEGMENT_COLORS.get(name, DEFAULT_SEGMENT_COLOR)