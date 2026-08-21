import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.data import DataGateway
from agent.security import SecurityError, is_supported_file, validate_source_path


class SecurityTests(unittest.TestCase):
    def test_path_outside_allowed_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(SecurityError):
                validate_source_path(Path(outside) / "secret.md", [Path(root)])

    def test_path_traversal_and_symlink_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            root_path = Path(root)
            outside_path = Path(outside)
            with self.assertRaises(SecurityError):
                validate_source_path(root_path / ".." / outside_path.name / "secret.md", [root_path])

            link = root_path / "outside-link"
            try:
                link.symlink_to(outside_path, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlinks unavailable: {error}")
            with self.assertRaises(SecurityError):
                validate_source_path(link / "secret.md", [root_path])

    def test_supported_file_enforces_extension_size_and_hidden_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            allowed = directory / "note.md"
            allowed.write_text("safe", encoding="utf-8")
            blocked = directory / "script.py"
            blocked.write_text("print('x')", encoding="utf-8")
            hidden_directory = directory / ".cache"
            hidden_directory.mkdir()
            hidden_file = hidden_directory / "note.txt"
            hidden_file.write_text("safe", encoding="utf-8")

            self.assertTrue(is_supported_file(allowed))
            self.assertFalse(is_supported_file(blocked))
            self.assertFalse(is_supported_file(allowed, max_bytes=2))
            self.assertFalse(is_supported_file(hidden_file))

    def test_configured_roots_returns_only_enabled_read_only_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            allowed = directory / "allowed"
            allowed.mkdir()
            config = directory / "sources.json"
            config.write_text(
                json.dumps(
                    {
                        "sources": [
                            {"path": str(allowed), "enabled": True, "read_only": True},
                            {"path": str(allowed), "enabled": False, "read_only": True},
                            {"path": str(allowed), "enabled": True, "read_only": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch("agent.data.is_demo_mode", return_value=False):
                self.assertEqual(DataGateway().configured_roots(config), (allowed.resolve(),))

    def test_configured_roots_does_not_read_real_roots_in_demo_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "missing-sources.json"
            with patch("agent.data.is_demo_mode", return_value=True):
                self.assertEqual(DataGateway().configured_roots(missing_config), ())
