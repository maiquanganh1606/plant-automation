from pathlib import Path
import unittest
from unittest.mock import patch

from plant_automation.farm import FarmStatus
from plant_automation.monitor import capture_farm_snapshot


class FakeBridge:
    def __init__(self) -> None:
        self.destination: Path | None = None

    def screenshot(self, destination: Path) -> None:
        self.destination = destination
        destination.write_bytes(b"preview")


class MonitorTests(unittest.TestCase):
    def test_snapshot_is_removed_after_reading(self) -> None:
        bridge = FakeBridge()
        with patch("plant_automation.monitor.inspect", return_value=FarmStatus((2,), (1,), False)):
            snapshot = capture_farm_snapshot(bridge, Path("reference.png"))
        self.assertEqual(snapshot.image_png, b"preview")
        self.assertEqual(snapshot.status.empty, (2,))
        self.assertIsNotNone(bridge.destination)
        self.assertFalse(bridge.destination.exists())  # type: ignore[union-attr]
