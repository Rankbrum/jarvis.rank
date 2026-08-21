import json
import tempfile
import unittest
from pathlib import Path

from agent.data import DataGateway
from data.generate_demo import generate_dataset


class DemoDataTests(unittest.TestCase):
    def test_generation_is_deterministic_and_edges_are_valid(self):
        first = generate_dataset()
        second = generate_dataset()
        self.assertEqual(first, second)
        ids = {item["id"] for item in first["documents"]}
        self.assertTrue(first["edges"])
        self.assertTrue(all(edge["source"] in ids and edge["target"] in ids for edge in first["edges"]))

    def test_fixture_contains_no_real_contact_details(self):
        serialized = json.dumps(generate_dataset(), ensure_ascii=False).lower()
        for forbidden in ("renan brum", "augustocostabrum", "99764-3562"):
            self.assertNotIn(forbidden, serialized)

    def test_gateway_loads_injected_demo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.json"
            path.write_text(json.dumps(generate_dataset()), encoding="utf-8")
            gateway = DataGateway(demo_path=path)
            self.assertGreater(len(gateway.documents()), 10)
