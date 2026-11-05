"""Đối chiếu số liệu Dashboard đọc từ MySQL (services/db_service.py) với dữ liệu sạch (Task 6).

Điều kiện: đã chạy customer_segmentation/database/import_mysql.py và cấu hình ui_app/.env.
Từ thư mục ui_app chạy:
    python -m tests.test_dashboard_stats

Số liệu kỳ vọng được tính độc lập bằng pandas từ
customer_segmentation/datasets/processed/Online Retail_cleaned.xlsx và rfm_customers.csv,
theo cùng định nghĩa với Dashboard: chỉ các dòng mua (Quantity > 0) có trong invoice_details.
"""
import unittest
from pathlib import Path

import pandas as pd

from services import db_service

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "customer_segmentation" / "datasets" / "processed"
CLEAN_FILE = PROCESSED / "Online Retail_cleaned.xlsx"
RFM_FILE = PROCESSED / "rfm_customers.csv"


class DashboardStatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Đang đọc dữ liệu sạch để đối chiếu (khoảng 1 phút)...")
        clean = pd.read_excel(CLEAN_FILE, dtype={"InvoiceNo": str, "StockCode": str})
        cls.clean = clean
        cls.sales = clean[clean["Quantity"] > 0]
        cls.rfm = pd.read_csv(RFM_FILE)
        cls.stats = db_service.get_dashboard_stats()

    def test_kpi_cards(self):
        sales = self.sales
        self.assertEqual(self.stats["total_customers"], sales["CustomerID"].nunique())
        self.assertEqual(self.stats["total_invoices"], sales["InvoiceNo"].nunique())
        self.assertAlmostEqual(self.stats["total_revenue"], round(sales["TotalAmount"].sum(), 2), places=2)
        self.assertEqual(self.stats["num_segments"], 2)

    def test_date_range(self):
        self.assertEqual(pd.Timestamp(self.stats["date_from"]), self.sales["InvoiceDate"].min())
        self.assertEqual(pd.Timestamp(self.stats["date_to"]), self.sales["InvoiceDate"].max())

    def test_monthly_revenue(self):
        # invoices.invoice_date là thời điểm sớm nhất của hóa đơn, nên tháng được gán theo hóa đơn.
        first_date = self.sales.groupby("InvoiceNo")["InvoiceDate"].transform("min")
        expected = self.sales.groupby(first_date.dt.strftime("%Y-%m"))["TotalAmount"].sum().round(2)
        actual = dict(db_service.get_monthly_revenue())
        self.assertEqual(list(actual), list(expected.index))
        for month, value in expected.items():
            self.assertAlmostEqual(actual[month], value, places=2, msg=month)
        self.assertAlmostEqual(sum(actual.values()), self.stats["total_revenue"], places=1)

    def test_segment_summary(self):
        rows = db_service.get_segment_summary()
        self.assertEqual(sum(r["customers"] for r in rows), len(self.rfm))
        self.assertAlmostEqual(sum(r["revenue"] for r in rows), self.rfm["monetary"].sum(), places=1)
        self.assertTrue(all("color" in r for r in rows))

    def test_transaction_page_total_matches_dashboard(self):
        result = db_service.get_transactions(page=1, page_size=5)
        self.assertEqual(result["total_rows"], len(self.sales))
        self.assertAlmostEqual(result["total_amount"], self.stats["total_revenue"], places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
