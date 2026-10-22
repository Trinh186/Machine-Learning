# UI — Customer Segmentation System (Nhóm 09)

Phần giao diện PyQt6: **MainWindow, menu điều hướng, Dashboard** (Task 10). Hiện đang chạy bằng **dữ liệu giả**, nên chưa cần MySQL hay model.

## Chạy thử

```bash
pip install -r requirements.txt
python main.py              # đăng nhập giả quyền Admin
python main.py --role user  # quyền User: ẩn menu User Management
```

## Chỉnh giao diện bằng Qt Designer

```bash
pip install pyside6
pyside6-designer            # mở ui/main_window.ui hoặc ui/pages/dashboard.ui
```

- **Giữ nguyên `objectName`** của các widget, ví dụ `lblKpiCustomersValue` hay `tblSegmentSummary`, vì code tìm widget theo tên này.
- Style nằm ở `ui/style.qss`. Muốn áp style cho widget mới thì thêm *Dynamic Property* kiểu String tên `cssClass`, giá trị là `card`, `cardTitle`, `kpiValue`, `primary`, …
- Biểu đồ được gắn bằng code vào các khung `hostRevenueChart` và `hostSegmentChart`.
- Chữ `&` trên nút phải gõ thành `&&` (ví dụ `RFM && Model`). Nếu gõ một `&` thì Qt hiểu là phím tắt và hiện dấu gạch dưới.

## Cấu trúc

```
main.py                      chạy app (user giả)
ui/main_window.ui            khung chính + sidebar        ← Qt Designer
ui/pages/dashboard.ui        trang Dashboard              ← Qt Designer
ui/style.qss                 style chung cho cả app (Login dùng chung)
app/main_window.py           điều hướng, phân quyền, đăng xuất
app/pages/dashboard_page.py  đổ dữ liệu vào Dashboard
app/pages/placeholder_page.py  trang tạm cho màn hình chưa làm
app/widgets/charts.py        biểu đồ cột + vành khuyên (QPainter)
services/__init__.py         chọn nguồn dữ liệu (mock ↔ thật)
services/mock_service.py     dữ liệu giả
```

## "Hợp đồng" dữ liệu với các thành viên khác

Giao diện **chỉ** gọi các hàm dưới đây. Phần thật (DAO/MySQL, model) cần viết `services/db_service.py` có **đúng tên hàm và đúng kiểu trả về**, rồi đổi dòng import trong `services/__init__.py`.

| Hàm | Trả về | Ai cung cấp |
|---|---|---|
| `get_dashboard_stats()` | `dict`: `total_customers`, `total_invoices`, `total_revenue` (£), `num_segments`, `date_from`, `date_to` (`datetime`) | Task 6 |
| `get_monthly_revenue()` | `list[(“YYYY-MM”, float)]`, tăng dần theo tháng | Task 6 |
| `get_segment_summary()` | `list[dict]`: `cluster_id`, `segment_name`, `customers`, `avg_recency`, `avg_frequency`, `avg_monetary`, `revenue`, `color` (hex) | Task 3 / 6 + tên phân khúc từ mục 3.5 |

**Login → MainWindow** (Task 7, 8): sau khi đăng nhập thành công thì gọi

```python
win = MainWindow(user={"username": ..., "full_name": ..., "role": "Admin" | "User"}, service=service)
win.logout_requested.connect(<hàm quay về màn Login>)
win.show()
```

### Sẽ bổ sung khi làm Task 11, 12 (cần thống nhất trước)

- `get_transactions(keyword="", country=None, date_from=None, date_to=None, limit=500)` → `list[dict]`
- `predict_segment(recency: float, frequency: float, monetary: float)` → `dict`: `cluster_id`, `segment_name` (Task 14)
- `get_customers_by_segment(segment_name)` → `list[dict]`, `get_marketing_actions(segment_name)` → `list[str]`

> Số liệu trong `mock_service.py` được tính thử từ `online_retail_II.xlsx`, với K-Means K = 2. Tên phân khúc "High-Value Loyal" / "Low-Engagement" là **tên tạm**, cần thay bằng tên chính thức trong mục 3.5.
