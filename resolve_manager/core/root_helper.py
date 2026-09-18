#!/usr/bin/env python3
"""Ayudante privilegiado. Se ejecuta como root mediante pkexec o sudo.

Recibe un plan en JSON y lo ejecuta paso a paso, informando del progreso por
stdout en formato JSON-líneas para que la interfaz lo muestre en vivo.

Es deliberadamente autonomo: no importa nada del resto del paquete, para que
funcione bajo pkexec sin depender de PYTHONPATH.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIND_EXEC = "exec"
KIND_SHIELD_LIBS = "shield_libs"
KIND_RESTORE_LIBS = "restore_libs"
KIND_CHOWN = "chown"
KIND_WRITE_DESKTOP = "write_desktop"
ALL_KINDS = {KIND_EXEC, KIND_SHIELD_LIBS, KIND_RESTORE_LIBS, KIND_CHOWN, KIND_WRITE_DESKTOP}


# El ayudante corre aislado bajo pkexec y no importa el paquete, así que lleva
# su propia tablita de traducción. El idioma viaja dentro del plan.
LANG = "es"

MESSAGES = {
    "Comando inválido.": "Invalid command.",
    "No pude ejecutar el comando: {detail}": "Could not run the command: {detail}",
    "No existe {path}; nada que hacer.": "{path} does not exist; nothing to do.",
    "apartada: {name}": "moved aside: {name}",
    "restaurada: {name}": "restored: {name}",
    "{count} librería(s) movidas a {target}": "moved {count} library file(s) to {target}",
    "Ya estaba aplicado.": "Already applied.",
    "No hay librerías apartadas que restaurar.": "No set-aside libraries to restore.",
    "{count} librería(s) restauradas.": "restored {count} library file(s).",
    "Usuario destino inválido.": "Invalid target user.",
    "propietario corregido: {path}": "ownership fixed: {path}",
    "no pude cambiar {path}: {detail}": "could not change {path}: {detail}",
    "{count} ruta(s) revisadas para el usuario {user}.":
        "checked {count} path(s) for user {user}.",
    "Ruta de lanzador inválida.": "Invalid launcher path.",
    "no pude escribir el lanzador: {detail}": "could not write the launcher: {detail}",
    "lanzador escrito en {path}": "launcher written to {path}",
    "error inesperado: {detail}": "unexpected error: {detail}",
    "Uso: root_helper.py <plan.json>": "Usage: root_helper.py <plan.json>",
    "No pude leer el plan: {detail}": "Could not read the plan: {detail}",
    "Acción no permitida: {kind}": "Action not allowed: {kind}",
}


def tr(text: str, **kwargs) -> str:
    out = text if LANG == "es" else MESSAGES.get(text, text)
    return out.format(**kwargs) if kwargs else out


def emit(**payload) -> None:
    """Manda un mensaje a la interfaz. Una línea JSON, siempre vaciando buffer."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log(line: str) -> None:
    emit(t="log", line=line.rstrip("\n"))


# --------------------------------------------------------------------------
# Implementacion de cada tipo de acción
# --------------------------------------------------------------------------

def do_exec(action: dict) -> int:
    argv = action.get("argv") or []
    if not argv or not all(isinstance(a, str) for a in argv):
        log(tr("Comando inválido."))
        return 2

    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (action.get("env") or {}).items()})
    # Salida predecible y sin colores ANSI en el registro.
    env.setdefault("LC_ALL", "C.UTF-8")
    env.setdefault("DEBIAN_FRONTEND", "noninteractive")

    log(f"$ {' '.join(argv)}")
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            errors="replace",
            bufsize=1,
            env=env,
        )
    except OSError as exc:
        log(tr("No pude ejecutar el comando: {detail}", detail=exc))
        return 127

    assert proc.stdout is not None
    for line in proc.stdout:
        log(line)
    return proc.wait()


def do_shield_libs(action: dict) -> int:
    """Aparta las librerías de Resolve que chocan con las del sistema."""
    params = action.get("params") or {}
    libs = Path(params.get("libs_dir", ""))
    disabled = Path(params.get("disabled_dir", ""))
    patterns = params.get("patterns") or []

    if not libs.is_dir():
        log(tr("No existe {path}; nada que hacer.", path=libs))
        return 0

    disabled.mkdir(parents=True, exist_ok=True)
    moved = 0
    for pattern in patterns:
        for item in sorted(libs.glob(pattern)):
            if not item.is_file() and not item.is_symlink():
                continue
            target = disabled / item.name
            if target.exists() or target.is_symlink():
                target.unlink()
            shutil.move(str(item), str(target))
            log(tr("apartada: {name}", name=item.name))
            moved += 1

    log(
        tr("{count} librería(s) movidas a {target}", count=moved, target=disabled)
        if moved else tr("Ya estaba aplicado.")
    )
    return 0


def do_restore_libs(action: dict) -> int:
    params = action.get("params") or {}
    libs = Path(params.get("libs_dir", ""))
    disabled = Path(params.get("disabled_dir", ""))
    if not disabled.is_dir():
        log(tr("No hay librerías apartadas que restaurar."))
        return 0

    restored = 0
    for item in sorted(disabled.iterdir()):
        target = libs / item.name
        if target.exists() or target.is_symlink():
            target.unlink()
        shutil.move(str(item), str(target))
        log(tr("restaurada: {name}", name=item.name))
        restored += 1
    try:
        disabled.rmdir()
    except OSError:
        pass
    log(tr("{count} librería(s) restauradas.", count=restored))
    return 0


def do_chown(action: dict) -> int:
    params = action.get("params") or {}
    uid, gid = int(params.get("uid", -1)), int(params.get("gid", -1))
    if uid < 0 or gid < 0:
        log(tr("Usuario destino inválido."))
        return 2

    touched = 0
    for raw in params.get("paths") or []:
        path = Path(raw)
        if not path.exists():
            continue
        try:
            os.chown(path, uid, gid)
            touched += 1
            for sub in path.rglob("*"):
                try:
                    os.chown(sub, uid, gid, follow_symlinks=False)
                except OSError:
                    pass
            log(tr("propietario corregido: {path}", path=path))
        except OSError as exc:
            log(tr("no pude cambiar {path}: {detail}", path=path, detail=exc))
    log(tr("{count} ruta(s) revisadas para el usuario {user}.",
           count=touched, user=params.get("user", uid)))
    return 0


def do_write_desktop(action: dict) -> int:
    params = action.get("params") or {}
    path = Path(params.get("path", ""))
    content = params.get("content", "")
    if not path.name.endswith(".desktop"):
        log(tr("Ruta de lanzador inválida."))
        return 2
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o644)
        log(tr("lanzador escrito en {path}", path=path))
    except OSError as exc:
        log(tr("no pude escribir el lanzador: {detail}", detail=exc))
        return 1

    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", str(path.parent)],
            capture_output=True,
            check=False,
        )
    return 0


HANDLERS = {
    KIND_EXEC: do_exec,
    KIND_SHIELD_LIBS: do_shield_libs,
    KIND_RESTORE_LIBS: do_restore_libs,
    KIND_CHOWN: do_chown,
    KIND_WRITE_DESKTOP: do_write_desktop,
}


# --------------------------------------------------------------------------
# Bucle principal
# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    global LANG

    if len(argv) != 2:
        emit(t="fatal", message=tr("Uso: root_helper.py <plan.json>"))
        return 2

    try:
        plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        LANG = plan.get("lang") if plan.get("lang") in ("es", "en") else "es"
        actions = [a for a in plan.get("actions", []) if a.get("enabled", True)]
    except (OSError, ValueError) as exc:
        emit(t="fatal", message=tr("No pude leer el plan: {detail}", detail=exc))
        return 2

    # Lista blanca: si el plan trae algo raro, no se toca el sistema.
    for action in actions:
        if action.get("kind", KIND_EXEC) not in ALL_KINDS:
            emit(t="fatal",
                 message=tr("Acción no permitida: {kind}", kind=action.get("kind")))
            return 2

    emit(t="start", total=len(actions))
    failed: list[str] = []

    for index, action in enumerate(actions):
        action_id = action.get("id", f"paso-{index}")
        emit(
            t="step",
            index=index,
            id=action_id,
            title=action.get("title", action_id),
            weight=action.get("weight", 1),
        )
        handler = HANDLERS[action.get("kind", KIND_EXEC)]
        try:
            rc = handler(action)
        except Exception as exc:  # noqa: BLE001 - un paso roto no debe tumbar el resto
            log(tr("error inesperado: {detail}", detail=exc))
            rc = 1

        ok = rc == 0 or action.get("allow_fail", False)
        if not ok:
            failed.append(action_id)
        emit(t="step_done", index=index, id=action_id, rc=rc, ok=ok)

        if not ok:
            emit(t="done", ok=False, failed=failed, stopped_at=action_id)
            return 1

    emit(t="done", ok=True, failed=failed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
