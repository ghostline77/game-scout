"""Install, diagnose or serve the standalone Game Scout MCP."""

from __future__ import annotations

import argparse
from contextlib import closing
import importlib
import json
import os
from pathlib import Path
import sys

from .config import default_home, load_config
from .errors import ScoutError
from .installation import install as install
from .library import Library
from .transport import Bridge


def make_bridge(config):
    return Bridge(
        Path(config["runtime"]),
        Path(config["competing_lock"]) if config.get("competing_lock") else None,
    )


def serve(config):
    # Initialize native capture on the main thread before starting heartbeat or
    # operation threads. Keep doctor independent of the image dependencies.
    importlib.import_module("windows_capture")
    from .controller import Scout
    from .images import CameraImages
    from .server import make_server

    with closing(make_bridge(config)) as bridge:
        library = Library(Path(config["data_root"]))
        controller = Scout(bridge, library, CameraImages(library))
        try:
            make_server(controller).run(transport="stdio")
        finally:
            try:
                controller.stop()
            finally:
                if controller.job_thread:
                    controller.job_thread.join(timeout=2)


def main(argv=None):
    home = default_home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=home / ".local/game-scout.json")
    commands = parser.add_subparsers(dest="command", required=True)
    installer = commands.add_parser("install")
    installer.add_argument(
        "--game-root",
        type=Path,
        default=os.environ.get("CYBERPUNK_GAME_ROOT"),
        required=not os.environ.get("CYBERPUNK_GAME_ROOT"),
    )
    installer.add_argument(
        "--data-root",
        type=Path,
        help="Library directory; preserves the configured path on reinstall",
    )
    commands.add_parser("doctor")
    commands.add_parser("serve")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            print(
                json.dumps(
                    install(args.game_root, args.data_root, args.config), indent=2
                )
            )
            return 0
        config = load_config(args.config)
        if args.command == "doctor":
            with closing(make_bridge(config)) as bridge:
                state = bridge.state()
                report = {"ready": True, "runtime": state, "config": config}
                print(json.dumps(report, indent=2))
            return 0
        serve(config)
        return 0
    except (ScoutError, OSError, ValueError, KeyError, ImportError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
