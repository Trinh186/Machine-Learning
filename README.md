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
├── customer_segmentation/
│   │
│   ├── datasets/
│   │   ├── raw/
│   │   └── processed/
│   │
│   ├── connectors/
│   │   └── mysql_connector.py          → MySQLConnector
│   │
│   ├── preprocessing/
│   │   └── data_preprocessor.py        → DataPreprocessor
│   │
│   ├── rfm/
│   │   └── rfm_analyzer.py             → RFMAnalyzer
│   │
│   ├── models/
│   │   └── clustering_model.py         → ClusteringModel
│   │
│   ├── ui/
│   │   ├── MainWindow.ui
│   │   ├── MainWindow.py
│   │   ├── MainWindowEx.py
│   │   └── chart_visualization.py      → ChartVisualization
│   │
│   ├── database/
│   │   └── database.sql
│   │
│   ├── outputs/
│   │
│   ├── test/
│   │
│   ├── main.py                         → Chạy chương trình
│   └── requirements.txt                → Thư viện cần cài đặt
│
├── .gitignore
└── README.md
```
