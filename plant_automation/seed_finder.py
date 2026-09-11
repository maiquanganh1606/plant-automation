"""Find a selected crop's seed pack inside a movable seed tray."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .crops import CropProfile
from .device_profile import FrameGeometry


@dataclass(frozen=True)
class SeedMatch:
    position: tuple[int, int]
    score: float
    source: str


def _read(path: Path) -> np.ndarray | None:
    return cv2.imread(str(path))


def find_seed(image_path: Path, crop: CropProfile, geometry: FrameGeometry) -> SeedMatch | None:
    """Return the seed-pack centre if its template is confidently visible.

    The search is constrained to the normalized seed tray region; this prevents
    a similarly colored icon elsewhere in the game from being selected.
    """
    if crop.seed_template is None or not crop.seed_template.exists():
        return None
    image = _read(image_path)
    template = _read(crop.seed_template)
    if image is None or template is None:
        return None
    sx, sy = geometry.scale
    if (sx, sy) != (1.0, 1.0):
        template = cv2.resize(template, None, fx=sx, fy=sy, interpolation=cv2.INTER_LINEAR)
    left, top, width, height = geometry.seed_menu_region
    tray = image[top:top + height, left:left + width]
    if tray.size == 0 or template.shape[0] > tray.shape[0] or template.shape[1] > tray.shape[1]:
        return None
    score_map = cv2.matchTemplate(tray, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, top_left = cv2.minMaxLoc(score_map)
    if score < crop.template_min_score:
        return None
    return SeedMatch(
        position=(left + top_left[0] + template.shape[1] // 2, top + top_left[1] + template.shape[0] // 2),
        score=float(score),
        source="template",
    )


def fallback_seed(crop: CropProfile, geometry: FrameGeometry) -> SeedMatch:
    """Scale a calibrated fallback point only when visual matching is unavailable."""
    return SeedMatch(position=geometry.scale_point(crop.seed_position), score=0.0, source="fallback")
