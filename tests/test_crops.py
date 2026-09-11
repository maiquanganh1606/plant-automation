import json
from pathlib import Path
import tempfile
import unittest

from plant_automation.crops import CropConfigError, load_crops, select_crop


class CropConfigTests(unittest.TestCase):
    def write(self, payload: object) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        handle.write(json.dumps(payload))
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_loads_crop_profile(self) -> None:
        path = self.write({"crops": [{"id": "tomato", "name": "Cà chua", "seed_position": [900, 950]}]})
        crop = select_crop(path, "tomato")
        self.assertEqual(crop.name, "Cà chua")
        self.assertEqual(crop.seed_position, (900, 950))
        self.assertEqual(crop.extra_taps, 2)

    def test_rejects_duplicate_crop_ids(self) -> None:
        path = self.write({"crops": [
            {"id": "tomato", "name": "Cà chua", "seed_position": [900, 950]},
            {"id": "tomato", "name": "Cà chua đỏ", "seed_position": [920, 950]},
        ]})
        with self.assertRaises(CropConfigError):
            load_crops(path)

    def test_shipped_catalog_includes_cucumber_and_sunflower(self) -> None:
        catalog = Path("config/crops.json")
        crops = {crop.id: crop for crop in load_crops(catalog)}
        self.assertEqual(crops["cucumber"].seed_position, (794, 949))
        self.assertEqual(crops["sunflower"].name, "Hướng dương")
        self.assertEqual(crops["sunflower"].seed_position, (990, 949))
