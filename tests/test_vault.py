import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.data import DataGateway
from agent.vault import VaultIndex


class VaultTests(unittest.TestCase):
    def test_wikilinks_create_edges_and_search_returns_the_matching_source(self):
        """Removing link parsing or source text indexing would break this contract."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "alpha.md").write_text(
                "# Alpha\nPlano para [[Beta]] e vendas.", encoding="utf-8"
            )
            (root / "beta.md").write_text("# Beta\nProjeto central.", encoding="utf-8")

            index = VaultIndex.from_roots([root])
            index.build()

            result = index.search("vendas")[0]
            self.assertEqual(result["filename"], "alpha.md")
            graph = index.graph()
            self.assertEqual(len(graph["edges"]), 1)
            edge = graph["edges"][0]
            self.assertEqual(len(index.shortest_path(edge["source"], edge["target"])), 2)

    def test_pdf_is_indexed_with_explicit_unavailable_text_status(self):
        """Treating an unread PDF as extracted text would violate the API contract."""
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "brief.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")

            index = VaultIndex.from_roots([Path(tmp)])
            index.build()

            node = index.graph()["nodes"][0]
            self.assertEqual(node["type"], "pdf")
            self.assertEqual(node["extraction_status"], "metadata_only")
            self.assertEqual(node["text"], "")

    def test_source_documents_keep_ids_and_support_node_lookup(self):
        """Replacing a supplied stable ID would disconnect demo graph edges."""
        index = VaultIndex(
            source_documents=[
                {
                    "id": "demo-stable",
                    "title": "Demo source",
                    "filename": "demo.md",
                    "preview": "Searchable preview",
                }
            ]
        )
        index.build()

        result = index.search("searchable")
        self.assertEqual([node["id"] for node in result], ["demo-stable"])
        self.assertEqual(index.node("demo-stable")["title"], "Demo source")
        self.assertIsNone(index.node("missing"))
        self.assertEqual(index.shortest_path("demo-stable", "missing"), [])

    def test_gateway_vault_preserves_demo_ids_and_dataset_edges(self):
        """Omitting dataset edges would leave a disconnected demo knowledge graph."""
        with patch("agent.data.is_demo_mode", return_value=True):
            gateway = DataGateway()
            index = gateway.vault_index()

        graph = index.graph()
        self.assertEqual(graph["nodes"][0]["id"], "demo-000")
        self.assertIn({"source": "demo-000", "target": "demo-003"}, graph["edges"])
