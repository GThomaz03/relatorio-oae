"""Entry point do backend para aplicativo desktop (Electron + PyInstaller)."""

from __future__ import annotations

import logging
import os
import socket
from pathlib import Path

from backend.config import (
    backend_port_file,
    ensure_user_data_layout,
    get_log_level_from_env,
    setup_logging,
)

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8765
PORT_RANGE = 10


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def resolve_port(host: str = "127.0.0.1") -> int:
    requested = int(os.environ.get("OAE_PORT", str(DEFAULT_PORT)))
    for offset in range(PORT_RANGE):
        candidate = requested + offset
        if _port_available(host, candidate):
            return candidate
    raise RuntimeError(f"Nenhuma porta disponível entre {requested} e {requested + PORT_RANGE - 1}")


def write_port_file(port: int) -> None:
    path = backend_port_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(port), encoding="utf-8")


def main() -> None:
    ensure_user_data_layout()
    from backend.config import LOGS_DIR

    log_path = LOGS_DIR / "backend.log"
    setup_logging(get_log_level_from_env(), log_file=log_path)

    host = os.environ.get("OAE_HOST", "127.0.0.1")
    port = resolve_port(host)
    write_port_file(port)
    os.environ["OAE_PORT"] = str(port)

    logger.info("Iniciando API desktop em http://%s:%d", host, port)

    import uvicorn

    uvicorn.run(
        "backend.api.server:app",
        host=host,
        port=port,
        reload=False,
        log_level=get_log_level_from_env().lower(),
    )


if __name__ == "__main__":
    main()
