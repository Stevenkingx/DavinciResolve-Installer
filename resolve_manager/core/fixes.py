"""Reparaciones post-instalación.

Son los arreglos que hoy la gente tiene que buscar en foros y aplicar a mano.
Cada arreglo sabe detectar si hace falta, aplicarse y deshacerse.
"""

from __future__ import annotations

import os
import pwd
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import t
from .plan import (
    KIND_CHOWN,
    KIND_RESTORE_LIBS,
    KIND_SHIELD_LIBS,
    KIND_WRITE_DESKTOP,
    Action,
)
from .system import RESOLVE_DIR

LIBS_DIR = RESOLVE_DIR / "libs"
DISABLED_DIR = LIBS_DIR / "disabled-libraries"

# Librerías que Resolve trae empaquetadas y que chocan con las del sistema en
# distribuciones modernas: el binario carga la copia vieja de Resolve y revienta
# al hablar con GTK o con los portales del escritorio. La solución conocida es
# apartarlas para que se use la versión del sistema.
SHIELD_PATTERNS = ["libglib-2.0*", "libgio-2.0*", "libgmodule-2.0*"]

DESKTOP_PATH = Path("/usr/share/applications/com.blackmagicdesign.resolve.desktop")

# El lanzador lleva las dos traducciones dentro, que es como funciona el
# estándar .desktop: cada escritorio elige según su idioma.
DESKTOP_CONTENT = """[Desktop Entry]
Version=1.0
Type=Application
Name=DaVinci Resolve
GenericName=Video Editor
GenericName[es]=Editor de vídeo
Comment=Editing, color, visual effects and audio post production
Comment[es]=Edición, color, efectos visuales y postproducción de audio
Path=/opt/resolve/
Exec=/opt/resolve/bin/resolve %u
Terminal=false
MimeType=application/x-resolveproj;
Icon=/opt/resolve/graphics/DV_Resolve.png
StartupNotify=true
Categories=AudioVideo;Video;AudioVideoEditing;
"""

# Carpetas que Resolve escribe como usuario normal. Si el instalador corrió como
# root y las dejó suyas, Resolve arranca y se cierra sin decir nada.
USER_OWNED_PATHS = [
    "~/.local/share/DaVinciResolve",
    "~/.cache/BlackmagicDesign",
    "~/.config/Blackmagic Design",
    "/opt/resolve/configs",
    "/opt/resolve/logs",
    "/opt/resolve/easyDCP",
    "/opt/resolve/Fusion",
    "/opt/resolve/.license",
]

STATUS_NEEDED = "needed"          # hace falta y no está aplicado
STATUS_APPLIED = "applied"        # ya está aplicado
STATUS_NA = "not_applicable"      # no aplica en este equipo


@dataclass
class Fix:
    id: str
    title: str
    detail: str
    status: str = STATUS_NEEDED
    recommended: bool = True
    revertible: bool = False
    evidence: list[str] = field(default_factory=list)

    @property
    def pending(self) -> bool:
        return self.status == STATUS_NEEDED


# --------------------------------------------------------------------------
# Detección
# --------------------------------------------------------------------------

def _shielded_libs() -> tuple[list[str], list[str]]:
    """Devuelve (librerías aún activas, librerías ya apartadas)."""
    active: list[str] = []
    parked: list[str] = []
    if LIBS_DIR.is_dir():
        for pattern in SHIELD_PATTERNS:
            active.extend(sorted(p.name for p in LIBS_DIR.glob(pattern) if p.is_file()))
    if DISABLED_DIR.is_dir():
        for pattern in SHIELD_PATTERNS:
            parked.extend(sorted(p.name for p in DISABLED_DIR.glob(pattern)))
    return active, parked


def real_user() -> tuple[str, int, int]:
    """El usuario real, también cuando corremos bajo pkexec o sudo."""
    value = os.environ.get("PKEXEC_UID")
    if value and value.isdigit():
        entry = pwd.getpwuid(int(value))
        return entry.pw_name, entry.pw_uid, entry.pw_gid

    name = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
    if name:
        try:
            entry = pwd.getpwnam(name)
            return entry.pw_name, entry.pw_uid, entry.pw_gid
        except KeyError:
            pass

    entry = pwd.getpwuid(os.getuid())
    return entry.pw_name, entry.pw_uid, entry.pw_gid


def _expand_user_paths(home: str) -> list[str]:
    return [p.replace("~", home, 1) if p.startswith("~") else p for p in USER_OWNED_PATHS]


def _misowned_paths(uid: int, home: str) -> list[str]:
    bad: list[str] = []
    for raw in _expand_user_paths(home):
        path = Path(raw)
        if not path.exists():
            continue
        try:
            if path.stat().st_uid != uid:
                bad.append(raw)
        except OSError:
            continue
    return bad


def detect_fixes(resolve_installed: bool) -> list[Fix]:
    fixes: list[Fix] = []
    name, uid, _gid = real_user()
    home = pwd.getpwuid(uid).pw_dir

    # 1. Librerías glib en conflicto
    active, parked = _shielded_libs()
    if not resolve_installed:
        status = STATUS_NA
    elif active:
        status = STATUS_NEEDED
    elif parked:
        status = STATUS_APPLIED
    else:
        status = STATUS_NA

    fixes.append(Fix(
        id="shield-glib",
        title=t("Apartar las librerías glib que trae Resolve"),
        detail=t(
            "Resolve incluye su propia copia (antigua) de libglib, libgio y "
            "libgmodule. En las distribuciones actuales esa copia choca con la "
            "del sistema y hace que el programa se cierre solo al abrir un "
            "diálogo de archivos o al exportar. Se mueven a «disabled-libraries» "
            "para que use las del sistema. Es reversible con un clic."
        ),
        status=status,
        revertible=bool(parked),
        evidence=active or parked,
    ))

    # 2. Permisos de las carpetas del usuario
    misowned = _misowned_paths(uid, home)
    fixes.append(Fix(
        id="fix-perms",
        title=t("Devolverte la propiedad de tus carpetas de Resolve"),
        detail=t(
            "El instalador se ejecuta como root y a veces deja carpetas de "
            "configuración a nombre de root. Cuando pasa, Resolve arranca y se "
            "cierra al instante sin ningún mensaje. Se devuelven a «{user}».",
            user=name,
        ),
        status=STATUS_NEEDED if misowned else STATUS_NA,
        evidence=misowned,
    ))

    # 3. Lanzador del menú
    current = ""
    if DESKTOP_PATH.exists():
        current = DESKTOP_PATH.read_text(encoding="utf-8", errors="replace")
    desktop_ok = "Exec=/opt/resolve/bin/resolve" in current

    fixes.append(Fix(
        id="desktop-entry",
        title=t("Reparar el acceso directo del menú de aplicaciones"),
        detail=t(
            "Rehace el lanzador de DaVinci Resolve para que aparezca en el menú "
            "con su icono y abra los proyectos con doble clic."
        ),
        status=STATUS_NA if (desktop_ok or not resolve_installed) else STATUS_NEEDED,
    ))
    return fixes


# --------------------------------------------------------------------------
# Traducción a acciones del plan
# --------------------------------------------------------------------------

def fix_action(fix: Fix, revert: bool = False) -> Action | None:
    if fix.id == "shield-glib":
        if revert:
            return Action(
                id="restore-glib",
                title=t("Restaurar las librerías glib originales de Resolve"),
                detail=t("Devuelve las librerías desde «disabled-libraries» a su sitio."),
                kind=KIND_RESTORE_LIBS,
                params={"libs_dir": str(LIBS_DIR), "disabled_dir": str(DISABLED_DIR)},
            )
        return Action(
            id="shield-glib",
            title=fix.title,
            detail=fix.detail,
            kind=KIND_SHIELD_LIBS,
            params={
                "libs_dir": str(LIBS_DIR),
                "disabled_dir": str(DISABLED_DIR),
                "patterns": SHIELD_PATTERNS,
            },
        )

    if fix.id == "fix-perms":
        name, uid, gid = real_user()
        home = pwd.getpwuid(uid).pw_dir
        return Action(
            id="fix-perms",
            title=fix.title,
            detail=fix.detail,
            kind=KIND_CHOWN,
            params={"paths": _expand_user_paths(home), "uid": uid, "gid": gid, "user": name},
        )

    if fix.id == "desktop-entry":
        return Action(
            id="desktop-entry",
            title=fix.title,
            detail=fix.detail,
            kind=KIND_WRITE_DESKTOP,
            params={"path": str(DESKTOP_PATH), "content": DESKTOP_CONTENT},
            allow_fail=True,
        )
    return None
