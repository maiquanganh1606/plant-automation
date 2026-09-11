import unittest
import sys
from unittest.mock import patch

from plant_automation.dependency_setup import check_dependencies, missing_summary
from plant_automation.external_tools import tool_path


class DependencySetupTests(unittest.TestCase):
    @patch("plant_automation.external_tools.shutil.which", side_effect=lambda name: "/bin/" + name if name == "adb" else None)
    def test_reports_missing_scrcpy(self, _which):
        with patch("plant_automation.external_tools.common_tool_directories", return_value=()):
            status = check_dependencies()
        self.assertFalse(status.ready)
        self.assertEqual(missing_summary(status), "scrcpy")

    @patch("plant_automation.external_tools.shutil.which", return_value="/bin/tool")
    def test_ready_when_both_tools_exist(self, _which):
        status = check_dependencies()
        self.assertTrue(status.ready)
        self.assertEqual(missing_summary(status), "Không thiếu công cụ")

    def test_finds_tool_outside_minimal_path(self):
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / ("adb.exe" if sys.platform == "win32" else "adb")
            executable.write_text("#!/bin/sh\n")
            executable.chmod(0o755)
            with patch("plant_automation.external_tools.shutil.which", return_value=None):
                self.assertEqual(tool_path("adb", search_dirs=(Path(directory),)), str(executable))


if __name__ == "__main__":
    unittest.main()
