"""Crop profiles used by the automatic planting workflow."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class CropConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class CropProfile:
    id: str
    name: str
    seed_position: tuple[int, int]
    seed_template: Path | None = None
    template_min_score: float = 0.88
    extra_taps: int = 2
    tap_delay_s: float = 0.25


def load_crops(path: Path) -> tuple[CropProfile, ...]:
    """Load validated crop profiles from a portable JSON configuration file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CropConfigError(f"Không đọc được cấu hình cây trồng: {path}") from error
    except json.JSONDecodeError as error:
        raise CropConfigError(f"Cấu hình cây trồng không phải JSON hợp lệ: {path}") from error
    entries = payload.get("crops") if isinstance(payload, dict) else None
    if not isinstance(entries, list) or not entries:
        raise CropConfigError("Cấu hình cần có danh sách 'crops' không rỗng.")
    crops: list[CropProfile] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CropConfigError("Mỗi cây trồng phải là một đối tượng JSON.")
        crop_id, name, position = entry.get("id"), entry.get("name"), entry.get("seed_position")
        if not isinstance(crop_id, str) or not crop_id.strip() or crop_id in seen:
            raise CropConfigError("Mỗi cây cần id riêng, không rỗng.")
        if not isinstance(name, str) or not name.strip():
            raise CropConfigError(f"Cây '{crop_id}' cần tên hiển thị.")
        if not isinstance(position, list) or len(position) != 2 or not all(isinstance(value, int) and value >= 0 for value in position):
            raise CropConfigError(f"Cây '{crop_id}' cần seed_position dạng [x, y].")
        template = entry.get("seed_template")
        min_score = entry.get("template_min_score", 0.88)
        extra_taps = entry.get("extra_taps", 2)
        tap_delay_s = entry.get("tap_delay_s", 0.25)
        if not isinstance(extra_taps, int) or not 0 <= extra_taps <= 10:
            raise CropConfigError(f"Cây '{crop_id}' có extra_taps không hợp lệ.")
        if not isinstance(tap_delay_s, (int, float)) or not 0.05 <= float(tap_delay_s) <= 2:
            raise CropConfigError(f"Cây '{crop_id}' có tap_delay_s không hợp lệ.")
        if template is not None and (not isinstance(template, str) or not template):
            raise CropConfigError(f"Cây '{crop_id}' có seed_template không hợp lệ.")
        if not isinstance(min_score, (int, float)) or not 0.5 <= float(min_score) <= 1:
            raise CropConfigError(f"Cây '{crop_id}' có template_min_score không hợp lệ.")
        crops.append(CropProfile(crop_id, name, (position[0], position[1]), Path(template) if template else None, float(min_score), extra_taps, float(tap_delay_s)))
        seen.add(crop_id)
    return tuple(crops)


def select_crop(path: Path, crop_id: str) -> CropProfile:
    for crop in load_crops(path):
        if crop.id == crop_id:
            return crop
    raise CropConfigError(f"Không tìm thấy cây trồng '{crop_id}' trong {path}.")
