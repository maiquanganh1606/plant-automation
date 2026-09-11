from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from plant_automation.crops import CropProfile
from plant_automation.device_profile import DEFAULT_DEVICE_PROFILE
from plant_automation.seed_finder import fallback_seed, find_seed


class SeedFinderTests(unittest.TestCase):
    def test_finds_seed_only_inside_seed_tray(self) -> None:
        image = np.zeros((1080, 2340, 3), dtype=np.uint8)
        template = np.zeros((30, 40, 3), dtype=np.uint8)
        template[:, :, 1] = 220
        cv2.circle(template, (12, 10), 5, (30, 40, 250), -1)
        cv2.rectangle(template, (25, 16), (36, 27), (250, 80, 20), -1)
        image[820:850, 900:940] = template
        image[180:210, 100:140] = template  # Deliberate false copy outside tray.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path, template_path = root / "screen.png", root / "sunflower.png"
            cv2.imwrite(str(image_path), image)
            cv2.imwrite(str(template_path), template)
            crop = CropProfile("sunflower", "Hướng dương", (990, 949), template_path, 0.8)
            match = find_seed(image_path, crop, DEFAULT_DEVICE_PROFILE.for_frame(2340, 1080))
        self.assertIsNotNone(match)
        self.assertEqual(match.position, (920, 835))  # type: ignore[union-attr]
        self.assertEqual(match.source, "template")  # type: ignore[union-attr]

    def test_scales_fallback_position(self) -> None:
        crop = CropProfile("sunflower", "Hướng dương", (990, 949))
        match = fallback_seed(crop, DEFAULT_DEVICE_PROFILE.for_frame(1170, 540))
        self.assertEqual(match.position, (495, 474))
