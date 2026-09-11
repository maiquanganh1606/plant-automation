"""Find Android command-line tools from desktop applications and terminals.

Apps launched by Finder/Explorer often receive a minimal PATH.  This module
looks in the standard locations used by Homebrew, Android Studio and WinGet,
so a packaged desktop app finds tools that already work in a terminal.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
from collections.abc import Iterable


def common_tool_directories() -> tuple[Path, ...]:
    directories: list[Path] = []
    if sys.platform == "darwin":
        directories.extend([
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            Path.home() / "Library" / "Android" / "sdk" / "platform-tools",
            Path("/Applications/Android Studio.app/Contents/sdk/platform-tools"),
        ])
    elif sys.platform == "win32":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        directories.extend([
            local_app_data / "Android" / "Sdk" / "platform-tools",
            program_files / "Android" / "Android Studio" / "platform-tools",
            local_app_data / "Microsoft" / "WinGet" / "Packages",
        ])
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(variable)
        if value:
            directories.append(Path(value) / "platform-tools")
    return tuple(dict.fromkeys(directories))


def tool_path(name: str, *, search_dirs: Iterable[Path] | None = None) -> str | None:
    """Return an executable path even if the application PATH is minimal."""
    in_path = shutil.which(name)
    if in_path:
        return in_path
    suffix = ".exe" if sys.platform == "win32" else ""
    for directory in search_dirs if search_dirs is not None else common_tool_directories():
        candidate = directory / f"{name}{suffix}"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def tool_environment() -> dict[str, str]:
    """Build PATH for child processes started by the packaged app."""
    environment = os.environ.copy()
    path_items = environment.get("PATH", "").split(os.pathsep)
    additions = [str(directory) for directory in common_tool_directories() if directory.is_dir()]
    environment["PATH"] = os.pathsep.join(dict.fromkeys([*additions, *path_items]))
    return environment
