import json
from pathlib import Path
import tempfile
import unittest

from plant_automation.scenario import ScenarioError, load_scenario


class ScenarioTests(unittest.TestCase):
    def write(self, payload: object) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        handle.write(json.dumps(payload))
        handle.close()
        return Path(handle.name)

    def test_accepts_supported_actions(self) -> None:
        path = self.write({"actions": [{"type": "tap", "x": 1, "y": 2}, {"type": "wait", "seconds": 0}]})
        self.assertEqual([action.type for action in load_scenario(path)], ["tap", "wait"])

    def test_rejects_unknown_action(self) -> None:
        path = self.write({"actions": [{"type": "shell", "command": "bad"}]})
        with self.assertRaises(ScenarioError):
            load_scenario(path)

    def test_rejects_unbounded_wait(self) -> None:
        path = self.write({"actions": [{"type": "wait", "seconds": 601}]})
        with self.assertRaises(ScenarioError):
            load_scenario(path)


if __name__ == "__main__":
    unittest.main()
