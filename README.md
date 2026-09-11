# Plant Automation (MVP cá nhân)

Ứng dụng dòng lệnh nhỏ để điều khiển **một** điện thoại Android đã kết nối USB:

- liệt kê thiết bị ADB;
- mở cửa sổ `scrcpy` để quan sát;
- chụp ảnh màn hình;
- thực thi kịch bản chạm, vuốt và chờ.

`scrcpy` chỉ dùng để hiển thị/điều khiển thủ công. Các thao tác tự động đi trực tiếp qua ADB để có thể ghi log và kiểm soát lỗi.

## Điều kiện cài đặt

- Python 3.10+
- [Android Platform Tools / ADB](https://developer.android.com/tools/releases/platform-tools)
- [scrcpy](https://github.com/Genymobile/scrcpy)
- Bật **Developer options → USB debugging** trên điện thoại, sau đó xác nhận khóa RSA trên điện thoại khi cắm cáp.

Kiểm tra:

```bash
python3 -m plant_automation devices
```

Nếu trạng thái là `unauthorized`, hãy mở khóa điện thoại và bấm **Allow**. Nếu danh sách trống, kiểm tra lại cáp dữ liệu, chế độ USB và USB debugging.

## Sử dụng

```bash
# Mở giao diện desktop: chọn thiết bị, ảnh mốc, xem nhật ký và Bắt đầu/Dừng vòng lặp
python3 -m plant_automation gui

# Mở màn hình điện thoại qua scrcpy (tự chọn thiết bị nếu chỉ có một)
python3 -m plant_automation mirror

# Chụp màn hình vào thư mục captures/
python3 -m plant_automation screenshot

# Khi 16 ô đều trống và không có popup, lưu ảnh mốc một lần
python3 -m plant_automation capture-empty-reference

# Chỉ xem trước các ô hệ thống sẽ gieo, chưa thao tác thật
python3 -m plant_automation plant-empty --empty-reference captures/empty-reference.png --seed-tool X Y

# Chạy kịch bản mẫu; Ctrl+C để dừng an toàn
python3 -m plant_automation run --scenario scenarios/planting.example.json
```

Giao diện desktop dùng PySide6/Qt và bao gồm trạng thái thiết bị, ảnh xem trước không lưu vào ổ đĩa, lưới 16 ô đất, chọn cây trồng, thời gian quét/chờ popup, log trực tiếp, nút **Mở Mirror** và nút Bắt đầu/Dừng an toàn. Tùy chọn **Tự mở Mirror khi bắt đầu** chỉ mở scrcpy khi bạn chạy vòng lặp.

Khi có nhiều điện thoại, thêm `--serial SERIAL`, ví dụ:

```bash
python3 -m plant_automation --serial R58N123ABC mirror
```

## Kịch bản

Mỗi kịch bản JSON giới hạn tối đa 100 thao tác và chỉ hỗ trợ các hành động minh bạch sau:

- `tap`: chạm tại `x`, `y`.
- `swipe`: vuốt từ `x1`, `y1` đến `x2`, `y2`, có `duration_ms`.
- `wait`: chờ `seconds`.
- `screenshot`: lưu ảnh minh chứng.

Hãy dùng `screenshot` và scrcpy để lấy tọa độ đúng cho giao diện ứng dụng của bạn. Không lưu mật khẩu hay dữ liệu nhạy cảm trong kịch bản.

## Quét ruộng và tưới có điều kiện

Trên Samsung S911B ở landscape `2340×1080`, công cụ nhận diện 16 ô bằng cách so sánh màn hình với ảnh mốc đất trống:

- `inspect-farm` đếm ô trống và ô đã có cây. Khi hạt đang chọn là dưa leo, số ô có cây chính là số dưa leo.
- `plant-empty` chỉ chạm các ô trống. Mặc định là chế độ xem trước; phải thêm `--confirm` mới thao tác thật.
- `plant-cucumber-verified` là chế độ trồng an toàn: nó dừng ngay khi game không xác nhận thêm cây sau từng vòng chọn hạt.
- `water-if-notified` chỉ tưới khi khớp ảnh mẫu `--notification-template`; có popup hoặc không có thông báo thì dừng, không chạm.
- `harvest-if-notified` hoạt động tương tự cho thu hoạch.
- `bulk-if-notified` là lựa chọn nên dùng: khi mẫu thông báo tưới hoặc thu hoạch xuất hiện, nó chỉ bấm nút hành động hàng loạt ở góc trái một lần.

```bash
python3 -m plant_automation inspect-farm --empty-reference captures/empty-reference.png
python3 -m plant_automation plant-empty --empty-reference captures/empty-reference.png --seed-tool X Y --confirm
python3 -m plant_automation plant-selected-empty --empty-reference captures/empty-reference.png --confirm
python3 -m plant_automation plant-cucumber-verified --empty-reference captures/empty-reference.png --confirm
python3 -m plant_automation bulk-if-notified --notification-template captures/water-notice.png --confirm

# Vòng lặp: tưới/thu hoạch hàng loạt khi có thông báo; gieo dưa leo khi có ô trống
python3 -m plant_automation --serial RFCX50B8ZMW farm-loop \
  --empty-reference captures/empty-reference.png --confirm --interval 3 --popup-wait 5 --mirror
```

Khi cần gieo, vòng lặp chạm **một** ô trống để mở thanh hạt, sau đó bấm hạt dưa leo liên tiếp cho toàn bộ các ô còn trống và thêm hai nhịp bù lỗi tải của game. Không cần thêm `--seed-menu-open`: chương trình tự nhận biết thanh hạt đang mở.
Thêm `--mirror` để mở scrcpy trước khi chạy vòng lặp; bỏ tùy chọn này nếu cửa sổ scrcpy đã mở.
Khi popup che ruộng, vòng lặp không thao tác và chờ `--popup-wait` giây (mặc định 5) trước khi quét lại.
Các ảnh dùng để quét thường xuyên được tạo trong thư mục tạm và xóa ngay sau khi nhận diện. Chỉ các lệnh chủ động như `screenshot`, `capture-empty-reference` và kịch bản có hành động `screenshot` mới lưu ảnh lâu dài trong `captures/`.

## Chọn loại cây trồng

Loại cây để tự động gieo được khai báo ở [`config/crops.json`](config/crops.json). Trong giao diện, chọn cây ở mục **Cây trồng tự động** trước khi bấm bắt đầu. Danh mục đã hiệu chuẩn có **Dưa leo** và **Hướng dương**. Nhận diện ruộng vẫn dùng ảnh mốc đất trống, vì vậy bất kỳ cây nào trong danh mục đều được xác định là “ô có cây”. Thêm cây mới bằng một mục có `id`, `name`, `seed_position`, `extra_taps` và `tap_delay_s` sau khi đã xác định đúng tọa độ hạt trên điện thoại.

Với dòng lệnh, chọn theo `id`:

```bash
python3 -m plant_automation --serial RFCX50B8ZMW farm-loop \
  --empty-reference captures/empty-reference.png --crop sunflower --confirm --mirror
```

## Hạt và thiết bị khác nhau

Phần mềm không còn giả định mọi máy đều có cùng tọa độ. Hồ sơ thiết bị tại [`config/device-profiles/default-farm.json`](config/device-profiles/default-farm.json) chứa độ phân giải gốc, 16 ô đất, nút hành động hàng loạt và vùng thanh hạt. Khi độ phân giải thay đổi nhưng cùng tỷ lệ màn hình, phần mềm tự co giãn mọi tọa độ theo ảnh chụp thực tế. Nếu tỷ lệ màn hình khác quá nhiều, chương trình dừng an toàn và yêu cầu một hồ sơ hiệu chuẩn mới.

Khi thanh hạt mở, chương trình tìm mẫu ảnh của gói hạt **trong vùng thanh hạt**, thay vì mặc định bấm một điểm cố định. `seed_position` trong cấu hình cây chỉ là phương án dự phòng đã được co giãn theo thiết bị. Tạo mẫu cho cây mới khi thanh hạt đang mở:

```bash
python3 -m plant_automation --serial RFCX50B8ZMW \
  --device-profile config/device-profiles/default-farm.json \
  capture-seed-template --crop sunflower --rect X Y WIDTH HEIGHT
```

Lệnh lưu ảnh mẫu vào đường dẫn `seed_template` của cây trong [`config/crops.json`](config/crops.json). Với một thiết bị/giao diện mới, hãy sao chép `default-farm.json`, hiệu chỉnh 16 ô đất và các nút theo màn hình mới, sau đó chạy với `--device-profile`.

Tự chụp và cắt sát nút/thông báo tưới khi nó xuất hiện thành `captures/water-notice.png`. Hãy xác minh tọa độ công cụ hạt và tưới qua scrcpy trước lần chạy có `--confirm`.

## Giới hạn MVP

Nhận diện hiện dựa vào bố cục màn hình cố định và ảnh mốc, nên phải tạo lại ảnh mốc nếu đổi điện thoại, thay đổi độ phân giải hoặc zoom. Nó không bấm khi có popup che giao diện.

Chỉ tự động hóa ứng dụng và thiết bị mà bạn có quyền sử dụng; kiểm tra điều khoản của ứng dụng trước khi chạy tự động hóa.
