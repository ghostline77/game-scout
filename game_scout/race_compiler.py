"""Invoke the installed Rust race compiler through its public JSON CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from .errors import ScoutError


def executable():
    override = os.environ.get("GHOSTLINE_RACE_BUILDER")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise ScoutError(
                f"GHOSTLINE_RACE_BUILDER executable does not exist: {path}"
            )
        return path
    name = "ghostline-race-builder" + (".exe" if os.name == "nt" else "")
    installed = shutil.which(name)
    if installed:
        return Path(installed).resolve()
    raise ScoutError(
        "Race Builder executable not found. Install the CLI with "
        "`cargo install --locked --git https://github.com/ghostline77/race-builder`, or set GHOSTLINE_RACE_BUILDER to its executable."
    )


def run(builder, *arguments):
    try:
        result = subprocess.run(
            [str(builder), *map(str, arguments)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ScoutError(f"Race Builder {arguments[0]} failed: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ScoutError(f"Race Builder {arguments[0]} failed: {detail[-8000:]}")
    try:
        report = json.loads(result.stdout)
    except ValueError as error:
        raise ScoutError(
            f"Race Builder {arguments[0]} returned invalid JSON"
        ) from error
    if not isinstance(report, dict):
        raise ScoutError(f"Race Builder {arguments[0]} returned an invalid report")
    return report
