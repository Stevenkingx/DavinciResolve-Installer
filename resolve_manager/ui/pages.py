"""Las pantallas de la aplicación.

Flujo: Inicio → Plan → Ejecución → Resultado.
Aparte está la pantalla de Reparación, accesible desde Inicio.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.archive import ArchiveInfo
from ..core.fixes import STATUS_APPLIED, STATUS_NEEDED, Fix
from ..core.installer import DOWNLOAD_URL, Situation, editions
from ..core.plan import Plan
from ..core.system import SystemReport
from ..i18n import t
from . import theme
from .widgets import (
    FAIL,
    INFO,
    OK,
    PENDING,
    DropZone,
    LogPane,
    ProgressBar,
    ResultMark,
    StatCard,
    StepList,
    section_title,
    separator,
)


def scrollable(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(inner)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return area


def note_box(text: str, kind: str = "info") -> QFrame:
    """Recuadro de aviso con una franja de color a la izquierda."""
    colors = {
        "info": (theme.INFO, theme.INFO_SOFT),
        "warn": (theme.WARN, theme.WARN_SOFT),
        "error": (theme.DANGER, theme.DANGER_SOFT),
        "ok": (theme.OK, theme.OK_SOFT),
    }
    accent, background = colors.get(kind, colors["info"])

    frame = QFrame()
    frame.setObjectName("NoteBox")
    frame.setStyleSheet(
        f"QFrame#NoteBox {{ background: {background}; border: none;"
        f" border-radius: 8px; }}"
    )
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 11, 14, 11)
    layout.setSpacing(12)

    stripe = QFrame()
    stripe.setObjectName("NoteStripe")
    stripe.setFixedWidth(3)
    stripe.setStyleSheet(
        f"QFrame#NoteStripe {{ background: {accent}; border: none; border-radius: 1px; }}"
    )
    stripe.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    layout.addWidget(stripe)

    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {theme.TEXT}; font-size: 12.5px; background: transparent;")
    layout.addWidget(label, 1)
    return frame


def clear_layout(layout) -> None:
    """Vacía un layout de forma inmediata.

    deleteLater() por sí solo no basta: hasta que el bucle de eventos recoge el
    widget, este sigue siendo hijo del contenedor y se dibuja encima de lo que
    acabamos de crear. setParent(None) lo quita de la pantalla ya.
    """
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout():
            clear_layout(item.layout())
            item.layout().deleteLater()


# ==========================================================================
# Selector de edición
# ==========================================================================

class EditionChooser(QWidget):
    """Elegir entre la edición gratuita y Studio, con lo que implica cada una."""

    editionChanged = pyqtSignal(str)

    def __init__(self, selected: str = "free", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected = selected if selected in ("free", "studio") else "free"
        self._cards: dict[str, QFrame] = {}
        self._radios: dict[str, QRadioButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(12)
        group = QButtonGroup(self)
        for key, edition in editions().items():
            card = self._build_card(key, edition, group)
            self._cards[key] = card
            row.addWidget(card, 1)
        layout.addLayout(row)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        ask = QLabel(t("¿Todavía no lo has descargado?"))
        ask.setObjectName("Muted")
        footer.addWidget(ask)

        link = QPushButton(t("Descargar de Blackmagic Design"))
        link.setObjectName("Link")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DOWNLOAD_URL)))
        footer.addWidget(link)
        footer.addStretch(1)
        layout.addLayout(footer)

        self._refresh()

    def _build_card(self, key: str, edition, group: QButtonGroup) -> QFrame:
        card = QFrame()
        card.setObjectName("CardPick")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        # Pulsar en cualquier punto de la tarjeta la selecciona, no solo el círculo.
        card.mousePressEvent = lambda _event, k=key: self.select(k)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(9)
        radio = QRadioButton()
        radio.setChecked(key == self._selected)
        radio.toggled.connect(lambda checked, k=key: checked and self.select(k))
        group.addButton(radio)
        self._radios[key] = radio
        top.addWidget(radio)

        name = QLabel(edition.name)
        name.setObjectName("PickName")
        top.addWidget(name)
        top.addStretch(1)
        layout.addLayout(top)

        summary = QLabel(edition.summary)
        summary.setObjectName("PickSummary")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        detail = QLabel(edition.detail)
        detail.setObjectName("Detail")
        detail.setWordWrap(True)
        layout.addWidget(detail)

        hint = QLabel(edition.file_hint)
        hint.setObjectName("PickHint")
        hint.setFont(theme.mono_font(8))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return card

    def select(self, key: str) -> None:
        if key not in self._cards or key == self._selected:
            if key in self._radios:
                self._radios[key].setChecked(True)
            return
        self._selected = key
        self._radios[key].setChecked(True)
        self._refresh()
        self.editionChanged.emit(key)

    def selected(self) -> str:
        return self._selected

    def _refresh(self) -> None:
        for key, card in self._cards.items():
            card.setObjectName("CardPickOn" if key == self._selected else "CardPick")
            # Qt solo relee la hoja de estilos si se le pide explícitamente.
            card.style().unpolish(card)
            card.style().polish(card)


# ==========================================================================
# Inicio
# ==========================================================================

class HomePage(QWidget):
    fileChosen = pyqtSignal(str)
    repairRequested = pyqtSignal()
    refreshRequested = pyqtSignal()
    editionChanged = pyqtSignal(str)

    def __init__(self, edition: str = "free", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._report: SystemReport | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(18)

        layout.addWidget(section_title(t("Estado de tu equipo")))

        grid = QGridLayout()
        grid.setSpacing(12)
        self.card_system = StatCard(t("Sistema"), "-", INFO)
        self.card_gpu = StatCard(t("Tarjeta gráfica"), "-", INFO)
        self.card_driver = StatCard(t("Driver y cómputo"), "-", INFO)
        self.card_resolve = StatCard(t("DaVinci Resolve"), "-", INFO)
        for index, card in enumerate(
            (self.card_system, self.card_gpu, self.card_driver, self.card_resolve)
        ):
            grid.addWidget(card, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.alert_holder = QVBoxLayout()
        self.alert_holder.setSpacing(8)
        layout.addLayout(self.alert_holder)

        layout.addSpacing(2)
        layout.addWidget(section_title(t("Qué edición quieres")))
        self.chooser = EditionChooser(edition)
        self.chooser.editionChanged.connect(self._on_edition)
        layout.addWidget(self.chooser)

        layout.addWidget(section_title(t("Instalar o actualizar")))
        self.drop = DropZone()
        self.drop.setMaximumHeight(210)
        self.drop.fileSelected.connect(self.fileChosen)
        layout.addWidget(self.drop, 1)

        self.hint = QLabel()
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        layout.addWidget(separator())

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.repair_button = QPushButton(t("Revisar y reparar instalación"))
        self.repair_button.clicked.connect(self.repairRequested)
        actions.addWidget(self.repair_button)

        self.refresh_button = QPushButton(t("Volver a analizar"))
        self.refresh_button.setObjectName("Ghost")
        self.refresh_button.setMinimumWidth(160)
        self.refresh_button.clicked.connect(self.refreshRequested)
        actions.addWidget(self.refresh_button)

        actions.addStretch(1)
        self.copy_button = QPushButton(t("Copiar diagnóstico"))
        self.copy_button.setObjectName("Ghost")
        self.copy_button.clicked.connect(self._copy_diagnostics)
        actions.addWidget(self.copy_button)
        layout.addLayout(actions)

        outer.addWidget(scrollable(body))
        self._on_edition(self.chooser.selected(), emit=False)

    # -- edición ----------------------------------------------------------

    def _on_edition(self, key: str, emit: bool = True) -> None:
        edition = editions()[key]
        self.drop.set_text(
            t("Arrastra aquí {file}", file=edition.file_hint),
            t("o pulsa para buscarlo en tu equipo"),
        )
        self.hint.setText(t(
            "Descarga el paquete de Linux desde blackmagicdesign.com y suéltalo "
            "aquí sin descomprimir. Sirve tanto para instalar por primera vez "
            "como para actualizar: tus proyectos no se tocan."
        ))
        if emit:
            self.editionChanged.emit(key)

    def edition(self) -> str:
        return self.chooser.selected()

    # -- datos ------------------------------------------------------------

    def set_report(self, report: SystemReport) -> None:
        self._report = report

        distro = report.distro
        self.card_system.update_card(
            distro.pretty,
            OK if distro.supported else INFO,
            "" if distro.supported else t(
                "Distribución no reconocida: instalaré Resolve, pero las "
                "dependencias tendrás que ponerlas tú."
            ),
        )

        if report.gpus:
            names = [g.name for g in report.gpus]
            extra = t("También detecté: {others}", others=", ".join(names[1:])) \
                if len(names) > 1 else ""
            self.card_gpu.update_card(names[0], OK, extra)
        else:
            self.card_gpu.update_card(
                t("No detectada"), FAIL,
                t("No pude leer las tarjetas con lspci. Instala «pciutils»."),
            )

        self.card_driver.update_card(*self._driver_summary(report))

        resolve = report.resolve
        self.card_resolve.update_card(
            resolve.label,
            OK if resolve.installed else PENDING,
            "" if resolve.installed else t("Suelta el paquete abajo para instalarlo."),
        )
        self._rebuild_alerts(report)

    @staticmethod
    def _driver_summary(report: SystemReport) -> tuple[str, str, str]:
        drivers = report.drivers
        has_nvidia = any(g.vendor == "nvidia" for g in report.gpus)
        has_amd = any(g.vendor == "amd" for g in report.gpus)

        parts: list[str] = []
        if has_nvidia:
            parts.append(
                f"NVIDIA {drivers.nvidia_driver}" if drivers.nvidia_driver
                else t("NVIDIA sin driver")
            )
        if has_amd:
            parts.append("ROCm" if drivers.rocm_present else t("Radeon sin ROCm"))

        platforms = ", ".join(drivers.opencl_platforms) or t("sin OpenCL")
        value = " · ".join(parts) if parts else platforms

        if has_nvidia and not drivers.nvidia_kernel_ok:
            return value, FAIL, t(
                "El driver de NVIDIA no responde: Resolve no va a acelerar."
            )
        if not drivers.opencl_ok:
            return value, FAIL, t(
                "Sin OpenCL, Resolve se quejará de la GPU al abrir proyectos."
            )
        return value, OK, t("OpenCL activo: {platforms}", platforms=platforms)

    def _rebuild_alerts(self, report: SystemReport) -> None:
        clear_layout(self.alert_holder)
        drivers = report.drivers

        if any(g.vendor == "nvidia" for g in report.gpus) and not drivers.nvidia_kernel_ok:
            self.alert_holder.addWidget(note_box(t(
                "Tienes una NVIDIA sin driver propietario activo. Es la causa "
                "número uno de que Resolve no arranque. Puedo instalarlo durante "
                "la instalación, o desde «Revisar y reparar»."
            ), "warn"))

        if not drivers.opencl_ok:
            self.alert_holder.addWidget(note_box(t(
                "No hay ninguna plataforma OpenCL activa en este equipo. Resolve "
                "necesita OpenCL (o CUDA) para funcionar."
            ), "warn"))

    def _copy_diagnostics(self) -> None:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        if not self._report:
            return
        QApplication.clipboard().setText(self._report.as_text())
        self.copy_button.setText(t("Copiado"))
        QTimer.singleShot(1600, lambda: self.copy_button.setText(t("Copiar diagnóstico")))


# ==========================================================================
# Plan
# ==========================================================================

class PlanPage(QWidget):
    confirmed = pyqtSignal()
    cancelled = pyqtSignal()
    optionsChanged = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checkboxes: dict[str, QCheckBox] = {}
        self.workdir: Path = Path.home() / "Downloads"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(16)

        self.headline = QLabel()
        self.headline.setObjectName("Title")
        self.headline.setWordWrap(True)
        layout.addWidget(self.headline)

        self.detail = QLabel()
        self.detail.setObjectName("Subtitle")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

        self.alerts = QVBoxLayout()
        self.alerts.setSpacing(8)
        layout.addLayout(self.alerts)

        layout.addWidget(section_title(t("Qué voy a hacer")))
        self.steps_holder = QVBoxLayout()
        self.steps_holder.setSpacing(4)
        layout.addLayout(self.steps_holder)

        layout.addWidget(separator())
        layout.addWidget(section_title(t("Ajustes")))
        self.settings_holder = QVBoxLayout()
        self.settings_holder.setSpacing(10)
        layout.addLayout(self.settings_holder)

        layout.addStretch(1)
        outer.addWidget(scrollable(body))

        footer = QHBoxLayout()
        footer.setContentsMargins(28, 12, 28, 18)
        footer.setSpacing(10)
        back = QPushButton(t("Atrás"))
        back.setObjectName("Ghost")
        back.clicked.connect(self.cancelled)
        footer.addWidget(back)
        footer.addStretch(1)
        self.go_button = QPushButton(t("Empezar"))
        self.go_button.setObjectName("Primary")
        self.go_button.clicked.connect(self.confirmed)
        footer.addWidget(self.go_button)
        outer.addLayout(footer)

    # -- contenido --------------------------------------------------------

    def load(self, situation: Situation, plan: Plan, info: ArchiveInfo,
             workdir: Path, amd_backend: str, offer_nvidia: bool) -> None:
        self.headline.setText(situation.headline)
        self.detail.setText(situation.detail)
        self.workdir = workdir

        clear_layout(self.alerts)
        for blocker in plan.blockers:
            self.alerts.addWidget(note_box(blocker, "error"))
        for note in plan.notes:
            self.alerts.addWidget(note_box(note, "warn"))

        clear_layout(self.steps_holder)
        self._checkboxes.clear()
        for action in plan.actions:
            self.steps_holder.addWidget(self._step_widget(action))

        clear_layout(self.settings_holder)
        self._build_settings(amd_backend, offer_nvidia)

        blocked = bool(plan.blockers)
        self.go_button.setEnabled(not blocked)
        self.go_button.setText(t("No se puede continuar") if blocked else t("Empezar"))

    def _step_widget(self, action) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)
        if action.optional:
            box = QCheckBox(action.title)
            box.setChecked(action.enabled)
            # Marcar o desmarcar solo activa esa acción: reconstruir el plan
            # aquí borraría la casilla en plena señal.
            box.toggled.connect(lambda checked, a=action: setattr(a, "enabled", checked))
            self._checkboxes[action.id] = box
            top.addWidget(box, 1)
        else:
            title = QLabel(action.title)
            title.setFont(theme.ui_font(10, QFont.Weight.DemiBold))
            title.setWordWrap(True)
            top.addWidget(title, 1)

            tag = QLabel(t("necesario"))
            tag.setStyleSheet(
                f"color: {theme.TEXT_FAINT}; font-size: 10px; background: transparent;"
            )
            top.addWidget(tag, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        if action.detail:
            detail = QLabel(action.detail)
            detail.setObjectName("Detail")
            detail.setWordWrap(True)
            layout.addWidget(detail)
        return frame

    def _build_settings(self, amd_backend: str, offer_nvidia: bool) -> None:
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(t("Carpeta de trabajo para descomprimir:"))
        label.setObjectName("Muted")
        row.addWidget(label)
        self.workdir_label = QLabel(str(self.workdir))
        self.workdir_label.setStyleSheet(f"color: {theme.TEXT}; font-size: 12px;")
        row.addWidget(self.workdir_label, 1)
        change = QPushButton(t("Cambiar"))
        change.setObjectName("Ghost")
        change.clicked.connect(self._pick_workdir)
        row.addWidget(change)
        self.settings_holder.addLayout(row)

        self.amd_group = QButtonGroup(self)
        self.amd_rocm = QRadioButton(t("ROCm (recomendado para Radeon dedicadas)"))
        self.amd_mesa = QRadioButton(t("OpenCL de Mesa (más ligero, bueno para APU integradas)"))
        self.amd_rocm.setChecked(amd_backend == "rocm")
        self.amd_mesa.setChecked(amd_backend != "rocm")
        self.amd_group.addButton(self.amd_rocm)
        self.amd_group.addButton(self.amd_mesa)
        self.amd_rocm.toggled.connect(self.optionsChanged)

        amd_box = QVBoxLayout()
        amd_box.setSpacing(4)
        amd_label = QLabel(t("Cómputo para GPU AMD:"))
        amd_label.setObjectName("Muted")
        amd_box.addWidget(amd_label)
        amd_box.addWidget(self.amd_rocm)
        amd_box.addWidget(self.amd_mesa)
        self.settings_holder.addLayout(amd_box)

        self.nvidia_box = QCheckBox(t("Instalar también el driver propietario de NVIDIA"))
        self.nvidia_box.setVisible(offer_nvidia)
        self.nvidia_box.toggled.connect(self.optionsChanged)
        self.settings_holder.addWidget(self.nvidia_box)
        if offer_nvidia:
            warn = QLabel(t("Requiere reiniciar el equipo al terminar."))
            warn.setObjectName("Muted")
            self.settings_holder.addWidget(warn)

    def _pick_workdir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, t("Carpeta donde descomprimir el instalador"), str(self.workdir)
        )
        if chosen:
            self.workdir = Path(chosen)
            self.workdir_label.setText(chosen)
            self.optionsChanged.emit()

    # -- lectura de opciones ----------------------------------------------

    def optional_states(self) -> dict[str, bool]:
        return {key: box.isChecked() for key, box in self._checkboxes.items()}

    def amd_backend(self) -> str:
        return "rocm" if self.amd_rocm.isChecked() else "mesa"

    def install_nvidia(self) -> bool:
        return self.nvidia_box.isChecked()


# ==========================================================================
# Ejecución
# ==========================================================================

class RunPage(QWidget):
    cancelRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        self.phase = QLabel(t("Preparando"))
        self.phase.setObjectName("Title")
        self.phase.setWordWrap(True)
        layout.addWidget(self.phase)

        self.hint = QLabel(t(
            "Puedes dejar esto trabajando. El paso más largo es descomprimir el "
            "instalador: son más de 10 GB."
        ))
        self.hint.setObjectName("Subtitle")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.bar = ProgressBar()
        layout.addWidget(self.bar)

        steps_card = QFrame()
        steps_card.setObjectName("Card")
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setContentsMargins(16, 10, 16, 10)
        self.steps = StepList()
        steps_layout.addWidget(self.steps)
        layout.addWidget(scrollable(steps_card), 1)

        self.log = LogPane()
        layout.addWidget(self.log)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.cancel_button = QPushButton(t("Cancelar"))
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.clicked.connect(self.cancelRequested)
        footer.addWidget(self.cancel_button)
        layout.addLayout(footer)

    def prepare(self, plan: Plan) -> None:
        self.steps.clear()
        self.log.clear()
        self.bar.set_value(0.0)
        self.phase.setText(t("Preparando"))
        self.cancel_button.setEnabled(True)
        for action in plan.active():
            self.steps.add_step(action.id, action.title)


# ==========================================================================
# Resultado
# ==========================================================================

class DonePage(QWidget):
    launchRequested = pyqtSignal()
    homeRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 28)
        layout.setSpacing(16)
        layout.addStretch(2)

        mark_row = QHBoxLayout()
        mark_row.addStretch(1)
        self.mark = ResultMark()
        mark_row.addWidget(self.mark)
        mark_row.addStretch(1)
        layout.addLayout(mark_row)

        self.title = QLabel()
        self.title.setObjectName("Title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        self.message = QLabel()
        self.message.setObjectName("Subtitle")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.extra = QVBoxLayout()
        self.extra.setSpacing(8)
        layout.addLayout(self.extra)
        layout.addStretch(3)

        self.log = LogPane()
        layout.addWidget(self.log)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)
        self.home_button = QPushButton(t("Volver al inicio"))
        self.home_button.setObjectName("Ghost")
        self.home_button.clicked.connect(self.homeRequested)
        buttons.addWidget(self.home_button)
        self.launch_button = QPushButton(t("Abrir DaVinci Resolve"))
        self.launch_button.setObjectName("Primary")
        self.launch_button.clicked.connect(self.launchRequested)
        buttons.addWidget(self.launch_button)
        layout.addLayout(buttons)

    def show_result(self, ok: bool, title: str, message: str,
                    log_text: str = "", notes: list[str] | None = None) -> None:
        self.mark.set_ok(ok)
        self.title.setText(title)
        self.message.setText(message)
        self.launch_button.setVisible(ok)

        clear_layout(self.extra)
        for note in notes or []:
            self.extra.addWidget(note_box(note, "warn"))

        self.log.clear()
        if log_text:
            self.log.append(log_text)
        if not ok:
            self.log.toggle.setChecked(True)
            self.log.set_expanded(True)


# ==========================================================================
# Reparación
# ==========================================================================

class RepairPage(QWidget):
    applyRequested = pyqtSignal(set, set)   # aplicar, revertir
    homeRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[Fix, QCheckBox, QCheckBox]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(14)

        title = QLabel(t("Revisar y reparar"))
        title.setObjectName("Title")
        layout.addWidget(title)

        subtitle = QLabel(t(
            "Estos son los arreglos conocidos que hacen que DaVinci Resolve "
            "funcione bien en Linux. Marco solos los que hacen falta en tu equipo."
        ))
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.holder = QVBoxLayout()
        self.holder.setSpacing(10)
        layout.addLayout(self.holder)
        layout.addStretch(1)
        outer.addWidget(scrollable(body))

        footer = QHBoxLayout()
        footer.setContentsMargins(28, 12, 28, 18)
        footer.setSpacing(10)
        back = QPushButton(t("Atrás"))
        back.setObjectName("Ghost")
        back.clicked.connect(self.homeRequested)
        footer.addWidget(back)
        footer.addStretch(1)
        self.apply_button = QPushButton(t("Aplicar seleccionados"))
        self.apply_button.setObjectName("Primary")
        self.apply_button.clicked.connect(self._emit_apply)
        footer.addWidget(self.apply_button)
        outer.addLayout(footer)

    def load(self, fixes: list[Fix]) -> None:
        clear_layout(self.holder)
        self._rows.clear()

        labels = {
            STATUS_NEEDED: (t("hace falta"), theme.WARN),
            STATUS_APPLIED: (t("ya aplicado"), theme.OK),
        }

        for fix in fixes:
            frame = QFrame()
            frame.setObjectName("Card")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(16, 13, 16, 13)
            layout.setSpacing(6)

            top = QHBoxLayout()
            apply_box = QCheckBox(fix.title)
            apply_box.setChecked(fix.pending)
            apply_box.setEnabled(fix.pending)
            top.addWidget(apply_box, 1)

            text, color = labels.get(fix.status, (t("no aplica"), theme.TEXT_FAINT))
            status = QLabel(text)
            status.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")
            top.addWidget(status, 0, Qt.AlignmentFlag.AlignTop)
            layout.addLayout(top)

            detail = QLabel(fix.detail)
            detail.setObjectName("Detail")
            detail.setWordWrap(True)
            layout.addWidget(detail)

            revert_box = QCheckBox(t("Deshacer este arreglo"))
            revert_box.setVisible(fix.revertible and fix.status == STATUS_APPLIED)
            layout.addWidget(revert_box)

            if fix.evidence:
                evidence = QLabel(
                    t("Afecta a: {items}", items=", ".join(fix.evidence[:6]))
                )
                evidence.setObjectName("Muted")
                evidence.setWordWrap(True)
                layout.addWidget(evidence)

            self.holder.addWidget(frame)
            self._rows.append((fix, apply_box, revert_box))

    def _emit_apply(self) -> None:
        selected = {f.id for f, box, _ in self._rows if box.isChecked() and box.isEnabled()}
        revert = {f.id for f, _, box in self._rows if box.isVisible() and box.isChecked()}
        self.applyRequested.emit(selected, revert)
