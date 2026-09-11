from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

import cv2
import numpy as np

from .adb import AndroidBridge
from .device_profile import DEFAULT_DEVICE_PROFILE, DeviceProfile, FrameGeometry


# Backwards-compatible defaults. New flows use a DeviceProfile scaled to each frame.
PLOT_CENTERS = DEFAULT_DEVICE_PROFILE.plot_centers
PLOT_HALF_WIDTH, PLOT_HALF_HEIGHT = DEFAULT_DEVICE_PROFILE.plot_half_size
BULK_ACTION_BUTTON = DEFAULT_DEVICE_PROFILE.bulk_action_button


class FarmVisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FarmStatus:
    empty: tuple[int, ...]
    occupied: tuple[int, ...]
    popup_detected: bool


@dataclass(frozen=True)
class FarmControls:
    seed_menu: tuple[int, int]
    cucumber_seed: tuple[int, int]


def _read(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise FarmVisionError(f"Không đọc được ảnh: {path}")
    return image


def frame_geometry(current_path: Path, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> FrameGeometry:
    """Resolve a device profile to the actual dimensions of one screenshot."""
    image = _read(current_path)
    return profile.for_frame(image.shape[1], image.shape[0])


def _plot(image: np.ndarray, center: tuple[int, int], half_size: tuple[int, int]) -> np.ndarray:
    x, y = center
    half_width, half_height = half_size
    return image[y - half_height:y + half_height, x - half_width:x + half_width]


def popup_present(image: np.ndarray) -> bool:
    """Detect the dark full-screen veil used by modal dialogs in this game."""
    height, width = image.shape[:2]
    left = image[round(height * .02):round(height * .10), round(width * .01):round(width * .07)]
    right = image[round(height * .02):round(height * .10), round(width * .88):round(width * .98)]
    return float((left.mean() + right.mean()) / 2) < 95


def inspect(current_path: Path, empty_reference_path: Path, threshold: float = 10.0, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> FarmStatus:
    current = _read(current_path)
    reference = _read(empty_reference_path)
    height, width = current.shape[:2]
    geometry = profile.for_frame(width, height)
    if reference.shape[:2] != (height, width):
        reference = cv2.resize(reference, (width, height), interpolation=cv2.INTER_LINEAR)
    if popup_present(current):
        return FarmStatus(empty=(), occupied=(), popup_detected=True)
    empty: list[int] = []
    occupied: list[int] = []
    for index, center in enumerate(geometry.plot_centers, start=1):
        difference = cv2.absdiff(_plot(current, center, geometry.plot_half_size), _plot(reference, center, geometry.plot_half_size))
        if float(difference.mean()) >= threshold:
            occupied.append(index)
        else:
            empty.append(index)
    return FarmStatus(tuple(empty), tuple(occupied), popup_detected=False)


def _scaled_template(template: np.ndarray, scale: tuple[float, float]) -> np.ndarray:
    if scale == (1.0, 1.0):
        return template
    return cv2.resize(template, None, fx=scale[0], fy=scale[1], interpolation=cv2.INTER_LINEAR)


def notification_visible(current_path: Path, template_path: Path, minimum_score: float = 0.90, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> bool:
    image = _read(current_path)
    template = _scaled_template(_read(template_path), profile.for_frame(image.shape[1], image.shape[0]).scale)
    if popup_present(image):
        return False
    return float(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED).max()) >= minimum_score


def notification_score(current_path: Path, template_path: Path, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> float:
    image = _read(current_path)
    template = _scaled_template(_read(template_path), profile.for_frame(image.shape[1], image.shape[0]).scale)
    if popup_present(image):
        return 0.0
    return float(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED).max())


def seed_bar_visible(current_path: Path, template_path: Path = Path("captures/cucumber-seed-template.png"), minimum_score: float = 0.82, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> bool:
    """Whether the owned-seed strip is already open, avoiding a second plot tap."""
    if not template_path.exists():
        return False
    return notification_score(current_path, template_path, profile) >= minimum_score


def _plot_centers(geometry: FrameGeometry | None) -> tuple[tuple[int, int], ...]:
    return geometry.plot_centers if geometry else PLOT_CENTERS


def plant_empty(bridge: AndroidBridge, status: FarmStatus, seed_tool: tuple[int, int], *, confirm: bool, geometry: FrameGeometry | None = None) -> tuple[int, ...]:
    if status.popup_detected:
        raise FarmVisionError("Phát hiện popup; không thao tác.")
    if confirm:
        bridge.tap(*seed_tool)
        for index in status.empty:
            bridge.tap(*_plot_centers(geometry)[index - 1])
    return status.empty


def plant_with_selected_seed(bridge: AndroidBridge, status: FarmStatus, *, confirm: bool, geometry: FrameGeometry | None = None) -> tuple[int, ...]:
    """Plant only the detected empty plots when a seed is already selected in-game."""
    if status.popup_detected:
        raise FarmVisionError("Phát hiện popup; không thao tác.")
    if confirm:
        for index in status.empty:
            bridge.tap(*_plot_centers(geometry)[index - 1])
    return status.empty


def water_occupied(bridge: AndroidBridge, status: FarmStatus, water_tool: tuple[int, int], *, confirm: bool, geometry: FrameGeometry | None = None) -> tuple[int, ...]:
    if status.popup_detected:
        raise FarmVisionError("Phát hiện popup; không thao tác.")
    if confirm:
        bridge.tap(*water_tool)
        for index in status.occupied:
            bridge.tap(*_plot_centers(geometry)[index - 1])
    return status.occupied


def bulk_action(bridge: AndroidBridge, *, confirm: bool, position: tuple[int, int] = BULK_ACTION_BUTTON) -> None:
    """Run the game's own visible all-plots watering/harvesting action once."""
    if confirm:
        bridge.tap(*position)


def plant_verified(bridge: AndroidBridge, controls: FarmControls, reference: Path, captures: Path, *, confirm: bool, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> int:
    """Select cucumber once per cycle and verify that the game added a plant."""
    captures.mkdir(parents=True, exist_ok=True)
    planted = 0
    for step in range(1, len(PLOT_CENTERS) + 1):
        before_path = captures / f"before-{step}.png"
        bridge.screenshot(before_path)
        geometry = frame_geometry(before_path, profile)
        before = inspect(before_path, reference, profile=profile)
        if before.popup_detected:
            raise FarmVisionError("Popup che giao diện; dừng trồng.")
        if not before.empty:
            return planted
        if not confirm:
            return len(before.empty)
        # The game exposes the owned-seed bar only after the target empty tile is chosen.
        target = geometry.plot_centers[before.empty[0] - 1]
        bridge.tap(*target)
        time.sleep(1)
        bridge.tap(*geometry.scale_point(controls.cucumber_seed))
        time.sleep(1)
        after_path = captures / f"after-{step}.png"
        bridge.screenshot(after_path)
        after = inspect(after_path, reference, profile=profile)
        if after.popup_detected or len(after.occupied) <= len(before.occupied):
            raise FarmVisionError("Không xác nhận được cây mới; dừng để tránh thao tác sai.")
        planted += len(after.occupied) - len(before.occupied)
    return planted
