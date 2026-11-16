"""Portable writable defaults and validated, configuration-relative paths."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import ScoutError


def default_home():
    override = os.environ.get("GAME_SCOUT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    project = Path(__file__).resolve().parents[1]
    if (project / "pyproject.toml").is_file():
        return project
    # A wheel must never write libraries or settings into site-packages.
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
    return base / "Ghostline" / "game-scout"


def resolve_path(value, base, name):
    if not isinstance(value, str) or not value.strip():
        raise ScoutError(f"{name} must be a nonempty path string")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def read_settings(path):
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ScoutError("Configuration must be a JSON object")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ScoutError("Unsupported configuration schema_version; expected 1")
    return config


def load_config(path):
    path = path.expanduser().resolve()
    config = read_settings(path)
    for name in ("runtime", "data_root"):
        config[name] = str(resolve_path(config.get(name), path.parent, name))
    if config.get("competing_lock") is not None:
        config["competing_lock"] = str(
            resolve_path(config["competing_lock"], path.parent, "competing_lock")
        )
    return config
