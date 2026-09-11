"""Read-only farm monitoring service shared by command and desktop UI layers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .adb import AndroidBridge
from .device_profile import DEFAULT_DEVICE_PROFILE, DeviceProfile
from .farm import FarmStatus, inspect


@dataclass(frozen=True)
class FarmSnapshot:
    image_png: bytes
    status: FarmStatus


def capture_farm_snapshot(bridge: AndroidBridge, empty_reference: Path, profile: DeviceProfile = DEFAULT_DEVICE_PROFILE) -> FarmSnapshot:
    """Capture and analyse one frame without storing it in the project."""
    with NamedTemporaryFile(prefix="plant-automation-preview-", suffix=".png", delete=False) as temporary:
        screenshot = Path(temporary.name)
    try:
        bridge.screenshot(screenshot)
        return FarmSnapshot(image_png=screenshot.read_bytes(), status=inspect(screenshot, empty_reference, profile=profile))
    finally:
        screenshot.unlink(missing_ok=True)
