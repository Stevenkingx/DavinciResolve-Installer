"""Memoria de la aplicación entre sesiones.

Solo guarda lo que el sistema no sabe decirnos. El caso importante es la
edición: `/opt/resolve/docs/Welcome.txt` dice «DaVinci Resolve 21.1» tanto si
instalaste la gratuita como la Studio, así que la única forma fiable de saberlo
es acordarse de lo que instalamos nosotros.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = (
    Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    / "davinci-resolve-manager"
    / "state.json"
)


def read() -> dict:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write(data: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # no poder recordar no es motivo para fallar


def record_install(version: str, studio: bool) -> None:
    data = read()
    data["last_install"] = {
        "version": version,
        "studio": studio,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write(data)


def last_install() -> dict:
    value = read().get("last_install")
    return value if isinstance(value, dict) else {}


def preferred_edition() -> str:
    """La edición que el usuario eligió la última vez: "free" o "studio"."""
    value = read().get("preferred_edition")
    return value if value in ("free", "studio") else ""


def set_preferred_edition(edition: str) -> None:
    if edition not in ("free", "studio"):
        return
    data = read()
    data["preferred_edition"] = edition
    write(data)
