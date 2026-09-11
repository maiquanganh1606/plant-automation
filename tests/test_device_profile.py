import json
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from plant_automation.device_profile import DEFAULT_DEVICE_PROFILE, DeviceProfileError, load_device_profile
from plant_automation.farm import inspect


class DeviceProfileTests(unittest.TestCase):
    def test_scales_geometry_to_same_aspect_device(self) -> None:
        geometry = DEFAULT_DEVICE_PROFILE.for_frame(1170, 540)
        self.assertEqual(geometry.plot_centers[0], (588, 98))
        self.assertEqual(geometry.bulk_action_button, (182, 150))
        self.assertEqual(geometry.plot_half_size, (35, 28))

    def test_rejects_incompatible_aspect_ratio(self) -> None:
        with self.assertRaises(DeviceProfileError):
            DEFAULT_DEVICE_PROFILE.for_frame(1080, 1080)

    def test_inspect_scales_reference_to_current_frame(self) -> None:
        reference = np.full((1080, 2340, 3), 160, dtype=np.uint8)
        current = cv2.resize(reference, (1170, 540), interpolation=cv2.INTER_LINEAR)
        x, y = DEFAULT_DEVICE_PROFILE.for_frame(1170, 540).plot_centers[2]
        current[y - 15:y + 15, x - 25:x + 25] = (10, 80, 10)
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.png"
            current_path = Path(directory) / "current.png"
            cv2.imwrite(str(reference_path), reference)
            cv2.imwrite(str(current_path), current)
            status = inspect(current_path, reference_path)
        self.assertEqual(status.occupied, (3,))

    def test_rejects_profile_without_sixteen_plots(self) -> None:
        payload = {
            "id": "bad", "base_resolution": [100, 100], "plot_centers": [[1, 1]],
            "plot_half_size": [1, 1], "bulk_action_button": [1, 1], "seed_menu_region": [0, 0, 1, 1],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(payload, file)
            path = Path(file.name)
        self.addCleanup(path.unlink, missing_ok=True)
        with self.assertRaises(DeviceProfileError):
            load_device_profile(path)
