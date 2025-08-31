# Hệ thống Điểm danh bằng Mã QR

Ứng dụng web được xây dựng bằng Python Dash để tạo và quản lý hệ thống điểm danh tự động cho các lớp học thông qua mã QR và Google Forms. Ứng dụng giúp giảng viên tạo mã điểm danh duy nhất cho mỗi buổi học, giới hạn thời gian điểm danh và tự động phát hiện các trường hợp gian lận.

## ✨ Tính năng chính

Tạo mã QR động: Tự động sinh mã QR với mã điểm danh duy nhất dựa trên thời gian thực.

Giới hạn thời gian: Giảng viên có thể tùy chỉnh thời gian hiệu lực của mã QR (ví dụ: 1, 5, 10, 15 phút) để đảm bảo sinh viên chỉ điểm danh khi có mặt tại lớp.

Tích hợp Google Forms & Sheets: Dữ liệu điểm danh được tự động lưu trữ và quản lý trên Google Sheet, dễ dàng truy cập và xử lý.

Phát hiện gian lận: Tự động highlight (tô đỏ) các lượt điểm danh của sinh viên sử dụng mã QR cũ hoặc không hợp lệ tại thời điểm điểm danh.

Giao diện trực quan: Hiển thị danh sách điểm danh theo thời gian thực, kèm theo các bộ lọc tiện lợi theo ngày và lớp học.

Tự động làm mới: Bảng điểm danh tự động cập nhật để giảng viên theo dõi.

Xuất báo cáo: Dễ dàng xuất toàn bộ dữ liệu điểm danh ra file Excel chỉ với một cú nhấp chuột.

## 🚀 Cài đặt và Chạy ứng dụng

Yêu cầu

Python 3.8+

Tài khoản Google

Bước 1: Thiết lập môi trường Google Cloud & Sheets

Đây là bước quan trọng nhất để ứng dụng có thể giao tiếp với Google Sheets.

Tạo Google Form:

Tạo một Google Form với các câu hỏi cần thiết (ví dụ: Họ và tên, Mã số sinh viên, Lớp học phần).

Quan trọng: Thêm một câu hỏi dạng "Short answer" (Trả lời ngắn) với tên chính xác là Mã điểm danh.

Liên kết Form với một Google Sheet mới.

Tạo Service Account trên Google Cloud:

Truy cập Google Cloud Console và tạo một dự án mới.

Kích hoạt Google Drive API và Google Sheets API cho dự án.

Tạo một Service Account, cấp quyền Editor.

Tạo một Key dạng JSON cho Service Account và tải về.

Chia sẻ quyền cho Google Sheet:

Mở file JSON vừa tải, sao chép giá trị của trường "client_email" (có dạng ...@...iam.gserviceaccount.com).

Mở Google Sheet, nhấn nút Share và chia sẻ quyền Editor cho địa chỉ email đó.

(Để xem hướng dẫn chi tiết từng bước, hãy tham khảo tài liệu của Google Cloud.)

Bước 2: Cấu hình ứng dụng

Clone repository này:

git clone https://github.com/thanvanvan/diem-danh.git

cd diem-danh

Tạo môi trường ảo và cài đặt thư viện:

python -m venv venv

### Trên Windows

.\venv\Scripts\activate

### Trên macOS/Linux

source venv/bin/activate

pip install -r requirements.txt

Tạo và cấu hình file .env:

Tạo một file mới tên là .env trong thư mục gốc.

Mở file và thêm các biến môi trường sau:

#### .env

#### ID của Google Sheet (lấy từ URL)

SPREADSHEET_ID=""

#### ID của Google Form (lấy từ URL)

FORM_ID=""

#### Nội dung file credentials.json (dán toàn bộ vào một dòng duy nhất)

GCP_CREDENTIALS_JSON="{ \"type\": \"service_account\", ... }"

Bước 3: Chạy ứng dụng

Sau khi đã cấu hình xong, chạy lệnh sau trong terminal:

python app.py

Mở trình duyệt và truy cập vào địa chỉ http://127.0.0.1:8050/.

## 📖 Hướng dẫn sử dụng

Tạo mã QR:

Chọn thời gian hiệu lực mong muốn trên thanh trượt.

Nhấn nút "Tạo QR mới".

Một mã QR và mã điểm danh tương ứng sẽ xuất hiện. Trình chiếu mã QR này cho sinh viên.

Theo dõi điểm danh:

Bảng điểm danh sẽ tự động làm mới.

Các lượt điểm danh của sinh viên sử dụng mã cũ sẽ được tô màu đỏ để giảng viên dễ dàng nhận biết.

Giảng viên có thể sử dụng bộ lọc để xem lại lịch sử điểm danh theo ngày hoặc theo lớp.

Kết thúc:

Nhấn nút "Xuất Excel" để tải về báo cáo điểm danh của toàn bộ các buổi học.

## 🛠️ Công nghệ sử dụng

Backend & Frontend: Dash (Python)

Biểu đồ & Bảng: Plotly, Dash DataTable

Giao diện: Dash Bootstrap Components

Tương tác với Google API: gspread, oauth2client

Tạo mã QR: qrcode

## 📜 Giấy phép

Dự án này được cấp phép theo Giấy phép MIT. Xem file LICENSE để biết thêm chi tiết.
