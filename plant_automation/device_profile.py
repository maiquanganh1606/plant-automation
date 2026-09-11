"""Portable geometry profiles for different Android screen sizes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class DeviceProfileError(RuntimeError):
    pass


DEFAULT_PLOTS: tuple[tuple[int, int], ...] = (
    (1175, 195),
    (960, 290), (1390, 290),
    (745, 390), (1175, 390), (1600, 390),
    (530, 485), (960, 485), (1390, 485), (1820, 485),
    (745, 580), (1175, 580), (1600, 580),
    (960, 675), (1390, 675),
    (1175, 770),
)


@dataclass(frozen=True)
class FrameGeometry:
    width: int
    height: int
    plot_centers: tuple[tuple[int, int], ...]
    plot_half_size: tuple[int, int]
    bulk_action_button: tuple[int, int]
    seed_menu_region: tuple[int, int, int, int]
    scale: tuple[float, float]

    def scale_point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (round(point[0] * self.scale[0]), round(point[1] * self.scale[1]))


@dataclass(frozen=True)
class DeviceProfile:
    id: str
    base_resolution: tuple[int, int]
    plot_centers: tuple[tuple[int, int], ...]
    plot_half_size: tuple[int, int]
    bulk_action_button: tuple[int, int]
    seed_menu_region: tuple[float, float, float, float]
    aspect_ratio_tolerance: float = 0.06

    def for_frame(self, width: int, height: int) -> FrameGeometry:
        if width <= 0 or height <= 0:
            raise DeviceProfileError("Kích thước màn hình không hợp lệ.")
        base_width, base_height = self.base_resolution
        ratio_delta = abs((width / height) / (base_width / base_height) - 1)
        if ratio_delta > self.aspect_ratio_tolerance:
            raise DeviceProfileError(
                f"Tỷ lệ màn hình {width}×{height} khác hồ sơ '{self.id}' quá nhiều; hãy hiệu chuẩn thiết bị."
            )
        sx, sy = width / base_width, height / base_height
        left, top, region_width, region_height = self.seed_menu_region
        return FrameGeometry(
            width=width,
            height=height,
            plot_centers=tuple((round(x * sx), round(y * sy)) for x, y in self.plot_centers),
            plot_half_size=(max(1, round(self.plot_half_size[0] * sx)), max(1, round(self.plot_half_size[1] * sy))),
            bulk_action_button=(round(self.bulk_action_button[0] * sx), round(self.bulk_action_button[1] * sy)),
            seed_menu_region=(round(left * width), round(top * height), round(region_width * width), round(region_height * height)),
            scale=(sx, sy),
        )


DEFAULT_DEVICE_PROFILE = DeviceProfile(
    id="samsung-s911b-landscape",
    base_resolution=(2340, 1080),
    plot_centers=DEFAULT_PLOTS,
    plot_half_size=(70, 55),
    bulk_action_button=(365, 300),
    seed_menu_region=(0.0, 0.66, 1.0, 0.34),
)


def load_device_profile(path: Path) -> DeviceProfile:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise DeviceProfileError(f"Không đọc được hồ sơ thiết bị: {path}") from error
    except json.JSONDecodeError as error:
        raise DeviceProfileError(f"Hồ sơ thiết bị không phải JSON hợp lệ: {path}") from error
    if not isinstance(payload, dict):
        raise DeviceProfileError("Hồ sơ thiết bị phải là đối tượng JSON.")
    try:
        profile_id = payload["id"]
        resolution = payload["base_resolution"]
        plots = payload["plot_centers"]
        half_size = payload["plot_half_size"]
        bulk = payload["bulk_action_button"]
        region = payload["seed_menu_region"]
    except KeyError as error:
        raise DeviceProfileError(f"Thiếu trường hồ sơ thiết bị: {error.args[0]}") from error
    pairs = (resolution, half_size, bulk)
    if not isinstance(profile_id, str) or not profile_id or any(not isinstance(value, list) or len(value) != 2 or not all(isinstance(x, int) and x > 0 for x in value) for value in pairs):
        raise DeviceProfileError("Hồ sơ thiết bị chứa kích thước hoặc tọa độ không hợp lệ.")
    if not isinstance(plots, list) or len(plots) != 16 or any(not isinstance(point, list) or len(point) != 2 or not all(isinstance(x, int) and x > 0 for x in point) for point in plots):
        raise DeviceProfileError("Hồ sơ cần đúng 16 tọa độ ô đất.")
    if not isinstance(region, list) or len(region) != 4 or not all(isinstance(value, (int, float)) and 0 <= value <= 1 for value in region):
        raise DeviceProfileError("seed_menu_region phải là [left, top, width, height] theo tỷ lệ 0–1.")
    if region[2] <= 0 or region[3] <= 0:
        raise DeviceProfileError("seed_menu_region phải có chiều rộng và chiều cao dương.")
    tolerance = payload.get("aspect_ratio_tolerance", 0.06)
    if not isinstance(tolerance, (int, float)) or not 0 < float(tolerance) <= 0.3:
        raise DeviceProfileError("aspect_ratio_tolerance không hợp lệ.")
    return DeviceProfile(profile_id, tuple(resolution), tuple(tuple(point) for point in plots), tuple(half_size), tuple(bulk), tuple(float(value) for value in region), float(tolerance))
