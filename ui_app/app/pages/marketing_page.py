
import csv
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy
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


STRATEGIES = {
    0: {
        "objective": "Retention & Loyalty",
        "priority": "Protect high-value revenue",
        "focus": "Retain valuable customers and increase loyalty.",
        "actions": [
            "Launch a VIP loyalty and rewards program.",
            "Offer personalized benefits based on purchase history.",
            "Provide proactive support for valuable customers.",
            "Encourage repeat purchases with exclusive offers.",
        ],
        "metric": "Repeat purchase rate",
    },
    1: {
        "objective": "Reactivation & Engagement",
        "priority": "Re-engage inactive customers",
        "focus": "Encourage inactive customers to purchase again.",
        "actions": [
            "Run targeted customer win-back campaigns.",
            "Send personalized reminders and recommendations.",
            "Offer suitable return-purchase incentives.",
            "Track responses and identify reactivated customers.",
        ],
        "metric": "Customer reactivation rate",
    },
}


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


def make_metric_row(title, value):
    row = QHBoxLayout()
    row.setSpacing(10)

    left = make_label(title, "cardSubtitle")
    right = make_label(value, "fieldLabel")
    right.setAlignment(
        Qt.AlignmentFlag.AlignRight
        | Qt.AlignmentFlag.AlignVCenter
    )

    row.addWidget(left)
    row.addStretch()
    row.addWidget(right)

    return row


class MarketingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        with PROFILE_PATH.open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            profiles = sorted(
                list(csv.DictReader(f)),
                key=lambda p: int(p["cluster"])
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)

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
            int(p["customers"]) for p in profiles
        )

        # 1. Overview card
        overview = make_card()
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(22, 18, 22, 18)

        overview_text = QVBoxLayout()
        overview_text.setSpacing(6)

        overview_text.addWidget(
            make_label("Marketing Strategy Overview", "cardTitle")
        )
        overview_text.addWidget(
            make_label(
                "Personalized marketing actions based on "
                "customer behavior and RFM segmentation.",
                "cardSubtitle"
            )
        )

        overview_layout.addLayout(overview_text, 1)

        summary = make_label(
            f"{len(profiles)} SEGMENTS  |  {total_customers:,} CUSTOMERS"
        )
        summary.setStyleSheet("""
            color: #3B5BDB;
            background: #EDF2FF;
            border-radius: 8px;
            padding: 10px 14px;
            font-weight: 700;
        """)
        summary.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred
        )
        overview_layout.addWidget(summary)

        layout.addWidget(overview)

        # 2. Strategy cards
        strategy_grid = QGridLayout()
        strategy_grid.setSpacing(16)

        for index, p in enumerate(profiles):
            cluster = int(p["cluster"])
            accent = BLUE if cluster == 0 else TEAL

            strategy = STRATEGIES.get(
                cluster,
                {
                    "objective": "Strategy Review",
                    "priority": "Review customer profile",
                    "focus": "Further analysis is required.",
                    "actions": [],
                    "metric": "To be defined",
                }
            )

            frame = make_card()
            body = QVBoxLayout(frame)
            body.setContentsMargins(22, 20, 22, 22)
            body.setSpacing(12)

            # Cluster badge
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

            # Cluster information
            body.addWidget(
                make_label("CUSTOMER PROFILE", "kpiTitle")
            )

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

            for title, value in metrics:
                body.addLayout(make_metric_row(title, value))

            # Divider
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setStyleSheet(
                "color: #E5E8F0; background: #E5E8F0;"
            )
            body.addWidget(divider)

            # Marketing objective
            body.addWidget(
                make_label("MARKETING OBJECTIVE", "kpiTitle")
            )

            objective = make_label(strategy["objective"])
            objective.setStyleSheet(f"""
                color: {accent};
                font-size: 14pt;
                font-weight: 700;
            """)
            body.addWidget(objective)

            body.addWidget(
                make_label(strategy["focus"], "resultBody")
            )

            priority = make_label(
                f'Priority: {strategy["priority"]}'
            )
            priority.setStyleSheet("""
                background: #F8FAFD;
                color: #374151;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
            """)
            body.addWidget(priority)

            # Recommended actions
            body.addWidget(
                make_label("RECOMMENDED ACTIONS", "kpiTitle")
            )

            for action in strategy["actions"]:
                action_row = QHBoxLayout()
                action_row.setSpacing(10)

                dot = make_label("●")
                dot.setStyleSheet(f"color: {accent};")
                dot.setFixedWidth(14)

                text = make_label(action, "resultBody")

                action_row.addWidget(dot)
                action_row.addWidget(text, 1)

                body.addLayout(action_row)

            body.addStretch()

            # Monitoring metric
            metric_box = QFrame()
            metric_box.setProperty("cssClass", "resultBox")

            metric_layout = QVBoxLayout(metric_box)
            metric_layout.setContentsMargins(14, 12, 14, 12)

            metric_layout.addWidget(
                make_label("SUGGESTED MONITORING KPI", "kpiTitle")
            )
            metric_layout.addWidget(
                make_label(strategy["metric"], "fieldLabel")
            )

            body.addWidget(metric_box)

            strategy_grid.addWidget(frame, 0, index)
            strategy_grid.setColumnStretch(index, 1)

        layout.addLayout(strategy_grid)

        # 3. Methodology
        method_card = make_card()
        method_layout = QVBoxLayout(method_card)
        method_layout.setContentsMargins(22, 18, 22, 18)
        method_layout.setSpacing(10)

        method_layout.addWidget(
            make_label("Recommendation Methodology", "cardTitle")
        )
        method_layout.addWidget(
            make_label(
                "Customer segments are identified using RFM "
                "(Recency, Frequency, Monetary) and K-Means clustering. "
                "Marketing recommendations are proposed based on "
                "the behavioral characteristics and revenue contribution "
                "of each segment. These actions are suggestions, "
                "not automatically executed marketing campaigns.",
                "cardSubtitle"
            )
        )

        layout.addWidget(method_card)
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
