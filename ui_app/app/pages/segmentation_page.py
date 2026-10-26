
import csv
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QSizePolicy
)


ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = (
    ROOT / "customer_segmentation"
    / "outputs" / "cluster_profile.csv"
)

BLUE = "#3B5BDB"
TEAL = "#16A6A1"
TEXT = "#111827"
MUTED = "#6B7280"


def read_profiles():
    with PROFILE_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        return sorted(
            list(csv.DictReader(f)),
            key=lambda p: int(p["cluster"])
        )


def make_label(text, css_class=None):
    lbl = QLabel(str(text))
    if css_class:
        lbl.setProperty("cssClass", css_class)
    lbl.setWordWrap(True)
    return lbl


def make_card():
    frame = QFrame()
    frame.setProperty("cssClass", "card")
    return frame


def make_kpi(title, value, note, accent=BLUE):
    frame = make_card()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(8)

    heading = make_label(title.upper(), "kpiTitle")
    number = make_label(value, "kpiValue")
    number.setStyleSheet(
        f"color: {accent}; font-size: 19pt; font-weight: 700;"
    )
    subtitle = make_label(note, "kpiNote")

    layout.addWidget(heading)
    layout.addWidget(number)
    layout.addWidget(subtitle)

    return frame


def make_bar(value, color):
    bar = QProgressBar()
    bar.setRange(0, 10000)
    bar.setValue(round(value * 100))
    bar.setTextVisible(False)
    bar.setFixedHeight(12)
    bar.setStyleSheet(f"""
        QProgressBar {{
            background: #EDF2FF;
            border: none;
            border-radius: 6px;
        }}
        QProgressBar::chunk {{
            background: {color};
            border-radius: 6px;
        }}
    """)
    return bar


class SegmentationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.profiles = read_profiles()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(18)
        layout.setContentsMargins(0, 0, 4, 8)

        total_customers = sum(
            int(p["customers"]) for p in self.profiles
        )
        total_revenue = sum(
            float(p["revenue"]) for p in self.profiles
        )

        # 1. KPI cards
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        kpis = [
            (
                "Total Customers",
                f"{total_customers:,}",
                "Customers analyzed",
                BLUE
            ),
            (
                "Customer Segments",
                str(len(self.profiles)),
                "K-Means clusters",
                TEAL
            ),
            (
                "Total Revenue",
                f"£{total_revenue / 1_000_000:,.2f}M",
                "Total dataset revenue",
                BLUE
            ),
        ]

        for col, (title, value, note, color) in enumerate(kpis):
            kpi_grid.addWidget(
                make_kpi(title, value, note, color), 0, col
            )
            kpi_grid.setColumnStretch(col, 1)

        layout.addLayout(kpi_grid)

        # 2. Customer / revenue share chart
        chart_card = make_card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(22, 20, 22, 22)
        chart_layout.setSpacing(15)

        chart_layout.addWidget(
            make_label(
                "Customer Distribution & Revenue Contribution",
                "cardTitle"
            )
        )
        chart_layout.addWidget(
            make_label(
                "Compare each segment's customer share "
                "with its contribution to total revenue.",
                "cardSubtitle"
            )
        )

        for p in self.profiles:
            cluster = int(p["cluster"])
            customer_pct = float(p["customer_pct"])
            revenue_pct = float(p["revenue_pct"])

            chart_layout.addSpacing(8)
            chart_layout.addWidget(
                make_label(
                    f'Cluster {cluster}  |  {p["segment_name_en"]}',
                    "fieldLabel"
                )
            )

            for name, value, color in [
                ("Customers", customer_pct, BLUE),
                ("Revenue", revenue_pct, TEAL),
            ]:
                row = QHBoxLayout()
                row.setSpacing(12)

                caption = make_label(name, "cardSubtitle")
                caption.setFixedWidth(80)

                percent = make_label(f"{value:.2f}%", "fieldLabel")
                percent.setFixedWidth(65)
                percent.setAlignment(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )

                row.addWidget(caption)
                row.addWidget(make_bar(value, color), 1)
                row.addWidget(percent)

                chart_layout.addLayout(row)

        layout.addWidget(chart_card)

        # 3. Detailed segment cards
        segment_grid = QGridLayout()
        segment_grid.setSpacing(14)

        for index, p in enumerate(self.profiles):
            cluster = int(p["cluster"])
            accent = BLUE if cluster == 0 else TEAL

            frame = make_card()
            body = QVBoxLayout(frame)
            body.setContentsMargins(20, 18, 20, 20)
            body.setSpacing(10)

            badge = make_label(f"CLUSTER {cluster}")
            badge.setStyleSheet(f"""
                color: {accent};
                background: #EDF2FF;
                border-radius: 7px;
                padding: 6px 10px;
                font-weight: 700;
            """)
            badge.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Preferred
            )
            body.addWidget(badge)

            body.addWidget(
                make_label(p["segment_name"], "cardTitle")
            )
            body.addWidget(
                make_label(p["segment_name_en"], "cardSubtitle")
            )

            body.addSpacing(6)

            metrics = [
                ("Customers", f'{int(p["customers"]):,}'),
                (
                    "Customer Share",
                    f'{float(p["customer_pct"]):.2f}%'
                ),
                (
                    "Revenue Share",
                    f'{float(p["revenue_pct"]):.2f}%'
                ),
                (
                    "Avg Recency",
                    f'{float(p["recency_mean"]):.2f} days'
                ),
                (
                    "Avg Frequency",
                    f'{float(p["frequency_mean"]):.2f}'
                ),
                (
                    "Avg Monetary",
                    f'£{float(p["monetary_mean"]):,.2f}'
                ),
            ]

            for metric, value in metrics:
                metric_row = QHBoxLayout()

                left = make_label(metric, "cardSubtitle")
                right = make_label(value, "fieldLabel")

                right.setAlignment(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )

                metric_row.addWidget(left)
                metric_row.addStretch()
                metric_row.addWidget(right)

                body.addLayout(metric_row)

            segment_grid.addWidget(frame, 0, index)
            segment_grid.setColumnStretch(index, 1)

        layout.addLayout(segment_grid)

        # 4. RFM comparison table
        table_card = make_card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 18, 20, 20)
        table_layout.setSpacing(12)

        table_layout.addWidget(
            make_label("RFM Cluster Comparison", "cardTitle")
        )
        table_layout.addWidget(
            make_label(
                "Average Recency, Frequency and Monetary "
                "for each customer segment.",
                "cardSubtitle"
            )
        )

        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Cluster", "Segment", "Customers",
            "Customer %", "Revenue %",
            "Recency", "Frequency", "Monetary (£)"
        ])
        table.setRowCount(len(self.profiles))
        table.setAlternatingRowColors(True)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(48)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.setMinimumHeight(155)

        for row, p in enumerate(self.profiles):
            values = [
                p["cluster"],
                p["segment_name_en"],
                f'{int(p["customers"]):,}',
                f'{float(p["customer_pct"]):.2f}%',
                f'{float(p["revenue_pct"]):.2f}%',
                f'{float(p["recency_mean"]):.2f}',
                f'{float(p["frequency_mean"]):.2f}',
                f'{float(p["monetary_mean"]):,.2f}',
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                table.setItem(row, col, item)

        table_layout.addWidget(table)
        layout.addWidget(table_card)

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)
