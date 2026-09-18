"""Lectura del paquete que el usuario suelta en la ventana.

Acepta el .zip tal cual lo descarga de Blackmagic, o el .run ya descomprimido.
La extracción se hace en trozos para poder mostrar progreso y cancelar: el
instalador de Resolve pesa más de 11 GB.
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..i18n import t

from .system import free_space_gb

CHUNK = 8 * 1024 * 1024  # 8 MB: buen equilibrio entre velocidad y refresco de UI

# DaVinci_Resolve_Studio_21.1_Linux.run  /  DaVinci_Resolve_20.0.1_Linux.zip
NAME_RE = re.compile(
    r"DaVinci[_ ]Resolve[_ ]?(?P<studio>Studio[_ ])?(?P<versión>\d+(?:\.\d+)*)[_ ]Linux",
    re.IGNORECASE,
)


class ArchiveError(Exception):
    """Problema con el paquete que el usuario eligio."""


@dataclass
class ArchiveInfo:
    source: Path
    kind: str               # "zip" o "run"
    version: str = ""
    studio: bool = False
    run_member: str = ""    # nombre del .run dentro del zip
    run_size: int = 0       # tamaño del .run ya descomprimido
    source_size: int = 0

    @property
    def edition(self) -> str:
        return "Studio" if self.studio else "Free"

    @property
    def label(self) -> str:
        version = self.version or t("versión desconocida")
        return f"DaVinci Resolve {self.edition} {version}"

    @property
    def needs_extraction(self) -> bool:
        return self.kind == "zip"

    @property
    def run_size_gb(self) -> float:
        return self.run_size / (1024 ** 3)


def _parse_name(text: str) -> tuple[str, bool]:
    m = NAME_RE.search(text)
    if not m:
        return "", False
    return m.group("versión"), bool(m.group("studio"))


def _version_from_instructions(zf: zipfile.ZipFile) -> tuple[str, bool]:
    """Plan B: leer la versión del HTML de instrucciones que viene en el zip."""
    for name in zf.namelist():
        if name.lower().endswith(".html"):
            try:
                text = zf.read(name).decode("utf-8", errors="replace")
            except (OSError, zipfile.BadZipFile):
                continue
            version, studio = _parse_name(text)
            if version:
                return version, studio
    return "", False


def inspect(path: str | Path) -> ArchiveInfo:
    """Averigua que es el archivo soltado, sin descomprimir nada."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ArchiveError(t("No encuentro el archivo:") + f"\n{source}")

    suffix = source.suffix.lower()
    size = source.stat().st_size

    if suffix == ".run":
        version, studio = _parse_name(source.name)
        return ArchiveInfo(
            source=source, kind="run", version=version, studio=studio,
            run_size=size, source_size=size,
        )

    if suffix != ".zip":
        raise ArchiveError(t(
            "Ese archivo no me sirve.\n\n"
            "Suelta aquí el .zip que descargaste de Blackmagic Design "
            "(por ejemplo DaVinci_Resolve_Studio_21.1_Linux.zip) o el .run "
            "que hay dentro."
        ))

    try:
        with zipfile.ZipFile(source) as zf:
            runs = [i for i in zf.infolist() if i.filename.lower().endswith(".run")]
            if not runs:
                raise ArchiveError(t(
                    "Este .zip no contiene ningún instalador .run.\n\n"
                    "Asegúrate de haber descargado el paquete de Linux desde "
                    "blackmagicdesign.com y no el de Windows o macOS."
                ))
            run = max(runs, key=lambda i: i.file_size)
            version, studio = _parse_name(run.filename)
            if not version:
                version, studio = _parse_name(source.name)
            if not version:
                version, studio = _version_from_instructions(zf)
            return ArchiveInfo(
                source=source,
                kind="zip",
                version=version,
                studio=studio,
                run_member=run.filename,
                run_size=run.file_size,
                source_size=size,
            )
    except zipfile.BadZipFile as exc:
        raise ArchiveError(t(
            "El .zip está dañado o incompleto.\n\n"
            "Lo más probable es que la descarga se cortara. Descárgalo otra vez."
        )) from exc


def check_space(info: ArchiveInfo, workdir: Path) -> str:
    """Devuelve un mensaje de error si no cabe, o cadena vacia si todo bien."""
    if not info.needs_extraction:
        return ""
    needed = info.run_size_gb * 1.05          # 5% de margen
    available = free_space_gb(workdir)
    if available < needed:
        return t(
            "No hay espacio suficiente en {workdir}.\n\n"
            "Hacen falta unos {needed} GB libres para descomprimir el instalador "
            "y solo quedan {available} GB. Libera espacio o elige otra carpeta "
            "de trabajo.",
            workdir=workdir, needed=f"{needed:.1f}", available=f"{available:.1f}",
        )
    return ""


def extract_run(
    info: ArchiveInfo,
    workdir: Path,
    progress: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Saca el .run del zip a `workdir` y devuelve su ruta.

    Si ya existe uno del tamaño correcto, lo reutiliza en vez de repetir 11 GB
    de escritura.
    """
    if not info.needs_extraction:
        return info.source

    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / Path(info.run_member).name

    if target.exists() and target.stat().st_size == info.run_size:
        if progress:
            progress(info.run_size, info.run_size)
        target.chmod(0o755)
        return target

    partial = target.with_suffix(target.suffix + ".part")
    done = 0
    try:
        with zipfile.ZipFile(info.source) as zf, zf.open(info.run_member) as src:
            with open(partial, "wb") as dst:
                while True:
                    if should_cancel and should_cancel():
                        raise ArchiveError(t("Extracción cancelada."))
                    block = src.read(CHUNK)
                    if not block:
                        break
                    dst.write(block)
                    done += len(block)
                    if progress:
                        progress(done, info.run_size)
    except ArchiveError:
        partial.unlink(missing_ok=True)
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        partial.unlink(missing_ok=True)
        raise ArchiveError(t("No pude descomprimir el instalador:") + f"\n{exc}") from exc

    os.replace(partial, target)
    target.chmod(0o755)
    return target
