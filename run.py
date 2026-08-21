import argparse
import os
from pathlib import Path


def load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    load_local_env(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    from agent.main import create_server

    server = create_server(args.host, args.port)
    print(f"JARVIS disponível em http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
