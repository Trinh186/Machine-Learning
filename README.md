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
