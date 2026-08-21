import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run


class BootstrapTests(unittest.TestCase):
    def test_load_local_env_does_not_override_process_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("EXAMPLE_VALUE=file\nSECOND_VALUE=loaded\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"EXAMPLE_VALUE": "process"}, clear=False):
                run.load_local_env(env_file)
                self.assertEqual(os.environ["EXAMPLE_VALUE"], "process")
                self.assertEqual(os.environ["SECOND_VALUE"], "loaded")

    def test_demo_mode_defaults_on_and_status_is_explicit(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            import agent.data as data
            import agent.main as main

            importlib.reload(data)
            importlib.reload(main)
            status = main.build_status()
        self.assertTrue(status["demo_mode"])
        self.assertEqual(status["assistant_mode"], "limited")
        self.assertFalse(status["voice_configured"])
