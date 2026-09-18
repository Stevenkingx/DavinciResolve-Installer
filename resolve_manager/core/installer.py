"""Orquestación: convierte «este paquete + este equipo» en un plan ejecutable."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import t
from .archive import ArchiveInfo, check_space
from .fixes import Fix, fix_action, real_user
from .packages import DependencyOptions, build_dependency_actions
from .plan import KIND_EXTRACT, Action, Plan
from .system import SystemReport, compare_versions, free_space_gb

# Flags reales del instalador de Blackmagic (comprobadas con --help):
#   -i  instalar sin interfaz gráfica
#   -y  no pedir confirmación
#   -a  permitir la instalación ejecutándose como root
INSTALL_FLAGS = ["-i", "-y", "-a"]

# El instalador comprueba los paquetes del sistema por nombre y se equivoca en
# casi todas las distros modernas: en Fedora busca «zlib» cuando el paquete real
# se llama «zlib-ng-compat», y aborta. Esta variable desactiva ese chequeo roto.
SKIP_CHECK_ENV = {"SKIP_PACKAGE_CHECK": "1"}

DOWNLOAD_URL = "https://www.blackmagicdesign.com/support/family/davinci-resolve-and-fusion"


# --------------------------------------------------------------------------
# Ediciones
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Edition:
    key: str          # "free" | "studio"
    name: str
    summary: str
    detail: str
    file_hint: str    # cómo se llama el archivo que hay que descargar


def editions() -> dict[str, Edition]:
    """Las dos ediciones, con los textos ya traducidos al idioma activo."""
    return {
        "free": Edition(
            key="free",
            name=t("Gratuita"),
            summary=t("Gratis, sin licencia ni registro"),
            detail=t(
                "La versión gratuita es un programa completo de edición, color, "
                "efectos y audio. Para la mayoría de la gente es la correcta. "
                "Exporta hasta 4K a 60 fps."
            ),
            file_hint=t("DaVinci_Resolve_<versión>_Linux.zip"),
        ),
        "studio": Edition(
            key="studio",
            name=t("Studio"),
            summary=t("De pago: necesita clave de activación o llave USB"),
            detail=t(
                "Studio añade las herramientas de IA (Magic Mask, seguimiento "
                "facial), reducción de ruido, HDR, exportación por encima de 4K y "
                "colaboración en red. Si no tienes licencia, no arrancará."
            ),
            file_hint=t("DaVinci_Resolve_Studio_<versión>_Linux.zip"),
        ),
    }


def edition_key(studio: bool) -> str:
    return "studio" if studio else "free"


def edition_mismatch(info: ArchiveInfo, preferred: str) -> str:
    """Aviso si el paquete soltado no es la edición que el usuario eligió."""
    if preferred not in ("free", "studio"):
        return ""
    actual = edition_key(info.studio)
    if actual == preferred:
        return ""
    table = editions()
    return t(
        "Elegiste la edición {wanted}, pero el paquete que soltaste es el de la "
        "edición {got}. Se instalará {got}: si no es lo que quieres, descarga el "
        "archivo correcto ({hint}).",
        wanted=table[preferred].name,
        got=table[actual].name,
        hint=table[preferred].file_hint,
    )


def fuse_available() -> bool:
    """El instalador es un AppImage y necesita FUSE para automontarse."""
    return Path("/dev/fuse").exists() and bool(
        shutil.which("fusermount") or shutil.which("fusermount3")
    )


# --------------------------------------------------------------------------
# Opciones y diagnóstico de la situación
# --------------------------------------------------------------------------

@dataclass
class InstallOptions:
    workdir: Path
    deps: DependencyOptions = field(default_factory=DependencyOptions)
    enabled_fixes: set[str] = field(
        default_factory=lambda: {"shield-glib", "fix-perms", "desktop-entry"}
    )
    preferred_edition: str = ""
    keep_installer: bool = True


@dataclass
class Situation:
    """Qué representa este paquete respecto a lo que ya hay instalado."""

    kind: str           # "install" | "update" | "reinstall" | "downgrade"
    headline: str
    detail: str


def assess(info: ArchiveInfo, report: SystemReport) -> Situation:
    current = report.resolve

    if not current.installed:
        return Situation(
            "install",
            t("Instalar {what}", what=info.label),
            t(
                "No hay ninguna versión de DaVinci Resolve en este equipo. Voy a "
                "hacer la instalación completa, drivers incluidos."
            ),
        )

    if not info.version or not current.version:
        return Situation(
            "reinstall",
            t("Reinstalar {what}", what=info.label),
            t(
                "No consigo comparar las versiones con seguridad, así que trataré "
                "esto como una reinstalación limpia sobre la actual."
            ),
        )

    order = compare_versions(info.version, current.version)
    edition_change = info.studio != current.studio
    extra = ""
    if edition_change:
        extra = " " + t(
            "Además cambia de edición: {before} → {after}.",
            before=current.edition, after=info.edition,
        )

    if order > 0:
        return Situation(
            "update",
            t("Actualizar a {what}", what=info.label),
            t(
                "Tienes la {current} y este paquete trae la {new}.",
                current=current.version, new=info.version,
            )
            + extra + " "
            + t("Tus proyectos y tu base de datos no se tocan."),
        )

    if order == 0:
        return Situation(
            "reinstall",
            t("Reinstalar {what}", what=info.label),
            t(
                "Ya tienes exactamente la {current} instalada. Reinstalar sirve "
                "para reparar una instalación que se rompió.",
                current=current.version,
            ) + extra,
        )

    return Situation(
        "downgrade",
        t("Volver a {what}", what=info.label),
        t(
            "Tienes la {current}, que es MÁS NUEVA que la {new} de este paquete. "
            "Instalar una versión anterior puede impedir que abras proyectos "
            "guardados con la versión nueva.",
            current=current.version, new=info.version,
        ) + extra,
    )


# --------------------------------------------------------------------------
# Construcción del plan
# --------------------------------------------------------------------------

def build_plan(
    info: ArchiveInfo,
    report: SystemReport,
    fixes: list[Fix],
    options: InstallOptions,
    run_path: Path | None = None,
) -> Plan:
    """Construye el plan completo. `run_path` se conoce tras descomprimir."""
    plan = Plan()

    # ---- comprobaciones que pueden impedir seguir --------------------------
    space_error = check_space(info, options.workdir)
    if space_error:
        plan.blockers.append(space_error)

    needed_opt = 6.0
    free_opt = free_space_gb("/opt")
    if free_opt < needed_opt:
        plan.blockers.append(t(
            "Quedan solo {free} GB libres en /opt y la instalación necesita unos "
            "{needed} GB.",
            free=f"{free_opt:.1f}", needed=f"{needed_opt:.0f}",
        ))

    if report.distro.immutable:
        plan.notes.append(t(
            "Estás en un sistema inmutable (Silverblue, Bazzite, SteamOS…). "
            "Resolve se instalará en /opt, pero las dependencias del sistema "
            "tendrás que añadirlas con rpm-ostree."
        ))

    mismatch = edition_mismatch(info, options.preferred_edition)
    if mismatch:
        plan.notes.append(mismatch)

    if info.studio:
        plan.notes.append(t(
            "DaVinci Resolve Studio necesita una clave de activación o una llave "
            "USB. Sin licencia se instalará, pero no arrancará."
        ))

    situation = assess(info, report)
    if situation.kind == "downgrade":
        plan.notes.append(t(
            "Vas a instalar una versión más antigua que la que ya tienes. Haz "
            "copia de tu base de datos de proyectos antes de continuar."
        ))

    # ---- 1. descomprimir el .run (sin root) --------------------------------
    if info.needs_extraction:
        plan.add(Action(
            id="extract",
            title=t("Descomprimir el instalador ({size} GB)",
                    size=f"{info.run_size_gb:.1f}"),
            detail=t(
                "El .zip guarda el instalador sin comprimir, así que esto es "
                "básicamente una copia de disco. Es el paso más lento."
            ),
            kind=KIND_EXTRACT,
            root=False,
            weight=12,
        ))

    # ---- 2. dependencias y drivers -----------------------------------------
    deps = build_dependency_actions(
        report.distro, report.gpus, report.drivers, options.deps
    )
    for action in deps.actions:
        plan.add(action)
    plan.notes.extend(deps.notes)

    # ---- 3. el instalador de Resolve ---------------------------------------
    target = str(run_path) if run_path else (Path(info.run_member).name or info.source.name)
    env = dict(SKIP_CHECK_ENV)
    # El instalador reparte permisos según el usuario que lanzó sudo; bajo
    # pkexec esa variable no existe, así que se la damos nosotros.
    user_name, _uid, _gid = real_user()
    env["SUDO_USER"] = user_name

    if not fuse_available():
        # Sin FUSE el AppImage no se automonta: que se auto-extraiga a disco.
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        env["TMPDIR"] = str(options.workdir)
        plan.notes.append(t(
            "Este equipo no tiene FUSE, así que el instalador se auto-extraerá en "
            "{workdir}. Necesitarás el doble de espacio temporal.",
            workdir=options.workdir,
        ))

    plan.add(Action(
        id="resolve-install",
        title=t("Instalar {what}", what=info.label),
        detail=(
            t("Ejecuta el instalador oficial de Blackmagic en modo silencioso.")
            + "\n"
            + t("Comando:") + f" SKIP_PACKAGE_CHECK=1 {Path(target).name} "
            + " ".join(INSTALL_FLAGS)
        ),
        argv=[target, *INSTALL_FLAGS],
        env=env,
        weight=25,
    ))

    # ---- 4. reparaciones post-instalación ----------------------------------
    # Estos dos arreglos describen problemas que crea el propio instalador, así
    # que en una instalación desde cero todavía no se pueden «detectar»: hay que
    # programarlos igualmente. Ambos son idempotentes.
    siempre_tras_instalar = {"shield-glib", "fix-perms"}
    instalando = any(a.id == "resolve-install" for a in plan.actions)

    for fix in fixes:
        if fix.id not in options.enabled_fixes:
            continue
        if not fix.pending and not (instalando and fix.id in siempre_tras_instalar):
            continue
        action = fix_action(fix)
        if action:
            plan.add(action)

    if plan.needs_reboot():
        plan.notes.append(t(
            "Se va a instalar un driver de kernel: reinicia el equipo antes de "
            "abrir DaVinci Resolve."
        ))
    return plan


def build_repair_plan(fixes: list[Fix], selected: set[str],
                      revert: set[str] | None = None) -> Plan:
    """Plan que solo aplica reparaciones, sin instalar nada."""
    plan = Plan()
    revert = revert or set()
    for fix in fixes:
        if fix.id in revert:
            action = fix_action(fix, revert=True)
        elif fix.id in selected:
            action = fix_action(fix)
        else:
            continue
        if action:
            plan.add(action)
    return plan


def build_uninstall_plan(run_path: Path) -> Plan:
    """Desinstalación limpia usando el propio instalador (-u)."""
    plan = Plan()
    plan.add(Action(
        id="resolve-uninstall",
        title=t("Desinstalar DaVinci Resolve"),
        detail=t(
            "Usa el desinstalador oficial. No borra tus proyectos ni tu base de "
            "datos, que viven en tu carpeta personal."
        ),
        argv=[str(run_path), "-u", "-y", "-a"],
        env=dict(SKIP_CHECK_ENV),
        weight=10,
    ))
    return plan
