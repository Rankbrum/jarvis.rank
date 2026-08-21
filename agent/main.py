import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent import data


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


class BootstrapHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/api/status":
            self.send_error(404)
            return
        body = json.dumps({"ok": True, "data": build_status()}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), BootstrapHandler)
