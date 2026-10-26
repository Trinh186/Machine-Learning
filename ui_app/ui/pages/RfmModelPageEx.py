"""Xử lý giao diện RFM & Model + ô nhập Predict (Task 11).

Giao diện được tạo bởi pyuic6: ui/pages/RfmModelPage.py (từ RfmModelPage.ui).
Lớp Ex chỉ xử lý trạng thái widget, signal/slot và gọi service:
    get_model_info(), get_segments(), get_rfm_table(...), predict_segment(r, f, m)
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QWidget

from app.widgets.charts import LineChart
from app.widgets.table_helpers import Pager, fill_table, setup_table
from ui.pages.RfmModelPage import Ui_RfmModelPage

HEADERS = ["Customer ID", "Recency (days)", "Frequency", "Monetary (£)", "Segment"]
NUMBER_COLS = (1, 2, 3)


class RfmModelPageEx(QWidget, Ui_RfmModelPage):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setupUi(self)          # sinh bởi pyuic6
        self.setupControls()
        self.setupSignalAndSlot()
        self.load_model_info()
        self.search_rfm()
        self.clear_prediction()

    # ---------------------------------------------------------------- setup
    def setupControls(self):
        self.segments = {s["cluster"]: s for s in self.service.get_segments()}

        setup_table(self.tblRfm, HEADERS, right_cols=NUMBER_COLS, stretch_col=4)
        self.cboRfmSegment.addItem("All segments", None)
        for cluster, seg in sorted(self.segments.items()):
            self.cboRfmSegment.addItem(f"Cluster {cluster} – {seg['segment_name_en']}", cluster)

        self.rfmPager = Pager(self.cboRfmPageSize, self.btnRfmPrevPage, self.btnRfmNextPage,
                              self.lblRfmPageInfo, self.lblRfmSummary, unit="customers", parent=self)

        # Biểu đồ chọn K: gắn vào 2 khung host đặt sẵn trong Qt Designer
        self.elbowChart = LineChart()
        self.hostElbowChart.layout().addWidget(self.elbowChart, 1)
        self.silhouetteChart = LineChart()
        self.hostSilhouetteChart.layout().addWidget(self.silhouetteChart, 1)

    def setupSignalAndSlot(self):
        self.btnRfmSearch.clicked.connect(self.search_rfm)
        self.txtRfmSearch.returnPressed.connect(self.search_rfm)
        self.cboRfmSegment.currentIndexChanged.connect(lambda _i: self.search_rfm())
        self.rfmPager.page_changed.connect(self.load_rfm_page)
        self.tblRfm.cellDoubleClicked.connect(self.use_selected_customer)
        self.btnPredict.clicked.connect(self.predict)
        self.btnClearPredict.clicked.connect(self.clear_prediction)

    # ---------------------------------------------------------------- model info
    def load_model_info(self):
        info = self.service.get_model_info()
        self.lblMetricKValue.setText(str(info["k"]))
        self.lblMetricKNote.setText(f"{info['n_customers']:,} customers · ref. date {info['reference_date']:%d/%m/%Y}")
        self.lblMetricSilhouetteValue.setText(f"{info['silhouette']:.4f}")
        self.lblMetricDaviesBouldinValue.setText(f"{info['davies_bouldin']:.4f}")
        self.lblMetricCalinskiValue.setText(f"{info['calinski_harabasz']:,.2f}")

        ks = info.get("k_search") or []
        labels = [row["k"] for row in ks]
        chosen = labels.index(info["k"]) if info["k"] in labels else None
        self.elbowChart.set_data(labels, [row["inertia"] for row in ks], chosen, "{:,.0f}", "#3B5BDB")
        self.silhouetteChart.set_data(labels, [row["silhouette"] for row in ks], chosen, "{:.4f}", "#1B7A4E")

    # ---------------------------------------------------------------- RFM table
    def search_rfm(self):
        self.rfmPager.reset()
        self.load_rfm_page()

    def load_rfm_page(self):
        result = self.service.get_rfm_table(
            keyword=self.txtRfmSearch.text(),
            cluster=self.cboRfmSegment.currentData(),
            page=self.rfmPager.page,
            page_size=self.rfmPager.page_size,
        )
        rows, colors = [], {}
        for i, r in enumerate(result["rows"]):
            rows.append([
                str(r["customer_id"]),
                f"{r['recency']:,}",
                f"{r['frequency']:,}",
                f"{r['monetary']:,.2f}",
                f"●  C{r['cluster']} · {r['segment_name_en'].replace(' Customers', '')}",
            ])
            colors[(i, 4)] = self.segments[r["cluster"]]["color"]
        fill_table(self.tblRfm, rows, right_cols=NUMBER_COLS, colors=colors, row_data=result["rows"])
        self.rfmPager.update(result["total_rows"])

    def use_selected_customer(self, row, _col):
        """Double-click 1 khách hàng → đưa RFM của khách đó sang ô Predict."""
        item = self.tblRfm.item(row, 0)
        if item is None:
            return
        r = item.data(Qt.ItemDataRole.UserRole)
        self.spinRecency.setValue(int(r["recency"]))
        self.spinFrequency.setValue(int(r["frequency"]))
        self.spinMonetary.setValue(float(r["monetary"]))
        self.predict()
        self.lblResultCaption.setText(f"PREDICTED SEGMENT · CUSTOMER {r['customer_id']}")

    # ---------------------------------------------------------------- predict
    def predict(self):
        try:
            result = self.service.predict_segment(
                self.spinRecency.value(), self.spinFrequency.value(), self.spinMonetary.value())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid input", str(exc))
            return
        self._show_result(result)

    def _show_result(self, result):
        color = result.get("color", "#3B5BDB")
        self.frameResult.setStyleSheet(f"#frameResult {{ border-left: 4px solid {color}; }}")
        self.lblResultCaption.setText("PREDICTED SEGMENT")
        self.lblResultSegment.setText(f"Cluster {result['cluster']} – {result['segment_name_en']}")
        self.lblResultSegment.setStyleSheet(f"color: {color};")
        self.lblResultSegmentVi.setText(result["segment_name"])
        self.lblResultDescription.setText(result.get("description", ""))
        self.lblResultStrategyTitle.show()
        self.lblResultStrategy.setText(result.get("marketing_strategy", ""))

    def clear_prediction(self):
        self.spinRecency.setValue(0)
        self.spinFrequency.setValue(1)
        self.spinMonetary.setValue(0)
        self.frameResult.setStyleSheet("")
        self.lblResultCaption.setText("PREDICTED SEGMENT")
        self.lblResultSegment.setText("Enter RFM values and click Predict Segment")
        self.lblResultSegment.setStyleSheet("")
        self.lblResultSegmentVi.setText("")
        self.lblResultDescription.setText("Tip: double-click a customer in the table to fill in their RFM values.")
        self.lblResultStrategyTitle.hide()
        self.lblResultStrategy.setText("")
