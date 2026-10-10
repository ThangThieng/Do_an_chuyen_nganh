# CHƯƠNG 7: NHẬN XÉT VÀ KẾT LUẬN

## 7.1. Nhận xét

### 7.1.1. Kết quả đạt được

Hệ thống đáp ứng đủ năm chức năng của tài liệu yêu cầu (Admin 1.1–1.3, Giảng viên 2.1–2.2) và giữ đúng các dạng trực quan hóa được chỉ định: thẻ KPI, biểu đồ cột chồng, bảng phân cấp có drill-down, biểu đồ đường hai trục, đèn giao thông, biểu đồ tròn, thanh tiến độ, biểu đồ so sánh cá nhân với trung bình lớp. Nhóm bổ sung sáu chức năng quản trị để hệ thống có đủ năm nhánh thực đơn chuẩn: đổi mật khẩu, quản lý người dùng, nhật ký ETL, danh mục môn học, sao lưu – phục hồi và trợ giúp.

Những điểm nhóm đánh giá là làm tốt đều có số liệu kiểm chứng: số liệu bảng fact khớp với truy vấn độc lập trên Moodle; luật cảnh báo đạt độ phủ 97,8% và độ chính xác 85,3% trên dữ liệu mô phỏng; truy vấn chậm nhất 8,55 ms trên dữ liệu gấp 10 lần; toàn bộ 284 ca pytest, 8 ca vitest và 32 ca E2E đạt, kể cả khi chạy trên Docker.

### 7.1.2. Đánh giá theo các bước phân tích và thiết kế

Bảng: Tự đánh giá theo các bước phân tích và thiết kế
%w 22,14,64
| Bước | Mức độ | Nhận xét |
|---|---|---|
| Xác định và mô hình hóa yêu cầu | Đạt | Yêu cầu chia theo bốn nhóm; bảng trách nhiệm cho sáu loại yêu cầu; 17 use case (các use case chính có đặc tả); DFD mức ngữ cảnh và DFD theo quy ước D1–D6 |
| Thiết kế hướng đối tượng | Đạt ở mức mô hình | Sơ đồ lớp phân tích mô tả đúng khái niệm nghiệp vụ; mã nguồn tổ chức theo mô-đun hàm và lớp dữ liệu, phù hợp với bài toán tổng hợp dữ liệu (mục 3.3.2), nên mô hình lớp và mã nguồn không tương ứng một – một |
| Thiết kế dữ liệu | Đạt, có ngoại lệ | Áp dụng quy tắc ánh xạ cơ bản và ánh xạ kế thừa; không tách bảng cho thuộc tính danh sách, thuộc tính rời rạc và phi chuẩn hóa bảng fact, mỗi ngoại lệ có lý do và số liệu đi kèm (mục 4.2) |
| Thiết kế giao diện | Đạt | Trả lời bốn câu hỏi định vị, kiểm tra dữ liệu ở mức ô và mức biểu mẫu, xác nhận trước thao tác không hoàn tác được, đạt kiểm tra WCAG 2.1 AA, dùng được trên điện thoại |

### 7.1.3. Hạn chế

1. Dữ liệu là mô phỏng cho một khoa; hệ thống chưa chạy trên Moodle thật của trường.
2. Chưa kiểm thử chấp nhận với giảng viên, nên mức độ hữu ích thực tế của danh sách cảnh báo chưa được xác nhận.
3. "Lượt truy cập" đếm từ nhật ký sự kiện của Moodle, là chỉ số gần đúng của tải hệ thống, không phải số yêu cầu HTTP thật.
4. Nút "Gửi tin nhắn Moodle" chỉ ghi nhật ký can thiệp, chưa gọi Web Service của Moodle.
5. Ngưỡng và luật xếp mức chỉ đổi được qua tệp cấu hình, chưa có màn hình cho người dùng nghiệp vụ.
6. Bộ đếm đăng nhập sai nằm trong bộ nhớ từng tiến trình; khi API chạy hai tiến trình, mỗi tiến trình đếm riêng.
7. Sao lưu chỉ gồm CSDL phân tích và chưa có lịch sao lưu tự động.
8. Hiệu năng được đo trước khi bổ sung các chức năng quản trị, chưa đo lại sau đó.

## 7.2. Kết luận

Đồ án đã xây dựng được một hệ thống trực quan hóa dữ liệu Moodle chạy được từ đầu đến cuối: đọc dữ liệu nguồn mà không ghi ngược, tổng hợp định kỳ vào CSDL phân tích và trình bày cho hai nhóm người dùng với thời gian phản hồi dưới 1 giây. Qua đồ án, nhóm thực hành đầy đủ các bước của môn học: xác định yêu cầu, mô hình hóa bằng use case và DFD, thiết kế lớp, tuần tự, trạng thái, hoạt động, triển khai, ánh xạ dữ liệu và thiết kế giao diện.

Nhóm rút ra hai bài học. Thứ nhất, bảng trách nhiệm cho các loại yêu cầu tiến hóa, an toàn, bảo mật giúp nhìn thấy những chức năng quản trị mà nếu chỉ tập trung vào biểu đồ sẽ dễ bỏ sót. Thứ hai, quy tắc ánh xạ và chuẩn hóa nên được áp dụng có cân nhắc: với CSDL phục vụ đọc và tổng hợp, một số ngoại lệ có chủ đích cho hiệu năng tốt hơn, miễn là tính toàn vẹn được bảo vệ bằng ràng buộc và kiểm thử.

## 7.3. Hướng phát triển

- Kiểm thử chấp nhận với 2–3 giảng viên: xem danh sách mức đỏ của lớp mình và cho biết đồng ý hay không (mục tiêu từ 80% trở lên), kết hợp bảng hỏi về tính dễ dùng như công trình [5].
- Chạy thử trên bản sao dữ liệu Moodle thật đã ẩn danh hóa và hiệu chỉnh lại ngưỡng.
- Màn hình cấu hình ngưỡng rủi ro cho quản trị viên, có lưu lịch sử thay đổi.
- Mô hình học máy (hồi quy logistic hoặc random forest) dự báo nguy cơ trên các đặc trưng sẵn có, dùng song song với luật hiện tại để so sánh.
- Gửi cảnh báo tự động qua email hoặc tin nhắn Moodle khi sinh viên chuyển sang mức đỏ; sao lưu tự động theo lịch.
