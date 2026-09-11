from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time

from .adb import AndroidBridge
from .scenario import Action


def run_actions(bridge: AndroidBridge, actions: list[Action], capture_dir: Path) -> None:
    for index, action in enumerate(actions, start=1):
        print(f"[{index}/{len(actions)}] {action.type}")
        if action.type == "tap":
            bridge.tap(action.values["x"], action.values["y"])
        elif action.type == "swipe":
            bridge.swipe(**action.values)
        elif action.type == "wait":
            time.sleep(action.values["seconds"])
        elif action.type == "screenshot":
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            bridge.screenshot(capture_dir / f"step-{index}-{stamp}.png")
