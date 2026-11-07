"""Shared colors for customer segments in MySQL and Demo modes."""

SEGMENT_COLORS = {
    "high-value customers": "#1B7A4E",
    "low-activity customers": "#767676",
}
DEFAULT_SEGMENT_COLOR = "#767676"


def segment_color(segment_name_en: str | None) -> str:
    name = (segment_name_en or "").strip().casefold()
    return SEGMENT_COLORS.get(name, DEFAULT_SEGMENT_COLOR)