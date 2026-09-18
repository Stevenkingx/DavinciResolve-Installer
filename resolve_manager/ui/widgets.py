"""Widgets propios: zona de arrastre, tarjetas, lista de pasos y barra.

Casi todo se pinta a mano con QPainter en lugar de usar los controles de serie,
para que la aplicación tenga cara propia y se vea nitida en pantallas HiDPI.
"""

from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..i18n import t
from . import theme

# Estados posibles de un paso o de una tarjeta.
PENDING, RUNNING, OK, FAIL, SKIP, INFO = "pending", "running", "ok", "fail", "skip", "info"

STATE_COLORS = {
    PENDING: theme.TEXT_FAINT,
    RUNNING: theme.ACCENT,
    OK: theme.OK,
    FAIL: theme.DANGER,
    SKIP: theme.TEXT_FAINT,
    INFO: theme.INFO,
}


# --------------------------------------------------------------------------
# Icono de la aplicación: rueda de color, dibujada en vez de incrustada
# --------------------------------------------------------------------------

def app_icon(size: int = 128) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.08
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

    path = QPainterPath()
    path.addRoundedRect(rect, size * 0.22, size * 0.22)
    painter.fillPath(path, QColor("#1B1E25"))

    center = rect.center()
    radius = rect.width() * 0.30
    gradient = QConicalGradient(center, 90)
    for stop, color in ((0.0, "#FFB53F"), (0.33, "#F87171"), (0.66, "#60A5FA"), (1.0, "#FFB53F")):
        gradient.setColorAt(stop, QColor(color))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(center, radius, radius)

    painter.setBrush(QColor("#1B1E25"))
    painter.drawEllipse(center, radius * 0.42, radius * 0.42)
    painter.end()
    return QIcon(pixmap)


# --------------------------------------------------------------------------
# Zona de arrastre
# --------------------------------------------------------------------------

class DropZone(QFrame):
    """Recuadro donde el usuario suelta el .zip descargado de Blackmagic."""

    fileSelected = pyqtSignal(str)

    ACCEPTED = (".zip", ".run")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(190)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._hover = False       # raton encima
        self._dragging = False    # hay un archivo sobrevolando
        self._title = t("Arrastra aquí el archivo de DaVinci Resolve")
        self._subtitle = t("el .zip que descargaste de Blackmagic  ·  o pulsa para buscarlo")

    # -- apariencia -------------------------------------------------------

    def set_text(self, title: str, subtitle: str) -> None:
        self._title, self._subtitle = title, subtitle
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        if self._dragging:
            border, fill, glyph = theme.ACCENT, QColor(theme.ACCENT_SOFT), theme.ACCENT
        elif self._hover:
            border, fill, glyph = QColor("#3D4454"), QColor(theme.SURFACE_2), theme.TEXT_MUTED
        else:
            border, fill, glyph = QColor(theme.BORDER), QColor(theme.SURFACE), theme.TEXT_FAINT

        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, fill)

        pen = QPen(QColor(border), 2 if self._dragging else 1.4)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 5])
        painter.setPen(pen)
        painter.drawPath(path)

        # Glifo: una caja con una flecha entrando.
        cx = rect.center().x()
        top = rect.center().y() - 46
        painter.setPen(QPen(QColor(glyph), 2.2, cap=Qt.PenCapStyle.RoundCap,
                            join=Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(cx, top), QPointF(cx, top + 30))
        painter.drawLine(QPointF(cx - 9, top + 21), QPointF(cx, top + 30))
        painter.drawLine(QPointF(cx + 9, top + 21), QPointF(cx, top + 30))
        painter.drawPath(self._tray_path(cx, top + 38))

        painter.setPen(QColor(theme.TEXT if (self._hover or self._dragging) else theme.TEXT_MUTED))
        font = theme.ui_font(12, QFont.Weight.DemiBold)
        painter.setFont(font)
        title_rect = QRectF(rect.left(), rect.center().y() + 14, rect.width(), 26)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self._title)

        painter.setPen(QColor(theme.TEXT_FAINT))
        painter.setFont(theme.ui_font(9))
        sub_rect = QRectF(rect.left(), rect.center().y() + 40, rect.width(), 22)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self._subtitle)
        painter.end()

    @staticmethod
    def _tray_path(cx: float, y: float) -> QPainterPath:
        """Bandeja abierta bajo la flecha."""
        path = QPainterPath()
        path.moveTo(cx - 22, y - 6)
        path.lineTo(cx - 22, y + 6)
        path.lineTo(cx + 22, y + 6)
        path.lineTo(cx + 22, y - 6)
        return path

    # -- interaccion ------------------------------------------------------

    def _acceptable(self, path: str) -> bool:
        return path.lower().endswith(self.ACCEPTED)

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if urls and self._acceptable(urls[0].toLocalFile()):
            self._dragging = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._dragging = False
        self.update()

    def dropEvent(self, event) -> None:
        self._dragging = False
        self.update()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if self._acceptable(path):
                self.fileSelected.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse()
        super().mouseReleaseEvent(event)

    def browse(self) -> None:
        start = str(Path.home() / "Downloads")
        if not Path(start).is_dir():
            start = str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("Elige el paquete de DaVinci Resolve"),
            start,
            t("Paquete de Resolve (*.zip *.run);;Todos los archivos (*)"),
        )
        if path:
            self.fileSelected.emit(path)


# --------------------------------------------------------------------------
# Tarjeta de estado
# --------------------------------------------------------------------------

class StatCard(QFrame):
    """Tarjeta pequeña: etiqueta, valor y un punto de color con el estado."""

    def __init__(self, label: str, value: str = "-", state: str = INFO,
                 hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._dot = _Dot(state)
        self._label = QLabel(label.upper())
        self._label.setObjectName("CardLabel")
        top.addWidget(self._dot)
        top.addWidget(self._label)
        top.addStretch(1)
        layout.addLayout(top)

        self._value = QLabel(value)
        self._value.setObjectName("CardValue")
        self._value.setWordWrap(True)
        layout.addWidget(self._value)

        self._hint = QLabel(hint)
        self._hint.setObjectName("Muted")
        self._hint.setWordWrap(True)
        self._hint.setVisible(bool(hint))
        layout.addWidget(self._hint)

    def update_card(self, value: str, state: str, hint: str = "") -> None:
        self._value.setText(value)
        self._dot.set_state(state)
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))


class _Dot(QWidget):
    """Punto de color de 9 px que indica el estado."""

    def __init__(self, state: str = INFO, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self.setFixedSize(10, 10)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(STATE_COLORS.get(self._state, theme.TEXT_FAINT))
        halo = QColor(color)
        halo.setAlpha(55)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(self.rect())
        painter.setBrush(color)
        painter.drawEllipse(QRectF(2.5, 2.5, 5, 5))
        painter.end()


# --------------------------------------------------------------------------
# Lista de pasos
# --------------------------------------------------------------------------

class StepRow(QWidget):
    """Una fila de la tubería de pasos, con su punto y su línea de unión."""

    GUTTER = 38

    def __init__(self, title: str, detail: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = PENDING
        self.is_first = False
        self.is_last = False
        self._angle = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.GUTTER, 9, 8, 9)
        layout.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setFont(theme.ui_font(10, QFont.Weight.DemiBold))
        layout.addWidget(self.title_label)

        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName("Detail")
        self.detail_label.setWordWrap(True)
        self.detail_label.setVisible(bool(detail))
        layout.addWidget(self.detail_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._spin)
        self._timer.setInterval(40)

    def set_state(self, state: str, detail: str | None = None) -> None:
        self.state = state
        if detail is not None:
            self.detail_label.setText(detail)
            self.detail_label.setVisible(bool(detail))
        if state == RUNNING:
            self._timer.start()
        else:
            self._timer.stop()
        color = {
            PENDING: theme.TEXT_MUTED,
            RUNNING: theme.TEXT,
            OK: theme.TEXT,
            FAIL: theme.DANGER,
            SKIP: theme.TEXT_FAINT,
        }.get(state, theme.TEXT)
        self.title_label.setStyleSheet(f"color: {color};")
        self.update()

    def _spin(self) -> None:
        self._angle = (self._angle + 9) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        x = 17.0
        cy = 22.0
        color = QColor(STATE_COLORS.get(self.state, theme.TEXT_FAINT))

        # Linea que une los pasos, como una tubería.
        line = QPen(QColor(theme.BORDER), 1.6)
        painter.setPen(line)
        if not self.is_first:
            painter.drawLine(QPointF(x, 0), QPointF(x, cy - 11))
        if not self.is_last:
            painter.drawLine(QPointF(x, cy + 11), QPointF(x, self.height()))

        if self.state == RUNNING:
            self._paint_spinner(painter, x, cy, color)
            return

        painter.setPen(Qt.PenStyle.NoPen)
        if self.state == PENDING:
            painter.setBrush(QColor(theme.BG))
            painter.drawEllipse(QPointF(x, cy), 8, 8)
            painter.setPen(QPen(QColor(theme.BORDER), 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x, cy), 8, 8)
        else:
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, cy), 9, 9)
            painter.setPen(QPen(QColor(theme.BG), 2.0, cap=Qt.PenCapStyle.RoundCap,
                                join=Qt.PenJoinStyle.RoundJoin))
            if self.state == OK:
                painter.drawLine(QPointF(x - 4, cy), QPointF(x - 1, cy + 3.2))
                painter.drawLine(QPointF(x - 1, cy + 3.2), QPointF(x + 4.2, cy - 3.2))
            elif self.state == FAIL:
                painter.drawLine(QPointF(x - 3.4, cy - 3.4), QPointF(x + 3.4, cy + 3.4))
                painter.drawLine(QPointF(x + 3.4, cy - 3.4), QPointF(x - 3.4, cy + 3.4))
            else:  # SKIP
                painter.drawLine(QPointF(x - 4, cy), QPointF(x + 4, cy))
        painter.end()

    def _paint_spinner(self, painter: QPainter, x: float, cy: float, color: QColor) -> None:
        painter.setBrush(QColor(theme.BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, cy), 9, 9)

        track = QPen(QColor(theme.BORDER), 2.2)
        painter.setPen(track)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(x - 8, cy - 8, 16, 16)
        painter.drawArc(rect, 0, 360 * 16)

        arc = QPen(color, 2.2, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        painter.drawArc(rect, int(-self._angle * 16), 110 * 16)
        painter.end()


class StepList(QWidget):
    """Contenedor de StepRow que gestiona primero/último y los estados."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._rows: dict[str, StepRow] = {}
        self._order: list[str] = []

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self._rows.clear()
        self._order.clear()

    def add_step(self, step_id: str, title: str, detail: str = "") -> StepRow:
        row = StepRow(title, detail)
        self._rows[step_id] = row
        self._order.append(step_id)
        self._layout.addWidget(row)
        self._refresh_edges()
        return row

    def _refresh_edges(self) -> None:
        for index, step_id in enumerate(self._order):
            row = self._rows[step_id]
            row.is_first = index == 0
            row.is_last = index == len(self._order) - 1
            row.update()

    def set_state(self, step_id: str, state: str, detail: str | None = None) -> None:
        row = self._rows.get(step_id)
        if row:
            row.set_state(state, detail)

    def row(self, step_id: str) -> StepRow | None:
        return self._rows.get(step_id)


# --------------------------------------------------------------------------
# Barra de progreso
# --------------------------------------------------------------------------

class ProgressBar(QWidget):
    """Barra fina y redondeada, con modo indeterminado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(6)
        self._value = 0.0
        self._indeterminate = False
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.setInterval(24)

    def set_value(self, value: float) -> None:
        self._indeterminate = False
        self._timer.stop()
        self._value = max(0.0, min(1.0, value))
        self.update()

    def set_indeterminate(self, active: bool) -> None:
        self._indeterminate = active
        if active:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._offset = (self._offset + 0.012) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = self.height() / 2
        full = QRectF(self.rect())

        track = QPainterPath()
        track.addRoundedRect(full, radius, radius)
        painter.fillPath(track, QColor("#22262F"))

        if self._indeterminate:
            width = full.width() * 0.32
            # Vaiven suave de extremo a extremo.
            travel = (full.width() + width) * self._offset - width
            rect = QRectF(travel, 0, width, full.height())
            painter.setClipPath(track)
            bar = QPainterPath()
            bar.addRoundedRect(rect, radius, radius)
            painter.fillPath(bar, QColor(theme.ACCENT))
        elif self._value > 0:
            rect = QRectF(0, 0, max(full.width() * self._value, radius * 2), full.height())
            bar = QPainterPath()
            bar.addRoundedRect(rect, radius, radius)
            painter.fillPath(bar, QColor(theme.ACCENT))
        painter.end()


# --------------------------------------------------------------------------
# Registro plegable
# --------------------------------------------------------------------------

class LogPane(QWidget):
    """Consola de salida, oculta por defecto para no asustar al novato."""

    MAX_LINES = 4000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.toggle = QPushButton(t("Mostrar detalles técnicos"))
        self.toggle.setObjectName("Ghost")
        self.toggle.setCheckable(True)
        self.toggle.clicked.connect(self._on_toggle)
        header.addWidget(self.toggle)
        header.addStretch(1)

        self.copy_button = QPushButton(t("Copiar registro"))
        self.copy_button.setObjectName("Ghost")
        self.copy_button.setVisible(False)
        header.addWidget(self.copy_button)
        layout.addLayout(header)

        self.view = QPlainTextEdit()
        self.view.setObjectName("Log")
        self.view.setReadOnly(True)
        self.view.setFont(theme.mono_font(9))
        self.view.setMaximumBlockCount(self.MAX_LINES)
        self.view.setVisible(False)
        self.view.setMinimumHeight(190)
        layout.addWidget(self.view)

        self.copy_button.clicked.connect(self._copy)

    def set_expanded(self, expanded: bool) -> None:
        """Despliega o pliega el registro desde fuera del widget."""
        self.toggle.setChecked(expanded)
        self._on_toggle(expanded)

    def _on_toggle(self, checked: bool) -> None:
        self.view.setVisible(checked)
        self.copy_button.setVisible(checked)
        self.toggle.setText(
            t("Ocultar detalles técnicos") if checked else t("Mostrar detalles técnicos")
        )

    def _copy(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.view.toPlainText())
        self.copy_button.setText(t("Copiado"))
        QTimer.singleShot(1500, lambda: self.copy_button.setText(t("Copiar registro")))

    def append(self, line: str) -> None:
        self.view.appendPlainText(line)

    def text(self) -> str:
        return self.view.toPlainText()

    def clear(self) -> None:
        self.view.clear()


# --------------------------------------------------------------------------
# Utilidades de maquetacion
# --------------------------------------------------------------------------

def section_title(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionTitle")
    return label


def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setObjectName("Separator")
    line.setStyleSheet(
        f"QFrame#Separator {{ background: {theme.BORDER_SOFT}; border: none; }}"
    )
    return line


class ResultMark(QWidget):
    """Círculo grande con un tic o un aspa para la pantalla de resultado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(76, 76)
        self._ok = True

    def set_ok(self, ok: bool) -> None:
        self._ok = ok
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(theme.OK if self._ok else theme.DANGER)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = self.width() / 2 - 4

        halo = QColor(color)
        halo.setAlpha(38)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(center, radius + 3, radius + 3)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 3))
        painter.drawEllipse(center, radius, radius)

        pen = QPen(color, 5, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        cx, cy = center.x(), center.y()
        if self._ok:
            path = QPainterPath()
            path.moveTo(cx - 15, cy + 1)
            path.lineTo(cx - 5, cy + 11)
            path.lineTo(cx + 16, cy - 12)
            painter.drawPath(path)
        else:
            painter.drawLine(QPointF(cx, cy - 13), QPointF(cx, cy + 4))
            painter.drawPoint(QPointF(cx, cy + 14))
        painter.end()
