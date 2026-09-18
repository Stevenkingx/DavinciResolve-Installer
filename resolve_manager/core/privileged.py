"""Elevacion de privilegios y ejecución del plan.

Objetivo de diseno: el usuario escribe su contraseña UNA sola vez. Todo el
trabajo que necesita root se manda de golpe al ayudante, que va informando del
progreso mientras trabaja.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..i18n import current as current_language, t
from .plan import Plan

HELPER = Path(__file__).resolve().parent / "root_helper.py"

EventCallback = Callable[[dict], None]
PasswordProvider = Callable[[], str | None]


class PrivilegeError(Exception):
    """No se pudo obtener permisos de administrador."""


def graphical_session() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def escalation_method() -> str:
    """Decide como pedir permisos: directo, pkexec o sudo."""
    if os.geteuid() == 0:
        return "root"
    if shutil.which("pkexec") and graphical_session():
        return "pkexec"
    if shutil.which("sudo"):
        return "sudo"
    return "none"


@dataclass
class RunResult:
    ok: bool
    failed: list[str]
    message: str = ""


class PrivilegedRunner:
    """Lanza el ayudante root y traduce su salida a eventos para la interfaz."""

    def __init__(
        self,
        plan: Plan,
        on_event: EventCallback,
        password_provider: PasswordProvider | None = None,
    ) -> None:
        self.plan = plan
        self.on_event = on_event
        self.password_provider = password_provider
        self._process: subprocess.Popen[str] | None = None
        self._cancelled = False

    # -- ciclo de vida ----------------------------------------------------

    def cancel(self) -> None:
        self._cancelled = True
        process = self._process
        if process and process.poll() is None:
            # El ayudante mata a sus hijos al morir; terminate es suficiente.
            process.terminate()

    # -- preparacion ------------------------------------------------------

    def _write_plan(self, directory: Path) -> Path:
        payload = {
            "lang": current_language(),
            "actions": [a.to_json() for a in self.plan.root_actions()],
        }
        path = directory / "plan.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return path

    def _build_command(self, method: str, plan_path: Path) -> tuple[list[str], bool]:
        """Devuelve (comando, necesita_password_por_stdin)."""
        python = sys.executable or "/usr/bin/python3"
        base = [python, str(HELPER), str(plan_path)]

        if method == "root":
            return base, False
        if method == "pkexec":
            # --disable-internal-agent fuerza el uso del agente gráfico del
            # escritorio, que es el diálogo bonito que el usuario espera.
            return ["pkexec", *base], False
        if method == "sudo":
            return ["sudo", "-S", "-p", "", *base], True
        raise PrivilegeError(t(
            "Este sistema no tiene ni pkexec ni sudo, así que no puedo pedir "
            "permisos de administrador. Ejecuta la aplicación con sudo."
        ))

    # -- ejecución --------------------------------------------------------

    def run(self) -> RunResult:
        actions = self.plan.root_actions()
        if not actions:
            return RunResult(ok=True, failed=[])

        method = escalation_method()
        if method == "none":
            raise PrivilegeError(t(
                "No encuentro forma de pedir permisos de administrador "
                "(ni pkexec ni sudo)."
            ))

        runtime = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
        with tempfile.TemporaryDirectory(prefix="resolve-manager-", dir=runtime) as tmp:
            directory = Path(tmp)
            directory.chmod(stat.S_IRWXU)
            plan_path = self._write_plan(directory)
            argv, needs_password = self._build_command(method, plan_path)

            password = None
            if needs_password and self.password_provider:
                password = self.password_provider()
                if password is None:
                    return RunResult(ok=False, failed=[],
                                     message=t("Cancelado por el usuario."))

            self.on_event({"t": "auth", "method": method})
            return self._stream(argv, password)

    def _stream(self, argv: list[str], password: str | None) -> RunResult:
        try:
            self._process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if password is not None else subprocess.DEVNULL,
                text=True,
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise PrivilegeError(t("No pude lanzar el ayudante:") + f" {exc}") from exc

        process = self._process
        if password is not None and process.stdin:
            try:
                process.stdin.write(password + "\n")
                process.stdin.flush()
                process.stdin.close()
            except OSError:
                pass

        failed: list[str] = []
        ok = False
        saw_done = False

        assert process.stdout is not None
        for raw in process.stdout:
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                # Ruido que no viene del ayudante (avisos de sudo, etc.).
                self.on_event({"t": "log", "line": raw})
                continue

            if event.get("t") == "done":
                saw_done = True
                ok = bool(event.get("ok"))
                failed = list(event.get("failed") or [])
            self.on_event(event)

        rc = process.wait()
        stderr = (process.stderr.read() if process.stderr else "") or ""

        if self._cancelled:
            return RunResult(ok=False, failed=failed, message=t("Operación cancelada."))

        if not saw_done:
            return RunResult(ok=False, failed=failed, message=self._explain(rc, stderr))

        return RunResult(ok=ok, failed=failed)

    @staticmethod
    def _explain(rc: int, stderr: str) -> str:
        """Traduce los fallos de autenticación a lenguaje humano."""
        noise = stderr.strip()
        if rc == 126:
            return t(
                "No se autorizó la operación.\n\n"
                "Se canceló el diálogo de contraseña, o tu usuario no tiene "
                "permisos de administrador en este equipo."
            )
        if rc == 127:
            return t("No encontré pkexec/sudo para elevar privilegios.")
        if "incorrect password" in noise.lower() or "sorry, try again" in noise.lower():
            return t("Contraseña incorrecta.")
        if noise:
            return t("El ayudante falló (código {rc}):", rc=rc) + f"\n{noise[-2000:]}"
        return t("El ayudante terminó inesperadamente (código {rc}).", rc=rc)
