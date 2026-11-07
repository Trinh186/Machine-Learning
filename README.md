## Cách chạy nhanh (không cần cài gì trước)

**Windows:** bấm đúp file **`CHAY_APP.bat`** ở thư mục gốc `Machine-Learning`.

- Lần đầu: file tự tạo môi trường riêng (`.venv`) và tự cài thư viện (cần Internet, khoảng 3–5 phút). Nếu máy chưa có Python 3.11+, file sẽ hỏi để tự cài Python 3.13.
- Những lần sau: app mở ngay.
- Chọn chế độ:
  1. **Đầy đủ** – có màn Đăng nhập, cần MySQL Server đang chạy. Lần đầu sẽ hỏi tài khoản/mật khẩu MySQL, tự tạo database, các bảng và tài khoản Admin.
  2. **Demo** – xem toàn bộ giao diện với dữ liệu mẫu, không cần MySQL.

**macOS / Linux:** `python3 launcher.py` (thêm `--demo` hoặc `--full` để bỏ qua bước chọn).

## Project Structure

```text
Machine-Learning/
│
├── CHAY_APP.bat                        → Bấm đúp để cài và mở app (Windows)
├── launcher.py                         → Tạo .venv, cài thư viện, chọn chế độ Đầy đủ / Demo
│
├── customer_segmentation/              → Xử lý dữ liệu và mô hình
│   ├── datasets/
│   │   ├── raw/                        → Online Retail gốc
│   │   └── processed/                  → Online Retail_cleaned.xlsx, rfm_customers.csv, customer_clusters.csv
│   ├── preprocessing/
│   │   └── data_preprocessor.py        → DataPreprocessor (làm sạch dữ liệu)
│   ├── rfm/
│   │   └── rfm_analyzer.py             → RFMAnalyzer (tính Recency, Frequency, Monetary)
│   ├── models/
│   │   ├── clustering_model.py         → Train K-Means (K = 2 … 10), lưu model vào outputs/
│   │   └── cluster_evaluation.py       → Đánh giá model đã lưu, vẽ hình mục 3.5
│   ├── database/
│   │   ├── database.sql                → Tạo database, các bảng, bảng segments
│   │   └── import_mysql.py             → Nạp dữ liệu sạch, RFM và nhãn cụm vào MySQL
│   ├── outputs/                        → kmeans_model.joblib, rfm_scaler.joblib, model_info.joblib, *.csv, figures/
│   └── requirements.txt
│
├── ui_app/                             → Ứng dụng PyQt6
│   ├── main.py                         → Điểm chạy app (python main.py, thêm --demo nếu không có MySQL)
│   ├── ui/                             → File Qt Designer: *.ui → *.py (pyuic6) → *Ex.py, style.qss, assets/
│   ├── app/                            → MainWindow, các trang (pages/), biểu đồ và widget dùng chung
│   ├── auth/                           → Đăng nhập, phân quyền, quản lý tài khoản
│   ├── dao/                            → Truy vấn MySQL
│   ├── services/                       → Lớp dữ liệu cho giao diện (MySQL, dữ liệu mẫu, model K-Means)
│   ├── scripts/                        → setup_db.py, create_admin.py
│   ├── tests/
│   ├── .env.example                    → Mẫu cấu hình kết nối MySQL
│   └── requirements.txt
│
├── .gitignore
└── README.md
```
