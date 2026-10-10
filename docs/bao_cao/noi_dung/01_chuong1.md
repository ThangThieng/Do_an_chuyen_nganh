# CHƯƠNG 1: GIỚI THIỆU BÀI TOÁN

## 1.1. Bối cảnh và lý do chọn đề tài

Moodle là hệ thống quản lý học tập được nhiều trường đại học sử dụng, trong đó có Trường Đại học Đà Lạt. Mỗi lần sinh viên mở một môn học, xem bài giảng, nộp bài hay được điểm danh, Moodle đều ghi lại một dòng dữ liệu. Sau vài tuần học, lượng dữ liệu này đủ để trả lời những câu hỏi mà giảng viên và người quản lý đào tạo thường phải đoán: sinh viên nào đã lâu không vào môn, lớp nào nộp bài đều, khung giờ nào hệ thống chịu tải cao.

Theo tài liệu yêu cầu của đề tài, CSDL Moodle 3.9 có hơn 460 bảng, riêng bảng nhật ký `mdl_logstore_standard_log` có thể lên tới hàng triệu dòng. Một câu hỏi thống kê thường phải kết từ 5 đến 20 bảng, chạy nhiều phút và làm chậm chính máy chủ đang phục vụ việc học. Các báo cáo sẵn có của Moodle chủ yếu xem theo từng môn, chưa gom thành bức tranh chung của khoa và chưa chỉ ra sinh viên nào đang có dấu hiệu bỏ học.

Nhóm chọn đề tài vì bài toán có người dùng cụ thể với nhu cầu mô tả được rõ, phù hợp để thực hành đầy đủ các bước phân tích và thiết kế của môn học. Đề tài cũng đặt ra một vấn đề thiết kế có thật: đọc dữ liệu từ một hệ thống lớn mà không làm ảnh hưởng tới hệ thống đó, rồi trình bày kết quả sao cho người dùng nắm được trong vài giây.

## 1.2. Khảo sát hiện trạng

### 1.2.1. Nguồn thông tin

Hiện trạng và yêu cầu của hệ thống được xác định sau quá trình tìm hiểu tài liệu và tham khảo ý kiến giảng viên hướng dẫn. Tài liệu chính gồm: tài liệu mô tả yêu cầu kỹ thuật và nghiệp vụ của đề tài, tài liệu cấu trúc CSDL Moodle 3.9, và bốn bài báo về bảng điều khiển phân tích học tập trên Moodle (mục 1.3).

### 1.2.2. Hiện trạng tổ chức

Về đối nội, hệ thống phục vụ hai nhóm người trong Khoa Công nghệ Thông tin. Người quản lý đào tạo và quản trị hệ thống cần nắm quy mô đào tạo theo khoa, môn học, học kỳ, theo dõi mức độ sử dụng hệ thống và lập báo cáo định kỳ. Giảng viên phụ trách một hoặc nhiều môn trên Moodle, cần biết sinh viên nào trong lớp đang vắng học, ít tương tác hoặc thiếu bài để hỗ trợ kịp thời.

Về đối ngoại, hệ thống có quan hệ với Moodle LMS, nơi phát sinh toàn bộ dữ liệu học tập, và với sinh viên, đối tượng được theo dõi nhưng không trực tiếp sử dụng hệ thống.

### 1.2.3. Hiện trạng nghiệp vụ

Theo tài liệu yêu cầu, để tìm sinh viên vắng học hay bỏ bài tập, giảng viên hiện phải lọc thủ công các tệp Excel tải từ Moodle. Bảng 1.1 tóm tắt các điểm nghẽn.

Bảng: Các điểm nghẽn trong quy trình hiện tại
%w 6,30,64
| STT | Công việc | Điểm nghẽn |
|---|---|---|
| 1 | Phát hiện sinh viên có nguy cơ | Ghép thủ công dữ liệu điểm danh, bài nộp, lần truy cập; mỗi giảng viên tự đặt ngưỡng; thường phát hiện khi đã muộn |
| 2 | Thống kê quy mô đào tạo theo khoa | Báo cáo Moodle xem theo từng môn, tổng hợp toàn khoa phải cộng tay |
| 3 | Theo dõi tải hệ thống | Không có biểu đồ lượt truy cập và người dùng theo giờ để dự báo giờ cao điểm |
| 4 | Lập báo cáo định kỳ | Dữ liệu xuất ra chưa lọc theo khoa, học kỳ, phải chỉnh lại |
| 5 | Truy vấn trực tiếp CSDL Moodle | Câu truy vấn nặng chạy trên máy chủ đang phục vụ học tập |

Nhóm ưu tiên việc phát hiện sinh viên nguy cơ, vì phát hiện chậm ở khâu này ảnh hưởng trực tiếp tới người học; tài liệu yêu cầu cũng xếp chức năng cảnh báo là chức năng trọng tâm.

### 1.2.4. Hiện trạng tin học

Hệ thống nguồn là Moodle 3.9 trên MySQL hoặc PostgreSQL; dữ liệu điểm danh nằm trong plugin `mod_attendance`. CSDL Moodle chuẩn hóa cao, phù hợp cho việc ghi nhưng không phù hợp cho truy vấn tổng hợp nhiều bảng. Người dùng được giả định đã quen thao tác trên trình duyệt và trên Moodle.

Từ hiện trạng này, tài liệu yêu cầu đề xuất hướng giải quyết: xây dựng tiến trình ETL định kỳ đọc dữ liệu thô từ Moodle, tổng hợp vào một CSDL PostgreSQL riêng, để ứng dụng web chỉ truy vấn CSDL này với thời gian phản hồi dưới 1 giây.

## 1.3. Các nghiên cứu liên quan

Pan và cộng sự [3] tổng quan 27 bài báo (2012–2023) về các biện pháp can thiệp dựa trên phân tích học tập trong LMS, nhận thấy dashboard xuất hiện nhiều trong các can thiệp có hiệu quả và khuyến nghị không bỏ quên công cụ dành cho giảng viên. Nhận xét này củng cố quyết định đặt phân hệ giảng viên làm trọng tâm và cho phép ghi nhận can thiệp ngay trên hệ thống.

Ong và Singh [4] xây dựng dashboard cho Moodle bằng Python và Dash theo mô hình "nguồn Moodle – xử lý – hiển thị", tương tự kiến trúc của đề tài; đề tài bổ sung cơ chế cập nhật định kỳ bằng ETL có lập lịch. Peraić và Grubišić [5] đánh giá dashboard cho sinh viên bằng bảng hỏi với 33 người dùng, cho thấy dashboard nên được kiểm tra bằng ý kiến người dùng thật về tính dễ dùng và tính hữu ích. Alonso-Fernández và cộng sự [6] đề xuất plugin Moodle theo dõi tiến độ gần thời gian thực cho giảng viên, là cơ sở cho màn hình "Tiến độ lớp".

Khác với các công trình trên, đề tài phục vụ đồng thời người quản lý (nhìn toàn khoa) và giảng viên (nhìn từng lớp), và dùng luật cảnh báo ba tiêu chí có ngưỡng rõ ràng để giảng viên hiểu vì sao một sinh viên bị đánh dấu.

## 1.4. Mục tiêu và phạm vi

Mục tiêu của đồ án là phân tích, mô hình hóa và thiết kế hệ thống theo hướng đối tượng (use case, DFD, sơ đồ lớp, tuần tự, trạng thái, hoạt động, triển khai), thiết kế dữ liệu và giao diện, rồi cài đặt thành ứng dụng web chạy được, có kiểm thử và đo hiệu năng.

Phạm vi:

- Người dùng: quản trị viên và giảng viên; sinh viên không đăng nhập vào hệ thống.
- Chức năng theo đề tài: thống kê phân cấp Khoa – Môn – Sinh viên, theo dõi lưu lượng truy cập, xuất báo cáo; cảnh báo sinh viên nguy cơ, thống kê tiến độ lớp.
- Chức năng quản trị để hoàn thiện hệ thống: đổi mật khẩu, quản lý người dùng, nhật ký ETL, tra cứu danh mục môn học, sao lưu và phục hồi, trợ giúp.
- Dữ liệu: hệ thống chạy trên CSDL `moodle_src` gồm 25 bảng giữ đúng tên bảng, tên cột, kiểu dữ liệu của Moodle 3.9, chứa dữ liệu mô phỏng một học kỳ của Khoa Công nghệ Thông tin (15 môn, 500 sinh viên, 8 giảng viên, khoảng 1,2 triệu dòng nhật ký).
- Ngoài phạm vi: mô hình học máy dự báo, gửi tin nhắn thật qua Moodle, chức năng dành cho sinh viên.

## 1.5. Phương pháp thực hiện

Nhóm thực hiện theo trình tự: tìm hiểu tài liệu yêu cầu và cấu trúc CSDL Moodle; phân tích và mô hình hóa yêu cầu; thiết kế kiến trúc, dữ liệu, giao diện; cài đặt theo bốn phần (CSDL, dữ liệu mô phỏng và ETL, API, giao diện); kiểm thử và triển khai bằng Docker. Công cụ chính gồm PostgreSQL 18, Python 3.11 (pandas, SQLAlchemy, FastAPI), React 18 với Chart.js và Ant Design, Docker Compose; sơ đồ UML vẽ bằng PlantUML.

Báo cáo gồm bảy chương: Chương 2 xác định và mô hình hóa yêu cầu; Chương 3 thiết kế hệ thống; Chương 4 thiết kế dữ liệu; Chương 5 thiết kế màn hình; Chương 6 cài đặt và thử nghiệm; Chương 7 nhận xét và kết luận.
