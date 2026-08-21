import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class UiRuntimeTests(unittest.TestCase):
    def test_runtime_contracts_in_dependency_free_node_harness(self):
        """Regression-prone UI state flows must execute against a DOM-shaped runtime, not source text."""
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required to run UI runtime contracts.")
        result = subprocess.run(
            [node, "--no-warnings", "tests/test_ui_runtime.mjs"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("UI runtime tests passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
