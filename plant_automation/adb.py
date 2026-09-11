from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from collections.abc import Iterable

from .external_tools import tool_path


class AdbError(RuntimeError):
    """An ADB command could not be completed."""


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str | None = None


class AndroidBridge:
    def __init__(self, serial: str | None = None) -> None:
        self.serial = serial

    @staticmethod
    def _tool(name: str) -> str:
        path = tool_path(name)
        if not path:
            raise AdbError(f"Không tìm thấy '{name}'. Hãy dùng nút Cài ADB / scrcpy hoặc cài thủ công.")
        return path

    @staticmethod
    def devices() -> list[Device]:
        adb = AndroidBridge._tool("adb")
        completed = subprocess.run(
            [adb, "devices", "-l"], text=True, capture_output=True, check=False
        )
        if completed.returncode:
            raise AdbError(completed.stderr.strip() or "Không thể truy vấn ADB.")

        result: list[Device] = []
        for line in completed.stdout.splitlines()[1:]:
            columns = line.split()
            if len(columns) < 2:
                continue
            model = next((item[6:] for item in columns[2:] if item.startswith("model:")), None)
            result.append(Device(serial=columns[0], state=columns[1], model=model))
        return result

    def resolve_serial(self) -> str:
        if self.serial:
            return self.serial
        ready = [device for device in self.devices() if device.state == "device"]
        if len(ready) == 1:
            return ready[0].serial
        if not ready:
            raise AdbError("Không thấy điện thoại sẵn sàng. Kiểm tra USB debugging và lệnh 'adb devices -l'.")
        raise AdbError("Có nhiều điện thoại. Hãy chọn một bằng --serial SERIAL.")

    def _run(self, *arguments: str, binary: bool = False) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
        adb = self._tool("adb")
        command = [adb, "-s", self.resolve_serial(), *arguments]
        completed = subprocess.run(command, capture_output=True, text=not binary, check=False)
        if completed.returncode:
            stderr = completed.stderr.decode() if binary and isinstance(completed.stderr, bytes) else completed.stderr
            raise AdbError(str(stderr).strip() or f"ADB command failed: {' '.join(command)}")
        return completed

    def tap(self, x: int, y: int) -> None:
        self._run("shell", "input", "tap", str(x), str(y))

    def tap_many(self, points: Iterable[tuple[int, int]], *, delay_s: float = 0.25) -> None:
        """Tap several validated points through one ADB shell session.

        Opening a new ``adb shell`` for every seed introduces noticeable latency.
        Keeping the short pause inside one Android shell is faster while still giving
        the game time to accept each input.
        """
        taps = tuple(points)
        if delay_s < 0:
            raise AdbError("Độ trễ giữa các lần chạm không được âm.")
        if not taps:
            return
        commands: list[str] = []
        for index, (x, y) in enumerate(taps):
            if not isinstance(x, int) or not isinstance(y, int) or x < 0 or y < 0:
                raise AdbError("Tọa độ chạm không hợp lệ.")
            commands.append(f"input tap {x} {y}")
            if delay_s and index < len(taps) - 1:
                commands.append(f"sleep {delay_s:.3f}")
        self._run("shell", "sh", "-c", "; ".join(commands))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        self._run("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))

    def screenshot(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        completed = self._run("exec-out", "screencap", "-p", binary=True)
        destination.write_bytes(completed.stdout)  # type: ignore[arg-type]

    def mirror(self) -> None:
        scrcpy = self._tool("scrcpy")
        subprocess.Popen([scrcpy, "--serial", self.resolve_serial()])
