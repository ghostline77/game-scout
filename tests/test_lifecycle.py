"""Configuration portability, reinstall preservation and startup cleanup."""

from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from game_scout import cli, config
from game_scout.files import atomic_json
from game_scout.installation import install
from game_scout.library import Library
from game_scout.transport import Bridge


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_relative_config_paths_resolve_beside_config(self):
        path = self.root / "settings/tool.json"
        atomic_json(
            path,
            {"schema_version": 1, "runtime": "../runtime", "data_root": "../library"},
        )
        result = config.load_config(path)
        self.assertEqual(result["runtime"], str((self.root / "runtime").resolve()))
        self.assertEqual(result["data_root"], str((self.root / "library").resolve()))

    def test_invalid_configuration_is_rejected_before_runtime_threads(self):
        path = self.root / "bad.json"
        for value in (
            [],
            {"schema_version": 1, "runtime": 7, "data_root": "library"},
            {"schema_version": 1, "runtime": "runtime"},
            {"schema_version": True},
        ):
            with self.subTest(value=value):
                atomic_json(path, value)
                with (
                    patch.object(cli, "make_bridge") as bridge,
                    redirect_stderr(io.StringIO()) as errors,
                ):
                    self.assertEqual(cli.main(["--config", str(path), "serve"]), 1)
                bridge.assert_not_called()
                self.assertTrue(errors.getvalue().strip())

    def test_constructor_failure_still_closes_bridge(self):
        bridge = Mock()
        with (
            patch.object(cli.importlib, "import_module"),
            patch.object(cli, "make_bridge", return_value=bridge),
            patch.object(cli, "Library", side_effect=OSError("disk unavailable")),
        ):
            with self.assertRaisesRegex(OSError, "disk unavailable"):
                cli.serve({"runtime": str(self.root), "data_root": str(self.root)})
        bridge.close.assert_called_once()

    def test_reinstall_preserves_library_and_records(self):
        game = self.root / "game"
        (game / "bin/x64/plugins/cyber_engine_tweaks/mods").mkdir(parents=True)
        data = self.root / "existing evidence"
        library = Library(data)
        evidence = library.put("image", "Existing image", {"path": "original.png"})
        path = self.root / "tool.json"
        atomic_json(
            path,
            {"schema_version": 1, "data_root": str(data), "bindings": {"interact": 18}},
        )
        result = install(game, None, path)
        saved = config.load_config(path)
        self.assertEqual(saved["data_root"], str(data))
        self.assertEqual(Library(data).get(evidence["id"]), evidence)
        self.assertTrue((Path(result["mod"]) / "engine.lua").is_file())

    def test_home_override_is_independent_of_working_directory(self):
        with patch.dict("os.environ", {"GAME_SCOUT_HOME": str(self.root)}):
            self.assertEqual(config.default_home(), self.root)

    def test_closing_bridge_stops_heartbeat_thread(self):
        bridge = Bridge(self.root)
        bridge.close()
        self.assertFalse(bridge._pulse.is_alive())


if __name__ == "__main__":
    unittest.main()
