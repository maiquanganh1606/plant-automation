from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
import time

import cv2

from .adb import AdbError, AndroidBridge
from .crops import CropConfigError, select_crop
from .device_profile import DeviceProfileError, load_device_profile
from .farm import PLOT_CENTERS, FarmControls, FarmVisionError, bulk_action, frame_geometry, inspect, notification_score, notification_visible, plant_empty, plant_verified, plant_with_selected_seed, seed_bar_visible, water_occupied
from .runner import run_actions
from .scenario import ScenarioError, load_scenario
from .seed_finder import fallback_seed, find_seed


def scan_screenshot(bridge: AndroidBridge, *, label: str) -> Path:
    """Capture a disposable scan outside the workspace.

    Routine detection must not grow ``captures/`` indefinitely.  The file is
    removed as soon as its pixels are no longer needed; it is only a short-lived
    bridge because OpenCV's current recognition API accepts file paths.
    """
    with NamedTemporaryFile(prefix=f"plant-automation-{label}-", suffix=".png", delete=False) as temporary:
        path = Path(temporary.name)
    bridge.screenshot(path)
    return path


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="MVP tự động hóa Android cá nhân qua ADB.")
    command.add_argument("--serial", help="ADB serial của điện thoại cần điều khiển")
    command.add_argument("--device-profile", type=Path, default=Path("config/device-profiles/default-farm.json"), help="Hồ sơ hình học thiết bị JSON")
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("devices", help="Liệt kê thiết bị ADB")
    subcommands.add_parser("gui", help="Mở giao diện desktop điều khiển tự động hóa")
    subcommands.add_parser("mirror", help="Mở scrcpy cho điện thoại")
    subcommands.add_parser("screenshot", help="Chụp ảnh màn hình")
    baseline = subcommands.add_parser("capture-empty-reference", help="Lưu ảnh mốc khi toàn bộ ô đất trống")
    baseline.add_argument("--output", type=Path, default=Path("captures/empty-reference.png"))
    inspect_farm = subcommands.add_parser("inspect-farm", help="Đếm ô trống và ô có cây so với ảnh mốc")
    inspect_farm.add_argument("--empty-reference", type=Path, required=True)
    plant = subcommands.add_parser("plant-empty", help="Gieo tại các ô trống đã phát hiện")
    plant.add_argument("--empty-reference", type=Path, required=True)
    plant.add_argument("--seed-tool", nargs=2, type=int, metavar=("X", "Y"), required=True)
    plant.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật; mặc định là xem trước")
    selected_plant = subcommands.add_parser("plant-selected-empty", help="Gieo tại ô trống khi hạt đã được chọn trong game")
    selected_plant.add_argument("--empty-reference", type=Path, required=True)
    selected_plant.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật; mặc định là xem trước")
    verified = subcommands.add_parser("plant-cucumber-verified", help="Chọn dưa leo và kiểm chứng sau từng cây")
    verified.add_argument("--empty-reference", type=Path, required=True)
    verified.add_argument("--seed-menu", nargs=2, type=int, default=(1760, 960))
    verified.add_argument("--cucumber-seed", nargs=2, type=int, default=(794, 949))
    verified.add_argument("--captures", type=Path, default=Path("captures/verified-plant"))
    verified.add_argument("--confirm", action="store_true")
    water = subcommands.add_parser("water-if-notified", help="Tưới khi mẫu nút thông báo xuất hiện")
    water.add_argument("--empty-reference", type=Path, required=True)
    water.add_argument("--notification-template", type=Path, required=True)
    water.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật; mặc định là xem trước")
    harvest = subcommands.add_parser("harvest-if-notified", help="Thu hoạch khi mẫu nút thông báo xuất hiện")
    harvest.add_argument("--empty-reference", type=Path, required=True)
    harvest.add_argument("--notification-template", type=Path, required=True)
    harvest.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật; mặc định là xem trước")
    bulk = subcommands.add_parser("bulk-if-notified", help="Bấm nút hàng loạt ở góc trái khi có thông báo")
    bulk.add_argument("--notification-template", type=Path, required=True)
    bulk.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật; mặc định là xem trước")
    loop = subcommands.add_parser("farm-loop", help="Lặp trồng, tưới và thu hoạch theo trạng thái màn hình")
    loop.add_argument("--empty-reference", type=Path, required=True)
    loop.add_argument("--water-template", type=Path, default=Path("captures/water-notice.png"))
    loop.add_argument("--harvest-template", type=Path, default=Path("captures/harvest-notice.png"))
    loop.add_argument("--crop-config", type=Path, default=Path("config/crops.json"), help="Danh mục cây trồng JSON")
    loop.add_argument("--crop", default="cucumber", help="ID loại cây cần trồng")
    loop.add_argument("--seed-position", "--cucumber-seed", dest="seed_position", nargs=2, type=int, help="Ghi đè tọa độ hạt cho lần chạy này")
    loop.add_argument("--interval", type=float, default=3.0, help="Giây chờ giữa các vòng")
    loop.add_argument("--popup-wait", type=float, default=5.0, help="Giây chờ trước khi quét lại khi có popup")
    loop.add_argument("--cycles", type=int, default=0, help="Số vòng; 0 chạy đến khi Ctrl+C")
    loop.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật")
    loop.add_argument("--mirror", action="store_true", help="Mở scrcpy cùng lúc trước khi bắt đầu vòng lặp")
    loop.add_argument("--seed-menu-open", action="store_true", help="Tương thích lệnh cũ; chương trình tự kiểm tra menu hạt trên màn hình")
    batch = subcommands.add_parser("plant-menu-batch", help="Bấm hạt liên tiếp cho toàn bộ ô trống")
    batch.add_argument("--empty-reference", type=Path, required=True)
    batch.add_argument("--crop-config", type=Path, default=Path("config/crops.json"), help="Danh mục cây trồng JSON")
    batch.add_argument("--crop", default="cucumber", help="ID loại cây cần trồng")
    batch.add_argument("--seed-position", "--cucumber-seed", dest="seed_position", nargs=2, type=int, help="Ghi đè tọa độ hạt cho lần chạy này")
    batch.add_argument("--confirm", action="store_true", help="Cho phép thao tác thật")
    template = subcommands.add_parser("capture-seed-template", help="Lưu mẫu ảnh gói hạt khi thanh hạt đang mở")
    template.add_argument("--crop-config", type=Path, default=Path("config/crops.json"))
    template.add_argument("--crop", required=True, help="ID loại cây cần tạo mẫu")
    template.add_argument("--rect", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"), required=True, help="Vùng gói hạt trên độ phân giải gốc của hồ sơ")
    run = subcommands.add_parser("run", help="Chạy kịch bản JSON")
    run.add_argument("--scenario", type=Path, required=True, help="Đường dẫn tệp JSON")
    run.add_argument("--captures", type=Path, default=Path("captures"), help="Thư mục lưu ảnh")
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "devices":
            devices = AndroidBridge.devices()
            if not devices:
                print("Không tìm thấy thiết bị.")
            for device in devices:
                print(f"{device.serial}\t{device.state}\t{device.model or '-'}")
            return 0
        if args.command == "gui":
            from .qt_gui import launch

            return launch(args.serial, args.device_profile)

        bridge = AndroidBridge(args.serial)
        profile = load_device_profile(args.device_profile)
        if args.command == "mirror":
            bridge.mirror()
            print(f"Đã mở scrcpy cho {bridge.resolve_serial()}.")
        elif args.command == "screenshot":
            destination = Path("captures") / f"screen-{datetime.now():%Y%m%d-%H%M%S}.png"
            bridge.screenshot(destination)
            print(f"Đã lưu {destination}")
        elif args.command == "capture-empty-reference":
            bridge.screenshot(args.output)
            print(f"Đã lưu ảnh mốc đất trống: {args.output}")
        elif args.command == "bulk-if-notified":
            current = scan_screenshot(bridge, label="check")
            geometry = frame_geometry(current, profile)
            if not notification_visible(current, args.notification_template, profile=profile):
                current.unlink(missing_ok=True)
                print("Không thấy thông báo hành động; không thao tác.")
                return 0
            current.unlink(missing_ok=True)
            bulk_action(bridge, confirm=args.confirm, position=geometry.bulk_action_button)
            print("Đã bấm nút hàng loạt." if args.confirm else "Sẽ bấm nút hàng loạt (xem trước).")
        elif args.command == "plant-menu-batch":
            crop = select_crop(args.crop_config, args.crop)
            current = scan_screenshot(bridge, label="batch")
            geometry = frame_geometry(current, profile)
            status = inspect(current, args.empty_reference, profile=profile)
            current.unlink(missing_ok=True)
            if status.popup_detected:
                raise FarmVisionError("Popup che giao diện; dừng.")
            count = len(status.empty)
            if count == 0:
                print("Không có ô trống; không mở menu hạt.")
                return 0
            if args.confirm:
                # The first empty plot must be selected before the owned-seed menu appears.
                bridge.tap(*geometry.plot_centers[status.empty[0] - 1])
                time.sleep(0.7)
                menu = scan_screenshot(bridge, label="seed-menu")
                menu_geometry = frame_geometry(menu, profile)
                if args.seed_position:
                    seed = menu_geometry.scale_point(tuple(args.seed_position))
                    source = "tọa độ ghi đè"
                else:
                    match = find_seed(menu, crop, menu_geometry)
                    resolved = match or fallback_seed(crop, menu_geometry)
                    seed, source = resolved.position, f"{resolved.source} ({resolved.score:.2f})"
                menu.unlink(missing_ok=True)
                bridge.tap_many((seed for _ in range(count + crop.extra_taps)), delay_s=crop.tap_delay_s)
            print(f"{'Đã trồng' if args.confirm else 'Sẽ trồng'} {crop.name} liên tiếp {count} ô trống (+{crop.extra_taps} nhịp bù lỗi tải; hạt: {source if args.confirm else 'xem trước'}).")
        elif args.command == "capture-seed-template":
            crop = select_crop(args.crop_config, args.crop)
            if crop.seed_template is None:
                raise CropConfigError(f"Cây '{crop.name}' chưa khai báo seed_template trong cấu hình.")
            x, y, width, height = args.rect
            if width <= 0 or height <= 0:
                raise FarmVisionError("WIDTH và HEIGHT của rect phải dương.")
            current = scan_screenshot(bridge, label="seed-template")
            geometry = frame_geometry(current, profile)
            x, y = geometry.scale_point((x, y))
            width, height = round(width * geometry.scale[0]), round(height * geometry.scale[1])
            image = cv2.imread(str(current))
            current.unlink(missing_ok=True)
            assert image is not None
            crop_image = image[y:y + height, x:x + width]
            if crop_image.shape[:2] != (height, width):
                raise FarmVisionError("Vùng mẫu hạt nằm ngoài màn hình.")
            crop.seed_template.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(crop.seed_template), crop_image):
                raise FarmVisionError("Không lưu được mẫu hạt.")
            print(f"Đã lưu mẫu nhận diện {crop.name}: {crop.seed_template}")
        elif args.command == "farm-loop":
            crop = select_crop(args.crop_config, args.crop)
            if args.interval < 1:
                raise FarmVisionError("interval phải từ 1 giây trở lên.")
            if args.popup_wait < 1:
                raise FarmVisionError("popup-wait phải từ 1 giây trở lên.")
            if args.mirror:
                bridge.mirror()
                print(f"Đã mở scrcpy cho {bridge.resolve_serial()}.")
            print("Bắt đầu vòng lặp; Ctrl+C để dừng.")
            cycle = 0
            last_bulk_cycle = -999
            while args.cycles == 0 or cycle < args.cycles:
                cycle += 1
                current = scan_screenshot(bridge, label="loop")
                geometry = frame_geometry(current, profile)
                status = inspect(current, args.empty_reference, profile=profile)
                if status.popup_detected:
                    print(f"[{cycle}] popup che giao diện; chờ {args.popup_wait:g} giây rồi quét lại.")
                    current.unlink(missing_ok=True)
                    if args.cycles == 0 or cycle < args.cycles:
                        time.sleep(args.popup_wait)
                    continue
                water_score = notification_score(current, args.water_template, profile)
                harvest_score = notification_score(current, args.harvest_template, profile)
                # Require a clear winner to avoid treating a similar icon as the wrong action.
                if cycle - last_bulk_cycle < 2:
                    water_score = harvest_score = 0.0
                if water_score >= 0.94 and water_score >= harvest_score + 0.05:
                    bulk_action(bridge, confirm=args.confirm, position=geometry.bulk_action_button)
                    last_bulk_cycle = cycle
                    print(f"[{cycle}] tưới hàng loạt (score={water_score:.2f})")
                elif harvest_score >= 0.94 and harvest_score >= water_score + 0.05:
                    bulk_action(bridge, confirm=args.confirm, position=geometry.bulk_action_button)
                    last_bulk_cycle = cycle
                    print(f"[{cycle}] thu hoạch hàng loạt (score={harvest_score:.2f})")
                else:
                    if status.empty:
                        if args.confirm:
                            # A tile tap is needed exactly once to open the owned-seed strip.
                            # Do not trust --seed-menu-open blindly: if the game has closed the
                            # strip, a seed tap would be lost instead of planting the first tile.
                            menu_open = seed_bar_visible(current, profile=profile)
                            if not menu_open:
                                target = geometry.plot_centers[status.empty[0] - 1]
                                bridge.tap(*target)
                                time.sleep(0.7)
                            menu = scan_screenshot(bridge, label="seed-menu")
                            menu_geometry = frame_geometry(menu, profile)
                            if args.seed_position:
                                seed = menu_geometry.scale_point(tuple(args.seed_position))
                                source = "tọa độ ghi đè"
                            else:
                                match = find_seed(menu, crop, menu_geometry)
                                resolved = match or fallback_seed(crop, menu_geometry)
                                seed, source = resolved.position, f"{resolved.source} ({resolved.score:.2f})"
                            menu.unlink(missing_ok=True)
                            # Once open, every cucumber tap advances to the next empty tile.
                            # Extra taps are intentional: the game can drop an input while loading,
                            # and it ignores them safely after all empty tiles are filled.
                            bridge.tap_many(
                                (seed for _ in range(len(status.empty) + crop.extra_taps)),
                                delay_s=crop.tap_delay_s,
                            )
                            action = "dùng menu đang mở" if menu_open else "mở menu một lần"
                            print(f"[{cycle}] {action}, trồng {crop.name} bằng {len(status.empty) + crop.extra_taps} nhịp hạt; hạt: {source}")
                        else:
                            print(f"[{cycle}] sẽ trồng {crop.name} tại ô {status.empty[0]} (xem trước)")
                    else:
                        print(f"[{cycle}] không có hành động; cây={len(status.occupied)}, trống={len(status.empty)} (water={water_score:.2f}, harvest={harvest_score:.2f})")
                current.unlink(missing_ok=True)
                if args.cycles == 0 or cycle < args.cycles:
                    time.sleep(args.interval)
        elif args.command in {"inspect-farm", "plant-empty", "plant-selected-empty", "plant-cucumber-verified", "water-if-notified", "harvest-if-notified"}:
            current = scan_screenshot(bridge, label="check")
            geometry = frame_geometry(current, profile)
            status = inspect(current, args.empty_reference, profile=profile)
            if status.popup_detected:
                current.unlink(missing_ok=True)
                print("Dừng: phát hiện popup che giao diện.")
                return 3
            print(f"Ô trống: {len(status.empty)} {list(status.empty)}")
            print(f"Ô có cây: {len(status.occupied)} {list(status.occupied)}")
            if args.command == "plant-empty":
                current.unlink(missing_ok=True)
                plots = plant_empty(bridge, status, tuple(args.seed_tool), confirm=args.confirm, geometry=geometry)
                print(f"{'Đã gieo' if args.confirm else 'Sẽ gieo (xem trước)'}: {list(plots)}")
            elif args.command == "plant-selected-empty":
                current.unlink(missing_ok=True)
                plots = plant_with_selected_seed(bridge, status, confirm=args.confirm, geometry=geometry)
                print(f"{'Đã gieo' if args.confirm else 'Sẽ gieo (xem trước)'}: {list(plots)}")
            elif args.command == "plant-cucumber-verified":
                current.unlink(missing_ok=True)
                count = plant_verified(bridge, FarmControls(tuple(args.seed_menu), tuple(args.cucumber_seed)), args.empty_reference, args.captures, confirm=args.confirm, profile=profile)
                print(f"{'Đã trồng' if args.confirm else 'Sẽ trồng (xem trước)'}: {count} cây")
            elif args.command == "water-if-notified":
                if not notification_visible(current, args.notification_template, profile=profile):
                    current.unlink(missing_ok=True)
                    print("Không thấy nút thông báo tưới; không thao tác.")
                    return 0
                current.unlink(missing_ok=True)
                bulk_action(bridge, confirm=args.confirm, position=geometry.bulk_action_button)
                print("Đã tưới hàng loạt." if args.confirm else "Sẽ tưới hàng loạt (xem trước).")
            elif args.command == "harvest-if-notified":
                if not notification_visible(current, args.notification_template, profile=profile):
                    current.unlink(missing_ok=True)
                    print("Không thấy nút thông báo thu hoạch; không thao tác.")
                    return 0
                current.unlink(missing_ok=True)
                bulk_action(bridge, confirm=args.confirm, position=geometry.bulk_action_button)
                print("Đã thu hoạch hàng loạt." if args.confirm else "Sẽ thu hoạch hàng loạt (xem trước).")
            else:
                current.unlink(missing_ok=True)
        elif args.command == "run":
            actions = load_scenario(args.scenario)
            print(f"Chạy {len(actions)} thao tác trên {bridge.resolve_serial()}. Nhấn Ctrl+C để dừng.")
            run_actions(bridge, actions, args.captures)
            print("Hoàn tất kịch bản.")
        return 0
    except (AdbError, CropConfigError, DeviceProfileError, ScenarioError, FarmVisionError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nĐã dừng theo yêu cầu người dùng.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
