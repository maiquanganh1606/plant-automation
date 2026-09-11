import unittest
from unittest.mock import Mock

from plant_automation.adb import AdbError, AndroidBridge


class AndroidBridgeTests(unittest.TestCase):
    def test_tap_many_uses_one_shell_command_with_spacing(self) -> None:
        bridge = AndroidBridge("test-device")
        bridge._run = Mock()  # type: ignore[method-assign]

        bridge.tap_many(((10, 20), (30, 40), (50, 60)), delay_s=0.25)

        bridge._run.assert_called_once_with(
            "shell",
            "sh",
            "-c",
            "input tap 10 20; sleep 0.250; input tap 30 40; sleep 0.250; input tap 50 60",
        )

    def test_tap_many_rejects_invalid_coordinates(self) -> None:
        bridge = AndroidBridge("test-device")
        with self.assertRaises(AdbError):
            bridge.tap_many(((10, -1),))
