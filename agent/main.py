import json
import os
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
            content_type = self._header(headers, "content-type")
            if not content_type.startswith("application/json"):
                return self.error(415, "INVALID_CONTENT_TYPE", "Use application/json.")
            try:
                payload = json.loads(body or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.error(400, "INVALID_JSON", "JSON inválido.")
            if not isinstance(payload, dict):
                return self.error(400, "INVALID_REQUEST", "O JSON deve ser um objeto.")
            try:
                result = post_routes[path](payload)
            except MemoryConfirmationRequired:
                return self.error(
                    409,
                    "MEMORY_CONFIRMATION_REQUIRED",
                    "Confirme explicitamente antes de salvar a memória.",
                )
            except (KeyError, ValueError):
                return self.error(400, "INVALID_REQUEST", "Solicitação inválida.")
            return _json_response(
                200,
                {"ok": True, "data": {"spoken": result.spoken, "card": result.card}},
            )

        if path in {"/api/status", "/api/graph", *post_routes} or path.startswith("/api/node/"):
            return self.error(405, "METHOD_NOT_ALLOWED", "Método não permitido.")
        return self.error(404, "NOT_FOUND", "Rota não encontrada.")

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        for key, value in headers.items():
            if key.casefold() == name:
                return str(value).casefold()
        return ""

    def _chat(self, payload: dict[str, object]):
        return self.agent.respond(str(payload.get("text", "")))

    def _search(self, payload: dict[str, object]):
        return self.agent.tools.execute("search_brain", {"query": str(payload.get("query", ""))})

    def _remember(self, payload: dict[str, object]):
        return self.agent.tools.execute(
            "remember",
            {
                "fact": str(payload.get("fact", "")),
                "why": str(payload.get("why", "Informação durável solicitada pelo usuário.")),
                "category": str(payload.get("category", "general")),
                "confirmed": payload.get("confirmed") is True,
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


def make_handler(application: ApiApplication):
    class JarvisRequestHandler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                response = ApiApplication.error(400, "INVALID_REQUEST", "Content-Length inválido.")
            else:
                if length < 0:
                    response = ApiApplication.error(400, "INVALID_REQUEST", "Content-Length inválido.")
                elif length > MAX_JSON_BODY:
                    response = ApiApplication.error(413, "REQUEST_TOO_LARGE", "O corpo excede 1 MB.")
                else:
                    body = self.rfile.read(length) if length else b""
                    if self.path.startswith("/api/"):
                        response = application.dispatch(self.command, self.path, self.headers, body)
                    elif self.command == "GET":
                        response = _static_response(self.path)
                    else:
                        response = ApiApplication.error(405, "METHOD_NOT_ALLOWED", "Método não permitido.")
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response.body)

        do_GET = _handle
        do_POST = _handle
        do_PUT = _handle
        do_PATCH = _handle
        do_DELETE = _handle
        do_HEAD = _handle

        def log_message(self, format: str, *args: object) -> None:
            return

    return JarvisRequestHandler


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(build_application()))
