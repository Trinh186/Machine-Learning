-- Cập nhật mô tả 2 phân khúc cho database đã tạo từ trước (không xóa dữ liệu nào).
-- Database mới tạo từ database.sql đã có sẵn nội dung này, không cần chạy.
-- Chạy trong MySQL Workbench (chọn schema customer_segmentation) hoặc:
--   mysql -u root -p customer_segmentation < customer_segmentation/database/update_segment_descriptions.sql
SET NAMES utf8mb4;
UPDATE `segments` SET `description` = 'Nhóm khách hàng mua gần đây, mua thường xuyên và chi tiêu nhiều: trung bình 26 ngày kể từ lần mua cuối, 8,4 hóa đơn và 4.230 £ mỗi khách. Chỉ chiếm 38,2% số khách hàng nhưng mang lại 84,4% doanh thu.'
WHERE `segment_name_en` = 'High-Value Customers';
UPDATE `segments` SET `description` = 'Nhóm khách hàng đã lâu chưa quay lại, mua ít và chi tiêu thấp: trung bình 135 ngày kể từ lần mua cuối, 1,7 hóa đơn và 484 £ mỗi khách; 56% mới mua đúng một lần. Chiếm 61,8% số khách hàng nhưng chỉ tạo ra 15,6% doanh thu.'
WHERE `segment_name_en` = 'Low-Activity Customers';
