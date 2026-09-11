# Ghi chú phát hành cho người triển khai

Gói phát hành tạo ra ứng dụng desktop có giao diện Qt và toàn bộ mã Python đã được đóng gói. Khi khách mở lần đầu, ảnh mốc và cấu hình mặc định được sao chép sang thư mục dữ liệu riêng của tài khoản; các lần cập nhật không ghi đè hiệu chuẩn của khách.

## Tạo gói

- macOS: chạy `bash scripts/build_macos.sh` trên macOS.
- Windows: chạy `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1` trên Windows.

Không dùng macOS để tạo bản Windows hoặc ngược lại. PyInstaller tạo mã thực thi cho chính hệ điều hành đang chạy.

Tệp gửi khách nằm tại `release/Plant-Automation-macOS.zip`, `release/Plant-Automation-Windows-Setup.exe` (khuyến nghị) hoặc `release/Plant-Automation-Windows.zip` (portable).

Bản Windows Setup dùng Inno Setup, cài theo tài khoản người dùng nên thường không cần quyền quản trị để cài ứng dụng. Sau khi cài, app kiểm tra ADB/scrcpy và hiển thị nút cài có xác nhận nếu còn thiếu.

## Điều kiện giao hàng

Gói hiện đóng gói ứng dụng, OpenCV và Qt. App có trình thiết lập có xác nhận cho ADB/scrcpy: macOS dùng Homebrew (`android-platform-tools` và `scrcpy`), Windows dùng WinGet (`Google.PlatformTools` và `Genymobile.scrcpy`). Nếu máy khách không có trình quản lý gói hoặc mạng, kỹ thuật viên vẫn phải cài hai công cụ thủ công. Không sao chép tùy tiện các tệp Homebrew sang máy khác vì phụ thuộc thư viện hệ thống có thể khác.

Trước khi giao, cần kiểm tra trên một tài khoản macOS/Windows sạch: mở app, nhận USB debugging, tạo ảnh mốc, chạy chế độ xem trước và chạy một vòng có xác nhận.
