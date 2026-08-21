import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent.agent import JarvisAgent
from agent.main import ApiApplication, build_application, create_server, make_handler
from agent.memory import MemoryStore
from agent.tools import ToolRegistry, ToolResult


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

    def test_json_content_type_and_route_values_are_strictly_validated(self):
        """Prefix media-type checks or string coercion would turn structured input into commands."""
        jsonp = self.app.dispatch(
            "POST", "/api/chat", {"Content-Type": "application/jsonp"}, b'{"text": "oi"}'
        )
        unsupported_parameter = self.app.dispatch(
            "POST", "/api/chat", {"Content-Type": "application/json; boundary=test"}, b'{"text": "oi"}'
        )
        array = self.app.dispatch(
            "POST", "/api/chat", {"Content-Type": "application/json"}, b"[]"
        )
        invalid_text = self.app.dispatch(
            "POST", "/api/chat", {"Content-Type": "application/json; charset=utf-8"}, b'{"text": []}'
        )
        invalid_search = self.app.dispatch(
            "POST", "/api/search", {"Content-Type": "application/json"}, b'{"query": "  "}'
        )
        invalid_memory = self.app.dispatch(
            "POST", "/api/remember", {"Content-Type": "application/json"}, b'{"fact": "prioridade", "confirmed": "false"}'
        )

        self.assertEqual(json.loads(jsonp.body)["error"]["code"], "INVALID_CONTENT_TYPE")
        self.assertEqual(
            json.loads(unsupported_parameter.body)["error"]["code"], "INVALID_CONTENT_TYPE"
        )
        for response in (array, invalid_text, invalid_search, invalid_memory):
            self.assertEqual(response.status, 400)
            self.assertEqual(json.loads(response.body)["error"]["code"], "INVALID_REQUEST")

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

    def test_duplicate_memory_is_a_conflict_not_an_internal_error(self):
        """An existing same-day memory filename must have a stable, recoverable API result."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = MemoryStore(application_root=root, today=lambda: "2026-08-21")
            app = ApiApplication(
                JarvisAgent(ToolRegistry(self.app.index, memory)), self.app.index
            )
            request = json.dumps({"fact": "Priorizar vendas", "confirmed": True}).encode()
            first = app.dispatch("POST", "/api/remember", {"Content-Type": "application/json"}, request)
            duplicate = app.dispatch("POST", "/api/remember", {"Content-Type": "application/json"}, request)

        self.assertEqual(first.status, 200)
        self.assertEqual(duplicate.status, 409)
        self.assertEqual(json.loads(duplicate.body)["error"]["code"], "MEMORY_ALREADY_EXISTS")

    def test_chat_dispatch_serializes_shared_agent_state(self):
        """Concurrent chat requests must not mutate the one conversation history at the same time."""
        class TrackingAgent:
            def __init__(self):
                self.active = 0
                self.maximum_active = 0
                self.measurement_lock = threading.Lock()

            def respond(self, text: str) -> ToolResult:
                with self.measurement_lock:
                    self.active += 1
                    self.maximum_active = max(self.maximum_active, self.active)
                time.sleep(0.05)
                with self.measurement_lock:
                    self.active -= 1
                return ToolResult(text, {"type": "test"})

        agent = TrackingAgent()
        app = ApiApplication(agent, self.app.index)
        barrier = threading.Barrier(3)
        responses = []

        def send(text: str) -> None:
            barrier.wait()
            responses.append(
                app.dispatch(
                    "POST", "/api/chat", {"Content-Type": "application/json"}, json.dumps({"text": text}).encode()
                )
            )

        workers = [threading.Thread(target=send, args=(text,)) for text in ("um", "dois")]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join(timeout=2)

        self.assertEqual(agent.maximum_active, 1)
        self.assertEqual([response.status for response in responses], [200, 200])


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

    def _raw_request(self, method: str, path: str, headers=(), body: bytes = b""):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for name, value in headers:
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response, payload

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

    def test_create_server_rejects_non_loopback_bindings(self):
        """Allowing a public bind would expose a deliberately unauthenticated local API."""
        with self.assertRaises(ValueError):
            create_server("0.0.0.0", 0)

    def test_handler_rejects_missing_or_non_loopback_host(self):
        """Trusting an arbitrary Host would make the local-only boundary spoofable."""
        missing, missing_body = self._raw_request("GET", "/api/status")
        arbitrary, arbitrary_body = self._raw_request(
            "GET", "/api/status", (("Host", "attacker.invalid"),)
        )
        allowed, allowed_body = self._raw_request(
            "GET", "/api/status", (("Host", f"127.0.0.1:{self.server.server_port}"),)
        )

        for response, body in ((missing, missing_body), (arbitrary, arbitrary_body)):
            self.assertEqual(response.status, 400)
            self.assertEqual(json.loads(body)["error"]["code"], "INVALID_HOST")
        self.assertEqual(allowed.status, 200)
        self.assertTrue(json.loads(allowed_body)["ok"])

    def test_handler_rejects_unsafe_origin_but_allows_matching_loopback_origin(self):
        """A browser request from another origin must not be able to change local state."""
        body = b'{"text":"oi"}'
        common = (("Host", f"127.0.0.1:{self.server.server_port}"), ("Content-Type", "application/json"), ("Content-Length", str(len(body))))
        unsafe_headers = (
            ("Host", f"127.0.0.1:{self.server.server_port}"),
            ("Content-Type", "application/json"),
            ("Content-Length", "0"),
            ("Origin", "https://attacker.invalid"),
        )
        unsafe, unsafe_body = self._raw_request(
            "POST", "/api/chat", unsafe_headers
        )
        absent, absent_body = self._raw_request("POST", "/api/chat", common, body)
        safe, safe_body = self._raw_request(
            "POST", "/api/chat", common + (("Origin", f"http://127.0.0.1:{self.server.server_port}"),), body
        )

        self.assertEqual(unsafe.status, 403)
        self.assertEqual(json.loads(unsafe_body)["error"]["code"], "UNSAFE_ORIGIN")
        self.assertEqual(absent.status, 200)
        self.assertTrue(json.loads(absent_body)["ok"])
        self.assertEqual(safe.status, 200)
        self.assertTrue(json.loads(safe_body)["ok"])

    def test_handler_rejects_ambiguous_or_unframed_post_bodies(self):
        """Transfer encodings and ambiguous lengths must not reach the request dispatcher."""
        host = ("Host", f"127.0.0.1:{self.server.server_port}")
        content_type = ("Content-Type", "application/json")
        missing, missing_body = self._raw_request("POST", "/api/chat", (host, content_type))
        transfer, transfer_body = self._raw_request(
            "POST", "/api/chat", (host, content_type, ("Transfer-Encoding", "chunked"))
        )
        duplicate, duplicate_body = self._raw_request(
            "POST", "/api/chat", (host, content_type, ("Content-Length", "2"), ("Content-Length", "2")), b"{}"
        )

        for response, body, status, code in (
            (missing, missing_body, 411, "LENGTH_REQUIRED"),
            (transfer, transfer_body, 400, "UNSUPPORTED_TRANSFER_ENCODING"),
            (duplicate, duplicate_body, 400, "INVALID_CONTENT_LENGTH"),
        ):
            self.assertEqual(response.status, status)
            self.assertEqual(json.loads(body)["error"]["code"], code)

    def test_handler_returns_sanitized_json_for_unexpected_application_error(self):
        """Unhandled exceptions must not expose internal messages or default HTML errors."""
        class ExplodingApplication:
            def dispatch(self, method, path, headers, body):
                raise RuntimeError("internal-secret-detail")

        server = create_server("127.0.0.1", 0)
        server.RequestHandlerClass = make_handler(ExplodingApplication())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection(*server.server_address, timeout=2)
            connection.request("GET", "/api/status")
            response = connection.getresponse()
            body = response.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        payload = json.loads(body)
        self.assertEqual(response.status, 500)
        self.assertEqual(payload["error"]["code"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("internal-secret-detail", body.decode())
