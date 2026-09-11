# Plant Automation — Hướng dẫn sử dụng

Phiên bản này tự động trồng, tưới và thu hoạch trong ứng dụng trồng cây Android qua cáp USB. Bạn luôn chịu trách nhiệm bảo đảm mình có quyền sử dụng ứng dụng và tính năng tự động hóa.

## 1. Chuẩn bị một lần

1. Khi mở app lần đầu, nếu thiếu công cụ, bấm **Cài ADB / scrcpy** và xác nhận. App sẽ dùng trình quản lý gói chính thức của hệ điều hành; có thể yêu cầu Internet và quyền quản trị. Nếu nút này không khả dụng, cài **ADB (Android Platform Tools)** và **scrcpy** thủ công rồi mở lại app.
2. Trên Android, bật **Tùy chọn nhà phát triển → Gỡ lỗi USB**.
3. Cắm cáp dữ liệu, mở khóa điện thoại và chọn **Cho phép gỡ lỗi USB** khi điện thoại hỏi.
4. Đưa game về đúng màn hình ruộng, xoay ngang như khi hiệu chuẩn. Không để popup che ruộng.

## 2. Mở phần mềm

**macOS:** mở `Plant Automation.app`. Nếu macOS chặn lần đầu, giữ Control, bấm ứng dụng và chọn **Open**.

**Windows:** giải nén gói ZIP, sau đó mở `Plant Automation.exe`. Không di chuyển riêng tệp EXE ra ngoài thư mục đã giải nén.

Màn hình Dashboard sẽ hiển thị điện thoại đã kết nối, ảnh xem trước, 16 ô đất và nhật ký hoạt động.
App tự nhận ADB/scrcpy ở các vị trí phổ biến của Homebrew và Android Studio, kể cả khi bạn mở app từ Finder thay vì Terminal.

## 3. Hiệu chuẩn ruộng trước lần chạy đầu

1. Bảo đảm toàn bộ 16 ô đều trống.
2. Trong thư mục dữ liệu của ứng dụng, thay ảnh `captures/empty-reference.png` bằng ảnh mốc đã chụp từ đúng điện thoại và giao diện đang dùng. Có thể dùng lệnh dòng lệnh `capture-empty-reference` của bản kỹ thuật để tạo ảnh này.
3. Mở lại ứng dụng. Khi ảnh xem trước và số ô trống hiển thị đúng, hiệu chuẩn đã sẵn sàng.

Đường dẫn dữ liệu của ứng dụng:

- macOS: `~/Library/Application Support/Plant Automation/`
- Windows: `%LOCALAPPDATA%\Plant Automation\`

Không xóa thư mục này khi còn muốn giữ ảnh mốc, cấu hình cây và mẫu hạt.

## 4. Chạy tự động hóa

1. Chọn điện thoại ở mục **Thiết bị** và chọn **Cây trồng**.
2. Tùy chọn: bấm **Mở Mirror** để quan sát game qua scrcpy.
3. Chọn tốc độ quét và thời gian chờ popup. Khuyến nghị giữ 3 giây và 5 giây trong lần đầu.
4. Lần kiểm tra đầu tiên, bỏ chọn **Cho phép thao tác thật**, rồi bấm **Bắt đầu vòng lặp**. Phần mềm chỉ ghi dự kiến trong nhật ký, không chạm điện thoại.
5. Khi kết quả đúng, chọn **Cho phép thao tác thật** và bấm bắt đầu lại.
6. Dùng **Dừng an toàn** hoặc đóng ứng dụng để ngừng vòng lặp.

Trong khi chạy, phần mềm sẽ:

- chờ và quét lại khi popup tạm thời che ruộng;
- bấm một lần nút hàng loạt khi nhận ra thông báo tưới hoặc thu hoạch;
- khi có ô trống, bấm một ô để mở thanh hạt, rồi chọn cùng hạt liên tiếp. Các nhịp bù có chủ đích để xử lý game tải chậm.

## 5. Cây trồng và thiết bị mới

- Dưa leo có sẵn mẫu nhận diện hạt.
- Hướng dương có tọa độ dự phòng. Để nhận diện khi vị trí hạt thay đổi, kỹ thuật viên mở thanh hạt và tạo mẫu ảnh cho hướng dương một lần.
- Khi đổi sang điện thoại có tỷ lệ màn hình khác, cần tạo hồ sơ thiết bị mới. Phần mềm tự co giãn tọa độ nếu chỉ thay đổi độ phân giải cùng tỷ lệ; nếu tỷ lệ khác đáng kể, nó dừng an toàn thay vì bấm nhầm.

## Xử lý sự cố nhanh

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không thấy điện thoại | Kiểm tra cáp dữ liệu, mở khóa máy và xác nhận USB debugging. |
| Báo không tìm thấy ADB/scrcpy | Cài Platform Tools và scrcpy, sau đó mở lại ứng dụng. |
| Dashboard không nhận đúng ô đất | Tạo lại ảnh mốc khi ruộng trống, cùng điện thoại, hướng xoay và giao diện. |
| Không trồng được hoặc chọn sai hạt | Tắt thao tác thật, mở Mirror để kiểm tra; tạo lại mẫu hạt hoặc chọn đúng cây. |
| Có popup | Chờ popup biến mất; phần mềm sẽ quét lại sau thời gian đã đặt. |

## An toàn dữ liệu

Ảnh quét thường xuyên chỉ tồn tại tạm thời và bị xóa ngay sau khi nhận diện. Chỉ ảnh mốc, mẫu hạt và ảnh do người dùng chủ động chụp mới nằm trong thư mục dữ liệu.
