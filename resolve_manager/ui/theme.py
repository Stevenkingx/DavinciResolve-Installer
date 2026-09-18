"""Tema visual de la aplicación.

Paleta oscura afin a DaVinci Resolve: grises fríos y el ambar de Blackmagic
como color de acento.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

# -- paleta ----------------------------------------------------------------

BG          = "#15171C"   # fondo de la ventana
SURFACE     = "#1D2027"   # tarjetas
SURFACE_2   = "#252932"   # tarjetas elevadas / hover
BORDER      = "#2F3441"
BORDER_SOFT = "#262A33"

TEXT        = "#E9EBEF"
TEXT_MUTED  = "#9AA2B1"
TEXT_FAINT  = "#6C7485"

ACCENT      = "#FFB53F"   # ambar Blackmagic
ACCENT_DIM  = "#C98A28"
ACCENT_SOFT = "#2A2318"

OK          = "#4ADE80"
OK_SOFT     = "#16271D"
WARN        = "#FBBF24"
WARN_SOFT   = "#2A2416"
DANGER      = "#F87171"
DANGER_SOFT = "#2A1A1A"
INFO        = "#60A5FA"
INFO_SOFT   = "#172230"

RADIUS = 12


def qcolor(value: str, alpha: int = 255) -> QColor:
    color = QColor(value)
    color.setAlpha(alpha)
    return color


# -- tipografía ------------------------------------------------------------

def ui_font(size: int = 10, weight: int = QFont.Weight.Normal) -> QFont:
    families = QFontDatabase.families()
    for name in ("Inter", "Inter Display", "Noto Sans", "Cantarell", "DejaVu Sans"):
        if name in families:
            font = QFont(name)
            break
    else:
        font = QFont()
    font.setPointSize(size)
    font.setWeight(weight)
    return font


def mono_font(size: int = 9) -> QFont:
    families = QFontDatabase.families()
    for name in ("JetBrains Mono", "Fira Code", "Hack", "Noto Sans Mono", "DejaVu Sans Mono", "monospace"):
        if name in families:
            font = QFont(name)
            break
    else:
        font = QFont("monospace")
    font.setPointSize(size)
    return font


# -- hoja de estilos -------------------------------------------------------

STYLESHEET = f"""
QWidget {{
    background: transparent;
    color: {TEXT};
}}
QMainWindow, #Root {{
    background: {BG};
}}

/* ---- tarjetas ---- */
#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
}}
#CardRaised {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
/* Tarjeta elegible (selector de edición) */
#CardPick {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: {RADIUS}px;
}}
#CardPick:hover {{
    border-color: #3D4454;
    background: {SURFACE_2};
}}
#CardPickOn {{
    background: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
    border-radius: {RADIUS}px;
}}
#PickName {{ font-size: 15px; font-weight: 600; color: {TEXT}; }}
#PickSummary {{ font-size: 12px; color: {TEXT_MUTED}; }}
#PickHint {{ font-size: 11px; color: {TEXT_FAINT}; }}
/* Conmutador de idioma */
QPushButton#Lang {{
    background: transparent; border: 1px solid {BORDER};
    border-radius: 6px; padding: 4px 10px; font-size: 11px; color: {TEXT_MUTED};
    min-width: 30px;
}}
QPushButton#Lang:hover {{ color: {TEXT}; border-color: #3D4454; }}
QPushButton#LangOn {{
    background: {ACCENT}; border: 1px solid {ACCENT};
    border-radius: 6px; padding: 4px 10px; font-size: 11px;
    color: #1A1405; font-weight: 600; min-width: 30px;
}}

/* ---- texto ---- */
#Title      {{ font-size: 21px; font-weight: 600; color: {TEXT}; }}
#Subtitle   {{ font-size: 13px; color: {TEXT_MUTED}; }}
#SectionTitle {{ font-size: 12px; font-weight: 600; color: {TEXT_FAINT};
                letter-spacing: 1px; text-transform: uppercase; }}
#CardLabel  {{ font-size: 11px; color: {TEXT_FAINT}; letter-spacing: 0.5px; }}
#CardValue  {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
#Muted      {{ color: {TEXT_MUTED}; font-size: 12px; }}
#Detail     {{ color: {TEXT_MUTED}; font-size: 12px; }}

/* ---- botones ---- */
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 13px;
    color: {TEXT};
}}
QPushButton:hover   {{ background: #2C313B; border-color: #3A4152; }}
QPushButton:pressed {{ background: #21252D; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; background: #1B1E25; border-color: {BORDER_SOFT}; }}

QPushButton#Primary {{
    background: {ACCENT};
    color: #1A1405;
    border: none;
    font-weight: 600;
    padding: 11px 26px;
}}
QPushButton#Primary:hover   {{ background: #FFC461; }}
QPushButton#Primary:pressed {{ background: {ACCENT_DIM}; }}
QPushButton#Primary:disabled {{ background: #3A3D44; color: {TEXT_FAINT}; }}

QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_MUTED};
    padding: 8px 14px;
}}
QPushButton#Ghost:hover {{ color: {TEXT}; background: {SURFACE_2}; }}

QPushButton#Danger {{ color: {DANGER}; border-color: #40282A; }}
QPushButton#Danger:hover {{ background: {DANGER_SOFT}; }}

QPushButton#Link {{
    background: transparent; border: none; color: {ACCENT};
    padding: 2px 4px; font-size: 12px; text-decoration: underline;
}}

/* ---- casillas ---- */
QCheckBox {{ spacing: 10px; font-size: 13px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid #3C4353; border-radius: 5px; background: #171A20;
}}
QCheckBox::indicator:hover   {{ border-color: {ACCENT_DIM}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox:disabled {{ color: {TEXT_FAINT}; }}

QRadioButton {{ spacing: 10px; font-size: 13px; }}
QRadioButton::indicator {{
    width: 17px; height: 17px; border-radius: 9px;
    border: 1px solid #3C4353; background: #171A20;
}}
QRadioButton::indicator:checked {{ border: 1px solid {ACCENT}; background: {ACCENT}; }}

/* ---- registro ---- */
QPlainTextEdit#Log {{
    background: #101218;
    border: 1px solid {BORDER_SOFT};
    border-radius: 8px;
    color: #B9C0CE;
    padding: 10px;
    selection-background-color: {ACCENT_DIM};
}}

/* ---- barras de desplazamiento ---- */
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #333947; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #414A5C; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #333947; border-radius: 5px; min-width: 30px; }}

/* ---- varios ---- */
QToolTip {{
    background: {SURFACE_2}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 8px;
}}
QLineEdit {{
    background: #171A20; border: 1px solid {BORDER}; border-radius: 7px;
    padding: 9px 12px; color: {TEXT}; font-size: 13px;
}}
QLineEdit:focus {{ border-color: {ACCENT_DIM}; }}
"""


# -- iconos generados ------------------------------------------------------
# Qt no sabe dibujar la marca de una casilla desde la hoja de estilos, así que
# la generamos como PNG la primera vez y la referenciamos desde el QSS.

def _assets_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    path = Path(base) / "davinci-resolve-manager" / "assets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _draw_check(size: int, color: str) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), size * 0.16)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    path = QPainterPath()
    path.moveTo(size * 0.22, size * 0.52)
    path.lineTo(size * 0.42, size * 0.72)
    path.lineTo(size * 0.79, size * 0.28)
    painter.drawPath(path)
    painter.end()
    return pixmap


def _draw_dot(size: int, color: str) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    radius = size * 0.22
    painter.drawEllipse(QPointF(size / 2, size / 2), radius, radius)
    painter.end()
    return pixmap


def ensure_assets() -> dict[str, str]:
    """Crea los PNG que necesita la hoja de estilos y devuelve sus rutas."""
    directory = _assets_dir()
    assets = {"check": directory / "check.png", "dot": directory / "dot.png"}
    # Se regeneran siempre: son diminutos y así un cambio de paleta se aplica.
    _draw_check(36, "#1A1405").save(str(assets["check"]))
    _draw_dot(36, "#1A1405").save(str(assets["dot"]))
    return {key: str(value) for key, value in assets.items()}


def stylesheet() -> str:
    """Hoja de estilos final, con las rutas de los iconos ya resueltas."""
    assets = ensure_assets()
    extra = f"""
QCheckBox::indicator:checked {{
    image: url("{assets['check']}");
}}
QRadioButton::indicator:checked {{
    image: url("{assets['dot']}");
}}
"""
    return STYLESHEET + extra
