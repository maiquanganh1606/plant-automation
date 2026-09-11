from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from plant_automation.farm import PLOT_CENTERS, inspect


class FarmVisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="plant-farm-test-")
        self.addCleanup(self.tempdir.cleanup)
        directory = Path(self.tempdir.name)
        self.reference_path = directory / "farm-reference.png"
        self.current_path = directory / "farm-current.png"
        self.reference = np.full((1080, 2340, 3), 160, dtype=np.uint8)
        cv2.imwrite(str(self.reference_path), self.reference)

    def tearDown(self) -> None:
        self.reference_path.unlink(missing_ok=True)
        self.current_path.unlink(missing_ok=True)

    def test_identifies_changed_plot_as_occupied(self) -> None:
        current = self.reference.copy()
        x, y = PLOT_CENTERS[0]
        current[y - 20:y + 20, x - 40:x + 40] = (10, 80, 10)
        cv2.imwrite(str(self.current_path), current)
        status = inspect(self.current_path, self.reference_path)
        self.assertEqual(status.occupied, (1,))
        self.assertEqual(len(status.empty), 15)

    def test_stops_when_modal_veil_is_detected(self) -> None:
        cv2.imwrite(str(self.current_path), np.full((1080, 2340, 3), 40, dtype=np.uint8))
        self.assertTrue(inspect(self.current_path, self.reference_path).popup_detected)
