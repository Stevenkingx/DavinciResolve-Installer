"""Hilo de trabajo: descomprime y ejecuta el plan sin congelar la ventana."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ..core import archive, state, system
from ..i18n import t
from ..core.archive import ArchiveError, ArchiveInfo
from ..core.plan import KIND_EXTRACT, Plan
from ..core.privileged import PrivilegeError, PrivilegedRunner


class PlanWorker(QThread):
    """Ejecuta un plan completo e informa del avance paso a paso."""

    stepStarted = pyqtSignal(str)             # id del paso
    stepFinished = pyqtSignal(str, bool)      # id, correcto
    logLine = pyqtSignal(str)
    progressChanged = pyqtSignal(float)       # 0.0 .. 1.0
    phaseChanged = pyqtSignal(str)            # texto grande de estado
    authStarted = pyqtSignal(str)             # metodo de elevación
    finished_ok = pyqtSignal(bool, str)       # correcto, mensaje

    def __init__(
        self,
        plan: Plan,
        info: ArchiveInfo | None = None,
        workdir: Path | None = None,
        password: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.plan = plan
        self.info = info
        self.workdir = workdir or Path.home()
        self.password = password
        self.run_path: Path | None = None
        self._cancelled = False
        self._runner: PrivilegedRunner | None = None
        self._done_weight = 0.0
        self._total_weight = float(plan.total_weight())
        self._current: str = ""

    # -- control ----------------------------------------------------------

    def cancel(self) -> None:
        self._cancelled = True
        if self._runner:
            self._runner.cancel()

    # -- progreso ---------------------------------------------------------

    def _emit_progress(self, partial: float = 0.0) -> None:
        value = (self._done_weight + partial) / max(self._total_weight, 1.0)
        self.progressChanged.emit(max(0.0, min(1.0, value)))

    def _weight_of(self, action_id: str) -> float:
        for action in self.plan.active():
            if action.id == action_id:
                return float(action.weight)
        return 1.0

    # -- ejecución --------------------------------------------------------

    def run(self) -> None:  # noqa: D102 - QThread
        try:
            if not self._extract():
                return
            if not self._run_privileged():
                return
        except ArchiveError as exc:
            self.finished_ok.emit(False, str(exc))
            return
        except PrivilegeError as exc:
            self.finished_ok.emit(False, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - la UI debe enterarse de todo
            self.finished_ok.emit(False, t("Error inesperado:") + f" {exc}")
            return

        self.phaseChanged.emit(t("Comprobando el resultado"))
        self.progressChanged.emit(1.0)

        installed = system.detect_resolve()
        instalaba = any(a.id == "resolve-install" for a in self.plan.active())

        if not instalaba:
            # Fue un plan de reparación: no hay versión nueva que anunciar.
            self.finished_ok.emit(
                True, installed.label if installed.installed else t("Tu sistema")
            )
        elif installed.installed:
            # Welcome.txt no distingue Studio: hay que recordarlo nosotros.
            if self.info is not None:
                state.record_install(self.info.version or installed.version,
                                     self.info.studio)
                installed = system.detect_resolve()
            self.finished_ok.emit(True, installed.label)
        else:
            self.finished_ok.emit(False, t(
                "Los pasos terminaron sin error, pero no encuentro DaVinci Resolve "
                "en /opt/resolve. Revisa los detalles técnicos."
            ))

    def _extract(self) -> bool:
        step = next((a for a in self.plan.active() if a.kind == KIND_EXTRACT), None)
        if step is None:
            self.run_path = self.info.source if self.info else None
            return True
        if self.info is None:
            self.finished_ok.emit(False, t("No hay ningún paquete que descomprimir."))
            return False

        self.stepStarted.emit(step.id)
        self.phaseChanged.emit(t("Descomprimiendo el instalador"))
        weight = float(step.weight)

        last = [-1]

        def on_progress(done: int, total: int) -> None:
            fraction = done / total if total else 0.0
            self._emit_progress(weight * fraction)
            percent = int(fraction * 100)
            if percent != last[0] and percent % 5 == 0:
                last[0] = percent
                gb = done / (1024 ** 3)
                self.logLine.emit(t("descomprimiendo… {percent}%  ({gb} GB)",
                                    percent=percent, gb=f"{gb:.1f}"))

        try:
            self.run_path = archive.extract_run(
                self.info, self.workdir, on_progress, lambda: self._cancelled
            )
        except ArchiveError as exc:
            self.stepFinished.emit(step.id, False)
            self.finished_ok.emit(False, str(exc))
            return False

        self._done_weight += weight
        self._emit_progress()
        self.stepFinished.emit(step.id, True)
        self.logLine.emit(t("instalador listo en {path}", path=self.run_path))
        return True

    def _run_privileged(self) -> bool:
        if self._cancelled:
            self.finished_ok.emit(False, t("Operación cancelada."))
            return False

        # Ahora que existe el .run, se completa el comando del instalador.
        if self.run_path:
            for action in self.plan.actions:
                if action.id in ("resolve-install", "resolve-uninstall") and action.argv:
                    action.argv[0] = str(self.run_path)

        if not self.plan.root_actions():
            return True

        self.phaseChanged.emit(t("Pidiendo permisos de administrador"))
        self._runner = PrivilegedRunner(self.plan, self._on_event, lambda: self.password)
        result = self._runner.run()

        if not result.ok:
            message = result.message or (
                t("Fallo en:") + " " + ", ".join(result.failed) if result.failed
                else t("La instalación no pudo completarse.")
            )
            self.finished_ok.emit(False, message)
            return False
        return True

    def _on_event(self, event: dict) -> None:
        kind = event.get("t")

        if kind == "auth":
            self.authStarted.emit(str(event.get("method", "")))
            self.phaseChanged.emit(t("Esperando tu autorización"))
        elif kind == "log":
            self.logLine.emit(str(event.get("line", "")))
        elif kind == "step":
            self._current = str(event.get("id", ""))
            self.stepStarted.emit(self._current)
            self.phaseChanged.emit(str(event.get("title") or t("Trabajando")))
        elif kind == "step_done":
            action_id = str(event.get("id", self._current))
            ok = bool(event.get("ok"))
            self._done_weight += self._weight_of(action_id)
            self._emit_progress()
            self.stepFinished.emit(action_id, ok)
        elif kind == "fatal":
            self.logLine.emit(f"ERROR: {event.get('message', '')}")


class ScanWorker(QThread):
    """Analiza el equipo en segundo plano para que la ventana abra al instante."""

    ready = pyqtSignal(object)   # SystemReport

    def run(self) -> None:  # noqa: D102 - QThread
        self.ready.emit(system.collect())
