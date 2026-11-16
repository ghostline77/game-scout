"""Install only this tool's CET Lua files and preserve local settings."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from .config import default_home, read_settings, resolve_path
from .errors import ScoutError
from .files import atomic_json, file_lock
from .library import Library


def install(game: Path, data: Path, config_path: Path):
    game = game.expanduser().resolve()
    config_path = config_path.expanduser().resolve()
    previous = read_settings(config_path) if config_path.exists() else {}
    if data is None:
        data = (
            resolve_path(previous["data_root"], config_path.parent, "data_root")
            if previous.get("data_root")
            else default_home() / "data/library"
        )
    data = data.expanduser().resolve()
    mods = game / "bin/x64/plugins/cyber_engine_tweaks/mods"
    if not mods.is_dir():
        raise ScoutError(f"No CET installation at {mods}")
    destination = mods / "game_scout"
    with file_lock(destination / "runtime/controller.lock"):
        backup = (
            game
            / "ghostline-mod-backups"
            / ("game-scout-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        )
        existing = [
            destination / name
            for name in ("init.lua", "engine.lua")
            if (destination / name).exists()
        ]
        if existing:
            backup.mkdir(parents=True)
            for path in existing:
                shutil.copy2(path, backup / path.name)
        for name in ("init.lua", "engine.lua"):
            shutil.copy2(Path(__file__).parent / "cet" / name, destination / name)
    config = {
        "schema_version": 1,
        "game_root": str(game),
        "data_root": str(data),
        "runtime": str(destination / "runtime"),
        "competing_lock": str(mods / "world_location_capture/runtime/controller.lock"),
    }
    atomic_json(config_path, config)
    Library(data)
    return {
        "config": str(config_path.resolve()),
        "mod": str(destination),
        "data_root": str(data),
        "reload_required": True,
        "existing_mod_backup": str(backup) if existing else None,
    }
