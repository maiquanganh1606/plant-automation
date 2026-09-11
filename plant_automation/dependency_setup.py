"""Detection and consent-driven installation of external Android tools."""

from __future__ import annotations

from dataclasses import dataclass
import platform
import shlex

from .external_tools import tool_path


@dataclass(frozen=True)
class DependencyStatus:
    adb: str | None
    scrcpy: str | None

    @property
    def ready(self) -> bool:
        return self.adb is not None and self.scrcpy is not None


def check_dependencies() -> DependencyStatus:
    return DependencyStatus(tool_path("adb"), tool_path("scrcpy"))


def install_command() -> tuple[str, list[str]] | None:
    """Return a shell command for this OS, or None if no safe installer exists."""
    system = platform.system()
    if system == "Darwin":
        brew = tool_path("brew")
        if brew is None:
            return None
        command = f"{shlex.quote(brew)} install --cask android-platform-tools && {shlex.quote(brew)} install scrcpy"
        return "/bin/sh", ["-lc", command]
    if system == "Windows":
        command = (
            "winget install --id Google.PlatformTools -e --source winget "
            "--accept-source-agreements --accept-package-agreements; "
            "winget install --id Genymobile.scrcpy -e --source winget "
            "--accept-source-agreements --accept-package-agreements"
        )
        return "powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    return None


def missing_summary(status: DependencyStatus) -> str:
    missing = []
    if status.adb is None:
        missing.append("ADB")
    if status.scrcpy is None:
        missing.append("scrcpy")
    return ", ".join(missing) if missing else "Không thiếu công cụ"
