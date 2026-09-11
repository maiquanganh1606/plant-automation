"""Desktop entry point used by the distributable application.

The normal CLI intentionally uses paths relative to the project directory.  A
packaged application has no project directory the customer can safely write
to, so this module copies the initial configuration and calibration assets to
the current user's application-data directory on its first launch.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

from .external_tools import tool_environment


APP_FOLDER = "Plant Automation"


def resource_root() -> Path:
    """Return read-only resources, whether running from source or a bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def user_data_root() -> Path:
    """Return the per-user, writable directory for settings and references."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_FOLDER


def _copy_initial_files(source: Path, destination: Path) -> None:
    """Copy only missing initial assets; never overwrite customer calibration."""
    if not source.exists():
        return
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        target = destination / item.relative_to(source)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def prepare_runtime() -> Path:
    """Create a writable working directory populated with safe defaults."""
    runtime = user_data_root()
    runtime.mkdir(parents=True, exist_ok=True)
    source = resource_root()
    _copy_initial_files(source / "config", runtime / "config")
    _copy_initial_files(source / "captures", runtime / "captures")
    return runtime


def main() -> int:
    """Launch the GUI, or act as the worker process spawned by that GUI."""
    # In a frozen build the dashboard starts a second copy of this executable
    # for the farm loop.  Dispatching it here preserves the same stop/log
    # behavior as the Python development build.
    # Finder launches .app bundles with a reduced PATH.  Populate standard
    # Homebrew/Android SDK paths before GUI and worker processes start.
    os.environ.update(tool_environment())
    if "--automation-worker" in sys.argv:
        from .cli import main as cli_main

        sys.argv.remove("--automation-worker")
        return cli_main()

    runtime = prepare_runtime()
    os.chdir(runtime)
    from .qt_gui import launch

    return launch(device_profile_path=runtime / "config" / "device-profiles" / "default-farm.json")


if __name__ == "__main__":
    raise SystemExit(main())
