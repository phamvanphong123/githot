HỆ THỐNG ĐĂNG KÝ SỰ KIỆN CÔNG TY XYZ
====================================

BẢN GIAO DIỆN NÂNG CẤP
- Bố cục đăng nhập dạng 2 cột, nhận diện thương hiệu XYZ Events.
- Giao diện hiện đại, responsive trên laptop và điện thoại.
- Danh sách sự kiện dạng thẻ, thông tin địa điểm/thời gian, trạng thái và thanh sức chứa.
- Thanh điều hướng, bảng quản trị, biểu mẫu và dashboard đồng bộ phong cách.

1. Cài Python 3.10 trở lên.
2. Mở CMD/Terminal tại thư mục chứa app.py.
3. Cài thư viện:
   py -m pip install -r requirements.txt
4. Chạy ứng dụng:
   py app.py
5. Mở trình duyệt:
   http://127.0.0.1:5000

TÀI KHOẢN DEMO (mật khẩu chung: Employee@123)
- Admin: admin@xyz.com
- Organizer: organizer@xyz.com
- Organizer nhân sự: organizer.hr@xyz.com
- Employee: employee@xyz.com
- Tài khoản bị khóa để kiểm thử: locked@xyz.com

CÁC CHỨC NĂNG ĐÃ BỔ SUNG
- Đăng nhập, phân quyền và đăng xuất.
- Danh sách sự kiện, tìm kiếm, lọc ngày/phòng ban/trạng thái.
- Xem chi tiết, đăng ký và hủy đăng ký, xem sự kiện đã đăng ký.
- Organizer/Admin tạo, sửa, hủy sự kiện.
- Quản lý danh sách người đăng ký, xác nhận và điểm danh.
- Dashboard thống kê sự kiện, lượt đăng ký, lượt điểm danh, tỷ lệ tham gia.
- Admin khóa/mở tài khoản.
- Validation dữ liệu, CSRF token, truy vấn SQL tham số.

LƯU Ý
- Đây là bản chạy thử học tập. Đổi SECRET_KEY trước khi triển khai thật.
- Muốn tạo lại dữ liệu mẫu, đóng ứng dụng rồi xóa xyz_events.db; chạy lại app.py.
  Thao tác này sẽ làm mất dữ liệu đã nhập và tạo lại dữ liệu mẫu.
- Thời gian trong biểu mẫu dùng định dạng YYYY-MM-DD HH:MM.
