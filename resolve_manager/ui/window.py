"""Ventana principal: mantiene el estado y conecta las pantallas."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, i18n
from ..core import fixes as fixes_mod
from ..core import installer, packages, privileged, state, system
from ..core.archive import ArchiveError, ArchiveInfo
from ..core.archive import inspect as inspect_archive
from ..core.plan import Plan
from ..i18n import t
from . import theme
from .pages import DonePage, HomePage, PlanPage, RepairPage, RunPage
from .widgets import FAIL, OK, RUNNING, app_icon
from .worker import PlanWorker, ScanWorker

PAGE_HOME, PAGE_PLAN, PAGE_RUN, PAGE_DONE, PAGE_REPAIR = range(5)

RESOLVE_BINARY = "/opt/resolve/bin/resolve"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowIcon(app_icon())
        self.resize(920, 900)
        self.setMinimumSize(780, 620)

        # -- estado de la sesión ------------------------------------------
        self.report: system.SystemReport | None = None
        self.info: ArchiveInfo | None = None
        self.plan: Plan | None = None
        self.situation: installer.Situation | None = None
        self.fixes: list[fixes_mod.Fix] = []
        self.workdir: Path = self._default_workdir()
        self.amd_backend = "rocm"
        self.install_nvidia = False
        self.edition = state.preferred_edition() or "free"
        self._overrides: dict[str, bool] = {}
        self.worker: PlanWorker | None = None
        self.scan: ScanWorker | None = None
        self._pending_reboot = False

        self._build_ui()
        self._start_scan()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    @staticmethod
    def _default_workdir() -> Path:
        downloads = Path.home() / "Downloads"
        return downloads if downloads.is_dir() else Path.home()

    def _build_ui(self) -> None:
        self.setWindowTitle(t("DaVinci Resolve Manager"))

        root = QWidget()
        root.setObjectName("Root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header())

        self.stack = QStackedWidget()
        self.home = HomePage(self.edition)
        self.plan_page = PlanPage()
        self.run_page = RunPage()
        self.done_page = DonePage()
        self.repair_page = RepairPage()
        for page in (self.home, self.plan_page, self.run_page,
                     self.done_page, self.repair_page):
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)

        self.setCentralWidget(root)

        # -- conexiones ---------------------------------------------------
        self.home.fileChosen.connect(self.on_file_chosen)
        self.home.repairRequested.connect(self.on_repair_requested)
        self.home.refreshRequested.connect(self._start_scan)
        self.home.editionChanged.connect(self.on_edition_changed)

        self.plan_page.confirmed.connect(self.on_plan_confirmed)
        self.plan_page.cancelled.connect(lambda: self.stack.setCurrentIndex(PAGE_HOME))
        self.plan_page.optionsChanged.connect(self.on_options_changed)

        self.run_page.cancelRequested.connect(self.on_cancel)

        self.done_page.homeRequested.connect(self.on_back_home)
        self.done_page.launchRequested.connect(self.launch_resolve)

        self.repair_page.homeRequested.connect(lambda: self.stack.setCurrentIndex(PAGE_HOME))
        self.repair_page.applyRequested.connect(self.on_apply_fixes)

    def _header(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("Header")
        bar.setFixedHeight(68)
        # El selector por id es imprescindible: sin él, la regla se propaga a
        # las etiquetas hijas y les pinta a cada una su propio borde inferior.
        bar.setStyleSheet(
            f"QFrame#Header {{ background: {theme.SURFACE}; border: none;"
            f" border-bottom: 1px solid {theme.BORDER_SOFT}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(14)

        badge = QLabel()
        badge.setPixmap(app_icon(72).pixmap(36, 36))
        layout.addWidget(badge)

        text = QVBoxLayout()
        text.setSpacing(1)
        title = QLabel("DaVinci Resolve Manager")
        title.setFont(theme.ui_font(12, QFont.Weight.DemiBold))
        text.addWidget(title)
        subtitle = QLabel(t("Instala, actualiza y repara Resolve en Linux"))
        subtitle.setObjectName("Muted")
        text.addWidget(subtitle)
        layout.addLayout(text)

        layout.addStretch(1)

        # Conmutador de idioma
        self._lang_buttons: dict[str, QPushButton] = {}
        for code in ("es", "en"):
            button = QPushButton(code.upper())
            button.setObjectName("LangOn" if code == i18n.current() else "Lang")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(i18n.LANGUAGES[code])
            button.clicked.connect(lambda _checked, c=code: self.change_language(c))
            self._lang_buttons[code] = button
            layout.addWidget(button)

        version = QLabel(f"v{__version__}")
        version.setObjectName("Muted")
        layout.addSpacing(6)
        layout.addWidget(version)
        return bar

    # ------------------------------------------------------------------
    # Idioma
    # ------------------------------------------------------------------

    def change_language(self, code: str) -> None:
        if code == i18n.current():
            return
        if self.worker and self.worker.isRunning():
            self.warn(
                t("Hay una operación en curso"),
                t("Espera a que termine para cambiar de idioma."),
            )
            return

        i18n.set_language(code)
        # Reconstruir es más fiable que ir cambiando textos uno a uno: así no
        # queda ninguna cadena sin traducir por olvido.
        page = self.stack.currentIndex() if hasattr(self, "stack") else PAGE_HOME
        self._build_ui()

        if self.report:
            self.home.set_report(self.report)
        if self.info and page == PAGE_PLAN:
            self._rebuild_plan()
            self.stack.setCurrentIndex(PAGE_PLAN)
        elif page == PAGE_REPAIR and self.report:
            self.on_repair_requested()
        else:
            self.stack.setCurrentIndex(PAGE_HOME)

    # ------------------------------------------------------------------
    # Análisis del equipo
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        self.home.refresh_button.setEnabled(False)
        self.home.refresh_button.setText(t("Analizando…"))
        self.scan = ScanWorker(self)
        self.scan.ready.connect(self._scan_done)
        self.scan.start()

    def _scan_done(self, report: system.SystemReport) -> None:
        self.report = report
        # Por defecto se ofrece la edición que ya está instalada.
        if not state.preferred_edition() and report.resolve.installed:
            self.edition = installer.edition_key(report.resolve.studio)
            self.home.chooser.select(self.edition)
        self.home.set_report(report)
        self.home.refresh_button.setEnabled(True)
        self.home.refresh_button.setText(t("Volver a analizar"))
        self.install_nvidia = False

    # ------------------------------------------------------------------
    # Edición y paquete
    # ------------------------------------------------------------------

    def on_edition_changed(self, key: str) -> None:
        self.edition = key
        state.set_preferred_edition(key)
        if self.info:
            self._rebuild_plan()

    def on_file_chosen(self, path: str) -> None:
        if self.report is None:
            self.warn(t("Espera"), t("Todavía estoy analizando el equipo."))
            return
        try:
            self.info = inspect_archive(path)
        except ArchiveError as exc:
            self.warn(t("No puedo usar ese archivo"), str(exc))
            return

        # El .zip suele estar en su propia carpeta: descomprimir ahí evita
        # copiar 10 GB de una partición a otra.
        source_dir = self.info.source.parent
        if source_dir.is_dir():
            self.workdir = source_dir

        self._overrides = {}
        self.fixes = fixes_mod.detect_fixes(self.report.resolve.installed)
        self._rebuild_plan()
        self.stack.setCurrentIndex(PAGE_PLAN)

    def _offer_nvidia(self) -> bool:
        if not self.report:
            return False
        return (any(g.vendor == "nvidia" for g in self.report.gpus)
                and not self.report.drivers.nvidia_kernel_ok)

    def _rebuild_plan(self) -> None:
        if not (self.info and self.report):
            return
        options = installer.InstallOptions(
            workdir=self.workdir,
            preferred_edition=self.edition,
            deps=packages.DependencyOptions(
                amd_backend=self.amd_backend,
                install_nvidia_driver=self.install_nvidia,
            ),
        )
        self.situation = installer.assess(self.info, self.report)
        self.plan = installer.build_plan(self.info, self.report, self.fixes, options)
        for action in self.plan.actions:
            if action.id in self._overrides:
                action.enabled = self._overrides[action.id]
        self.plan_page.load(
            self.situation, self.plan, self.info,
            self.workdir, self.amd_backend, self._offer_nvidia(),
        )

    def on_options_changed(self) -> None:
        """Un ajuste cambió: hay que recalcular el plan entero."""
        self._overrides = self.plan_page.optional_states()
        self.amd_backend = self.plan_page.amd_backend()
        self.install_nvidia = self.plan_page.install_nvidia()
        self.workdir = self.plan_page.workdir
        # Aplazado: quien emitió la señal es un control que load() va a destruir.
        QTimer.singleShot(0, self._rebuild_plan)

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    def on_plan_confirmed(self) -> None:
        if not self.plan:
            return
        for action in self.plan.actions:
            states = self.plan_page.optional_states()
            if action.id in states:
                action.enabled = states[action.id]

        if self.situation and self.situation.kind == "downgrade":
            if not self.confirm(
                t("Instalar una versión anterior"),
                t("Vas a instalar una versión más antigua que la que tienes.\n\n"
                  "Los proyectos guardados con la versión nueva pueden dejar de "
                  "abrirse. ¿Seguro que quieres continuar?"),
            ):
                return

        self._start_plan(self.plan, info=self.info)

    def on_apply_fixes(self, selected: set, revert: set) -> None:
        if not (selected or revert):
            self.warn(t("Nada que hacer"), t("No has marcado ninguna reparación."))
            return
        plan = installer.build_repair_plan(self.fixes, set(selected), set(revert))
        self._start_plan(plan, info=None)

    def _start_plan(self, plan: Plan, info: ArchiveInfo | None) -> None:
        password = None
        if privileged.escalation_method() == "sudo" and plan.needs_root():
            password = self._ask_password()
            if password is None:
                return

        self._pending_reboot = plan.needs_reboot()
        self.run_page.prepare(plan)
        self.stack.setCurrentIndex(PAGE_RUN)

        self.worker = PlanWorker(plan, info=info, workdir=self.workdir,
                                 password=password, parent=self)
        self.worker.stepStarted.connect(lambda i: self.run_page.steps.set_state(i, RUNNING))
        self.worker.stepFinished.connect(
            lambda i, ok: self.run_page.steps.set_state(i, OK if ok else FAIL)
        )
        self.worker.logLine.connect(self.run_page.log.append)
        self.worker.progressChanged.connect(self.run_page.bar.set_value)
        self.worker.phaseChanged.connect(self.run_page.phase.setText)
        self.worker.authStarted.connect(self._on_auth)
        self.worker.finished_ok.connect(self.on_worker_done)
        self.worker.start()

    def _on_auth(self, method: str) -> None:
        if method == "pkexec":
            self.run_page.hint.setText(t(
                "Confirma la ventana de contraseña del sistema para que pueda "
                "instalar. Es la única vez que te la va a pedir."
            ))

    def _ask_password(self) -> str | None:
        text, ok = QInputDialog.getText(
            self,
            t("Permisos de administrador"),
            t("Escribe tu contraseña de usuario para poder instalar:"),
            QLineEdit.EchoMode.Password,
        )
        return text if ok else None

    def on_cancel(self) -> None:
        if not self.worker:
            return
        if not self.confirm(
            t("Cancelar"),
            t("Si cancelas a medias puede quedar una instalación incompleta.\n\n"
              "¿Cancelar de todas formas?"),
        ):
            return
        self.run_page.cancel_button.setEnabled(False)
        self.run_page.phase.setText(t("Cancelando…"))
        self.worker.cancel()

    def on_worker_done(self, ok: bool, message: str) -> None:
        notes: list[str] = []
        if ok and self._pending_reboot:
            notes.append(t(
                "Se instaló un driver de kernel: reinicia el equipo antes de "
                "abrir DaVinci Resolve."
            ))
        if ok and self.plan:
            notes.extend(self.plan.notes)

        if ok:
            self.done_page.show_result(
                True,
                t("Todo listo"),
                t("{what} está instalado y configurado.", what=message),
                notes=notes,
            )
        else:
            self.done_page.show_result(
                False,
                t("No se pudo completar"),
                message,
                log_text=self.run_page.log.text(),
            )
        self.stack.setCurrentIndex(PAGE_DONE)
        self._start_scan()

    # ------------------------------------------------------------------
    # Reparación
    # ------------------------------------------------------------------

    def on_repair_requested(self) -> None:
        if self.report is None:
            self.warn(t("Espera"), t("Todavía estoy analizando el equipo."))
            return
        self.fixes = fixes_mod.detect_fixes(self.report.resolve.installed)
        self.repair_page.load(self.fixes)
        self.stack.setCurrentIndex(PAGE_REPAIR)

    # ------------------------------------------------------------------
    # Varios
    # ------------------------------------------------------------------

    def on_back_home(self) -> None:
        self.info = None
        self.plan = None
        self.stack.setCurrentIndex(PAGE_HOME)

    def launch_resolve(self) -> None:
        if not Path(RESOLVE_BINARY).exists():
            self.warn(
                t("No encuentro Resolve"),
                t("No existe {path}.", path=RESOLVE_BINARY),
            )
            return
        QProcess.startDetached(RESOLVE_BINARY, [], "/opt/resolve")
        self.showMinimized()

    def warn(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(title)
        box.setInformativeText(text)
        box.setIcon(QMessageBox.Icon.Warning)
        box.exec()

    def confirm(self, title: str, text: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(title)
        box.setInformativeText(text)
        box.setIcon(QMessageBox.Icon.Question)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            if not self.confirm(
                t("Hay una instalación en curso"),
                t("Si cierras ahora puede quedar a medias. ¿Cerrar igualmente?"),
            ):
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()
