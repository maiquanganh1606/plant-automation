from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


MAX_ACTIONS = 100
MAX_WAIT_SECONDS = 600


class ScenarioError(ValueError):
    """A scenario is malformed or exceeds safe MVP limits."""


@dataclass(frozen=True)
class Action:
    type: str
    values: dict[str, Any]


def load_scenario(path: Path) -> list[Action]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ScenarioError(f"Không tìm thấy kịch bản: {path}") from error
    except json.JSONDecodeError as error:
        raise ScenarioError(f"JSON không hợp lệ: {error.msg} (dòng {error.lineno})") from error

    actions = document.get("actions") if isinstance(document, dict) else None
    if not isinstance(actions, list) or not actions:
        raise ScenarioError("Kịch bản phải có mảng 'actions' không rỗng.")
    if len(actions) > MAX_ACTIONS:
        raise ScenarioError(f"Kịch bản vượt quá giới hạn {MAX_ACTIONS} thao tác.")

    parsed: list[Action] = []
    for index, raw in enumerate(actions, start=1):
        if not isinstance(raw, dict) or not isinstance(raw.get("type"), str):
            raise ScenarioError(f"Thao tác #{index} phải có trường 'type'.")
        action_type = raw["type"]
        values = {key: value for key, value in raw.items() if key != "type"}
        _validate(index, action_type, values)
        parsed.append(Action(type=action_type, values=values))
    return parsed


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(index: int, action_type: str, values: dict[str, Any]) -> None:
    if action_type == "tap":
        required = ("x", "y")
    elif action_type == "swipe":
        required = ("x1", "y1", "x2", "y2", "duration_ms")
    elif action_type == "wait":
        seconds = values.get("seconds")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not 0 <= seconds <= MAX_WAIT_SECONDS:
            raise ScenarioError(f"Thao tác #{index}: seconds phải trong khoảng 0–{MAX_WAIT_SECONDS}.")
        return
    elif action_type == "screenshot":
        return
    else:
        raise ScenarioError(f"Thao tác #{index}: type '{action_type}' chưa được hỗ trợ.")

    if not all(_integer(values.get(field)) and values[field] >= 0 for field in required):
        raise ScenarioError(f"Thao tác #{index}: {', '.join(required)} phải là số nguyên không âm.")
    if action_type == "swipe" and not 1 <= values["duration_ms"] <= 10_000:
        raise ScenarioError(f"Thao tác #{index}: duration_ms phải trong khoảng 1–10000.")
