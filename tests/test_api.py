import http.client
import json
import threading
import unittest
from pathlib import Path

from agent.main import build_application, create_server


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = build_application()

    def test_status_and_graph_are_json_with_indexed_demo_documents(self):
        """Dropping DataGateway.vault_index() would empty the status and graph contracts."""
        status = self.app.dispatch("GET", "/api/status", {}, b"")
        graph = self.app.dispatch("GET", "/api/graph", {}, b"")

        status_payload = json.loads(status.body)
        graph_payload = json.loads(graph.body)
        self.assertEqual(status.status, 200)
        self.assertTrue(status_payload["ok"])
        self.assertGreater(status_payload["data"]["indexed_documents"], 10)
        self.assertGreater(len(graph_payload["data"]["nodes"]), 10)

    def test_graph_node_route_decodes_an_index_node_id(self):
        """Removing the node lookup must not turn existing graph nodes into a 404."""
        response = self.app.dispatch("GET", "/api/node/demo-000", {}, b"")

        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body)["data"]["id"], "demo-000")

    def test_chat_rejects_wrong_content_type_and_malformed_json(self):
        """Skipping JSON boundary checks would let malformed input reach the agent."""
        wrong = self.app.dispatch("POST", "/api/chat", {"Content-Type": "text/plain"}, b"hello")
        malformed = self.app.dispatch("POST", "/api/chat", {"Content-Type": "application/json"}, b"{")

        self.assertEqual(wrong.status, 415)
        self.assertEqual(json.loads(wrong.body)["error"]["code"], "INVALID_CONTENT_TYPE")
        self.assertEqual(malformed.status, 400)
        self.assertEqual(json.loads(malformed.body)["error"]["code"], "INVALID_JSON")

    def test_unknown_route_and_oversized_body_use_standard_error_shape(self):
        """Missing status codes or error envelopes would leave API clients without recovery data."""
        missing = self.app.dispatch("GET", "/api/missing", {}, b"")
        huge = self.app.dispatch(
            "POST", "/api/chat", {"Content-Type": "application/json"}, b"x" * 1_048_577
        )

        self.assertEqual(missing.status, 404)
        self.assertEqual(huge.status, 413)
        for response, code in ((missing, "NOT_FOUND"), (huge, "REQUEST_TOO_LARGE")):
            payload = json.loads(response.body)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"]["code"], code)
            self.assertTrue(payload["error"]["message"])

    def test_memory_endpoint_requires_confirmation(self):
        """Ignoring confirmed=false would write persistent user memory without consent."""
        response = self.app.dispatch(
            "POST",
            "/api/remember",
            {"Content-Type": "application/json"},
            json.dumps({"fact": "RANKBRUM ONE AI é prioridade", "confirmed": False}).encode(),
        )

        self.assertEqual(response.status, 409)
        self.assertEqual(json.loads(response.body)["error"]["code"], "MEMORY_CONFIRMATION_REQUIRED")

    def test_application_memory_is_owned_by_the_repository(self):
        """A caller-supplied or temporary memory root would misplace durable user memories."""
        expected_root = Path(__file__).parents[1] / "memory"

        self.assertEqual(self.app.agent.tools.memory.root, expected_root.absolute())


class HttpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _request(self, path: str, method: str = "GET"):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        connection.request(method, path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response, body

    def test_static_shell_is_served_but_path_traversal_and_directory_are_not(self):
        """Serving arbitrary resolved files or directory listings would expose local application data."""
        page, page_body = self._request("/")
        traversal, traversal_body = self._request("/%2e%2e/agent/main.py")
        directory, directory_body = self._request("/ui/")

        self.assertEqual(page.status, 200)
        self.assertIn("text/html", page.getheader("Content-Type"))
        self.assertIn(b"JARVIS", page_body)
        for response, body in ((traversal, traversal_body), (directory, directory_body)):
            self.assertEqual(response.status, 404)
            self.assertEqual(json.loads(body)["error"]["code"], "NOT_FOUND")

    def test_non_get_static_request_returns_a_json_method_error(self):
        """Accepting POSTs to static files would make the public surface ambiguous."""
        response, body = self._request("/styles.css", method="POST")

        self.assertEqual(response.status, 405)
        self.assertEqual(json.loads(body)["error"]["code"], "METHOD_NOT_ALLOWED")
