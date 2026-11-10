# RFM Insight — QA (87 test case / 7 luồng)

Nguồn: `RFM_Insight_Test_Cases (1).xlsx` do nhóm cung cấp. Ma trận trong `matrix.json` giữ **đủ 87 mã TC và 7 luồng với 26 bước**. Kỳ vọng cũ về Demo/Retry trong Excel cần được nhóm cập nhật; runner **không phục hồi Demo**.

## Chạy ngay sau khi pull nhánh `test`

Đứng ở thư mục gốc repo:

```powershell
$env:PYTHONUTF8 = "1"
python -m qa.run
```

Không cần MySQL để chạy chế độ mặc định. Runner không dùng mật khẩu mẫu, không tự khởi tạo bảng, không dừng MySQL, không xóa dữ liệu và không sửa các tệp model. Nếu thiếu thư viện, một TC phụ thuộc thư viện được ghi `SKIP` có lý do; không tự khai PASS.

Để cài thư viện trong `.venv` từ các tệp của dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r ui_app/requirements.txt -r customer_segmentation/requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m qa.run
```

Nếu đã có `.venv` như khi chạy `launcher.py`, chỉ dùng lệnh cuối.

## Chế độ mở rộng

```powershell
# Test PyQt6 với màn hình giả lập, không cần mở cửa sổ thật
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -X utf8 -m qa.run --gui

# Đối chiếu SELECT với MySQL đã import: KHÔNG ghi database
.\.venv\Scripts\python.exe -X utf8 -m qa.run --db

# Kiểm thử dry-run import (đọc dữ liệu Excel lớn, không ghi MySQL)
.\.venv\Scripts\python.exe -X utf8 -m qa.run --slow

# Ghi báo cáo JSON vào qa/results.json (bị .gitignore bỏ qua)
.\.venv\Scripts\python.exe -X utf8 -m qa.run --gui --report qa/results.json
```

**PASS:** Toàn bộ phần kiểm tra đã được thực thi bằng assertion. **FAIL:** Kết quả thực tế sai hoặc có exception. **SKIP:** Chưa đủ môi trường/điều kiện để kết luận; các assertion chỉ bao phủ một phần cũng được để SKIP. **NOT_RUN (flow):** Từng bước E2E chưa được điều khiển nối tiếp, dù TC riêng có PASS; tuyệt đối không coi là PASS.

`DB-04` (nạp lại toàn bộ 6 bảng), test khóa Admin thật và test tắt MySQL chỉ được thực hiện trên **database thử nghiệm tách biệt, đã sao lưu**, không nằm trong lệnh chạy mặc định. Hiện runner ghi `SKIP` cho các trường hợp chưa có phương án cô lập; các phần kiểm thử thủ công vẫn phải được tester ghi nhận trong Excel.

`--strict` chỉ phù hợp làm cổng chấp nhận cuối: trả mã lỗi nếu có bất kỳ FAIL, SKIP hoặc luồng chưa chạy. Với CI mặc định, chỉ FAIL làm lệnh trả mã lỗi, nhưng tổng số SKIP và luồng NOT_RUN luôn hiển thị.

`qa/matrix.json` là bảng liên kết mã / tên / kỳ vọng / luồng, không phải dữ liệu giao dịch mẫu. Không có `.env`, file báo cáo, screenshot hay dữ liệu giả được commit vào repo.