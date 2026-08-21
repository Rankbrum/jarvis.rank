import json
import os
import socket
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from agent import data
from agent.agent import JarvisAgent
from agent.data import DataGateway
from agent.memory import MemoryConfirmationRequired, MemoryStore
from agent.tools import ToolRegistry
from agent.vault import VaultIndex


MAX_JSON_BODY = 1_048_576
APPLICATION_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = APPLICATION_ROOT / "ui"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
POST_ROUTE_PATHS = frozenset(
    {"/api/chat", "/api/search", "/api/remember", "/api/brief", "/api/plan"}
)


class RequestValidationError(ValueError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    content_type: str
    body: bytes


def _json_response(status: int, payload: dict[str, object]) -> HttpResponse:
    return HttpResponse(
        status,
        "application/json; charset=utf-8",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )


def build_status() -> dict[str, object]:
    llm_connected = bool(os.getenv("JARVIS_LLM_ENDPOINT"))
    return {
        "demo_mode": data.is_demo_mode(),
        "voice_configured": bool(
            os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID")
        ),
        "model_connected": llm_connected,
        "assistant_mode": "connected" if llm_connected else "limited",
        "indexed_documents": 0,
        "data_source": "demo" if data.is_demo_mode() else "configured",
    }


class ApiApplication:
    def __init__(self, agent: JarvisAgent, index: VaultIndex) -> None:
        self.agent = agent
        self.index = index
        self._agent_lock = threading.Lock()

    def dispatch(
        self, method: str, path: str, headers: Mapping[str, str], body: bytes
    ) -> HttpResponse:
        method = method.upper()
        path = urlsplit(path).path
        if len(body) > MAX_JSON_BODY:
            return self.error(413, "REQUEST_TOO_LARGE", "O corpo excede 1 MB.")

        if method == "GET" and path == "/api/status":
            return _json_response(
                200,
                {
                    "ok": True,
                    "data": {
                        **build_status(),
                        "indexed_documents": len(self.index.nodes),
                    },
                },
            )
        if method == "GET" and path == "/api/graph":
            return _json_response(200, {"ok": True, "data": self.index.graph()})
        if method == "GET" and path.startswith("/api/node/"):
            node = self.index.node(unquote(path.removeprefix("/api/node/")))
            if node is not None:
                return _json_response(200, {"ok": True, "data": node})
            return self.error(404, "NODE_NOT_FOUND", "Nó não encontrado.")

        post_routes = {
            "/api/chat": self._chat,
            "/api/search": self._search,
            "/api/remember": self._remember,
            "/api/brief": self._brief,
            "/api/plan": self._plan,
        }
        if method == "POST" and path in post_routes:
            if not self._is_json_content_type(self._header(headers, "content-type")):
                return self.error(415, "INVALID_CONTENT_TYPE", "Use application/json.")
            try:
                payload = json.loads(body or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.error(400, "INVALID_JSON", "JSON inválido.")
            if not isinstance(payload, dict):
                return self.error(400, "INVALID_REQUEST", "O JSON deve ser um objeto.")
            try:
                result = post_routes[path](payload)
            except RequestValidationError:
                return self.error(400, "INVALID_REQUEST", "Solicitação inválida.")
            except MemoryConfirmationRequired:
                return self.error(
                    409,
                    "MEMORY_CONFIRMATION_REQUIRED",
                    "Confirme explicitamente antes de salvar a memória.",
                )
            except FileExistsError:
                return self.error(409, "MEMORY_ALREADY_EXISTS", "A memória já existe.")
            except (KeyError, ValueError):
                return self.error(400, "INVALID_REQUEST", "Solicitação inválida.")
            return _json_response(
                200,
                {"ok": True, "data": {"spoken": result.spoken, "card": result.card}},
            )

        if path in {"/api/status", "/api/graph", *POST_ROUTE_PATHS} or path.startswith("/api/node/"):
            return self.error(405, "METHOD_NOT_ALLOWED", "Método não permitido.")
        return self.error(404, "NOT_FOUND", "Rota não encontrada.")

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        for key, value in headers.items():
            if key.casefold() == name:
                return str(value)
        return ""

    @staticmethod
    def _is_json_content_type(content_type: str) -> bool:
        parts = content_type.split(";")
        if not parts or parts[0].strip().casefold() != "application/json":
            return False
        seen_charset = False
        for parameter in parts[1:]:
            name, separator, value = parameter.partition("=")
            if not separator or name.strip().casefold() != "charset" or seen_charset:
                return False
            charset = value.strip().strip('"').casefold()
            if charset not in {"utf-8", "utf8"}:
                return False
            seen_charset = True
        return True

    @staticmethod
    def _required_string(payload: dict[str, object], name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise RequestValidationError(name)
        return value.strip()

    @classmethod
    def _optional_string(cls, payload: dict[str, object], name: str, default: str) -> str:
        if name not in payload:
            return default
        return cls._required_string(payload, name)

    def _chat(self, payload: dict[str, object]):
        text = self._required_string(payload, "text")
        with self._agent_lock:
            return self.agent.respond(text)

    def _search(self, payload: dict[str, object]):
        query = self._required_string(payload, "query")
        return self.agent.tools.execute("search_brain", {"query": query})

    def _remember(self, payload: dict[str, object]):
        confirmed = payload.get("confirmed", False)
        if "confirmed" in payload and type(confirmed) is not bool:
            raise RequestValidationError("confirmed")
        return self.agent.tools.execute(
            "remember",
            {
                "fact": self._required_string(payload, "fact"),
                "why": self._optional_string(
                    payload, "why", "Informação durável solicitada pelo usuário."
                ),
                "category": self._optional_string(payload, "category", "general"),
                "confirmed": confirmed,
            },
        )

    def _brief(self, payload: dict[str, object]):
        del payload
        return self.agent.tools.execute("brief_me", {})

    def _plan(self, payload: dict[str, object]):
        del payload
        return self.agent.tools.execute("plan_day", {})

    @staticmethod
    def error(status: int, code: str, message: str) -> HttpResponse:
        return _json_response(status, {"ok": False, "error": {"code": code, "message": message}})


def build_application() -> ApiApplication:
    index = DataGateway().vault_index()
    memory = MemoryStore(application_root=APPLICATION_ROOT)
    return ApiApplication(JarvisAgent(ToolRegistry(index, memory)), index)


def _static_response(request_path: str) -> HttpResponse:
    try:
        path = urlsplit(request_path).path
        relative = "index.html" if path in {"", "/"} else unquote(path.lstrip("/"))
        ui_root = UI_ROOT.resolve(strict=True)
        candidate = (ui_root / relative).resolve(strict=False)
    except (OSError, ValueError):
        return ApiApplication.error(404, "NOT_FOUND", "Arquivo não encontrado.")

    if ui_root not in candidate.parents or not candidate.is_file():
        return ApiApplication.error(404, "NOT_FOUND", "Arquivo não encontrado.")
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
    }
    return HttpResponse(
        200,
        content_types.get(candidate.suffix.lower(), "application/octet-stream"),
        candidate.read_bytes(),
    )


def _loopback_authority(value: str) -> tuple[str, int | None] | None:
    if not value or value != value.strip():
        return None
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port
    except ValueError:
        return None
    if (
        not parsed.hostname
        or parsed.hostname.casefold() not in LOOPBACK_HOSTS
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return None
    return parsed.hostname.casefold(), port


def _matches_loopback_origin(origin: str, host: tuple[str, int | None]) -> bool:
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme.casefold() != "http" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        return False
    origin_host = _loopback_authority(parsed.netloc)
    if origin_host is None:
        return False
    return origin_host == host


def make_handler(application: ApiApplication):
    class JarvisRequestHandler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            try:
                response = self._response_for_request()
            except Exception:
                response = ApiApplication.error(
                    500, "INTERNAL_SERVER_ERROR", "Erro interno do servidor."
                )
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response.body)

        def _response_for_request(self) -> HttpResponse:
            host_values = self.headers.get_all("Host") or []
            host = _loopback_authority(host_values[0]) if len(host_values) == 1 else None
            if host is None:
                return ApiApplication.error(400, "INVALID_HOST", "Host local obrigatório.")

            path = urlsplit(self.path).path
            is_post_body_route = self.command == "POST" and path in POST_ROUTE_PATHS
            origin_values = self.headers.get_all("Origin") or []
            if is_post_body_route and origin_values:
                if len(origin_values) != 1 or not _matches_loopback_origin(origin_values[0], host):
                    return ApiApplication.error(403, "UNSAFE_ORIGIN", "Origem não permitida.")

            if self.headers.get_all("Transfer-Encoding"):
                return ApiApplication.error(
                    400,
                    "UNSUPPORTED_TRANSFER_ENCODING",
                    "Transfer-Encoding não é suportado.",
                )
            length_values = self.headers.get_all("Content-Length") or []
            if len(length_values) > 1:
                return ApiApplication.error(
                    400, "INVALID_CONTENT_LENGTH", "Content-Length inválido."
                )
            if not length_values:
                if is_post_body_route:
                    return ApiApplication.error(
                        411, "LENGTH_REQUIRED", "Content-Length obrigatório."
                    )
                length = 0
            else:
                length_header = length_values[0]
                if not length_header.isascii() or not length_header.isdigit():
                    return ApiApplication.error(
                        400, "INVALID_CONTENT_LENGTH", "Content-Length inválido."
                    )
                length = int(length_header)
            if length > MAX_JSON_BODY:
                return ApiApplication.error(413, "REQUEST_TOO_LARGE", "O corpo excede 1 MB.")

            body = self.rfile.read(length) if length else b""
            if self.path.startswith("/api/"):
                return application.dispatch(self.command, self.path, self.headers, body)
            if self.command == "GET":
                return _static_response(self.path)
            return ApiApplication.error(405, "METHOD_NOT_ALLOWED", "Método não permitido.")

        do_GET = _handle
        do_POST = _handle
        do_PUT = _handle
        do_PATCH = _handle
        do_DELETE = _handle
        do_HEAD = _handle

        def log_message(self, format: str, *args: object) -> None:
            return

    return JarvisRequestHandler


class _IPv6ThreadingHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    if host not in LOOPBACK_HOSTS:
        raise ValueError("JARVIS accepts loopback bindings only")
    bind_host = "127.0.0.1" if host == "localhost" else host
    server_class = _IPv6ThreadingHTTPServer if bind_host == "::1" else ThreadingHTTPServer
    return server_class((bind_host, port), make_handler(build_application()))
