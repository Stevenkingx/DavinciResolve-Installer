"""Matriz de dependencias y drivers por distribución y por fabricante de GPU.

Es el corazón de "qué le falta a este equipo para que Resolve arranque".
Cada paquete lleva escrito POR QUÉ hace falta: la interfaz se lo enseña al
usuario en vez de pedirle fe ciega.

Los textos de `reason` se guardan aquí en español, que es el idioma de origen
del código, y se traducen al construir el plan (no al importar el módulo), para
que cambiar de idioma en caliente funcione.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field

from ..i18n import t
from .plan import Action
from .system import Distro, DriverStatus, Gpu, has_vendor, run


@dataclass
class Package:
    """Un paquete a instalar. `alternatives` cubre distros que lo renombraron."""

    name: str
    reason: str
    alternatives: list[str] = field(default_factory=list)
    optional: bool = False
    args: list[str] = field(default_factory=list)   # p.ej. --allowerasing

    @property
    def candidates(self) -> list[str]:
        return [self.name, *self.alternatives]


# --------------------------------------------------------------------------
# Gestores de paquetes
# --------------------------------------------------------------------------

MANAGER_BY_FAMILY = {
    "fedora": "dnf",
    "debian": "apt",
    "arch": "pacman",
    "suse": "zypper",
}


def manager_for(distro: Distro) -> str:
    manager = MANAGER_BY_FAMILY.get(distro.family, "")
    if manager == "dnf" and not shutil.which("dnf") and shutil.which("yum"):
        return "yum"
    return manager


def is_installed(manager: str, name: str) -> bool:
    if manager in ("dnf", "yum", "zypper"):
        return run(["rpm", "-q", name])[0] == 0
    if manager == "apt":
        rc, out = run(["dpkg-query", "-W", "-f=${db:Status-Status}", name])
        return rc == 0 and out.strip() == "installed"
    if manager == "pacman":
        return run(["pacman", "-Qq", name])[0] == 0
    return False


def exists_in_repo(manager: str, name: str) -> bool:
    """Comprueba que el paquete exista, para elegir entre nombres alternativos."""
    if manager in ("dnf", "yum"):
        return run(["dnf", "--cacheonly", "info", name], timeout=25)[0] == 0
    if manager == "apt":
        rc, out = run(["apt-cache", "policy", name], timeout=25)
        return rc == 0 and bool(out.strip())
    if manager == "pacman":
        return run(["pacman", "-Si", name], timeout=25)[0] == 0
    if manager == "zypper":
        return run(["zypper", "--non-interactive", "info", name], timeout=30)[0] == 0
    return True


def resolve_name(manager: str, package: Package) -> str:
    """Devuelve el primer nombre válido del paquete en esta distro."""
    for candidate in package.candidates:
        if is_installed(manager, candidate):
            return candidate
    for candidate in package.candidates:
        if exists_in_repo(manager, candidate):
            return candidate
    return package.name


def install_argv(manager: str, names: list[str], extra: list[str] | None = None) -> list[str]:
    extra = extra or []
    if manager in ("dnf", "yum"):
        return [manager, "install", "-y", *extra, *names]
    if manager == "apt":
        return ["apt-get", "install", "-y", *extra, *names]
    if manager == "pacman":
        return ["pacman", "-S", "--noconfirm", "--needed", *extra, *names]
    if manager == "zypper":
        return ["zypper", "--non-interactive", "install", *extra, *names]
    return []


# --------------------------------------------------------------------------
# Catálogo: paquetes base (los necesita Resolve en cualquier equipo)
# --------------------------------------------------------------------------

REASON_CRYPT = ("Provee libcrypt.so.1, que Resolve necesita para arrancar y que "
                "las distribuciones actuales ya no instalan por defecto.")
REASON_ICD = "Cargador OpenCL: es como Resolve encuentra tu GPU."
REASON_CLINFO = "Herramienta de diagnóstico de OpenCL."
REASON_FUSE = "Permite montar el instalador AppImage sin descomprimirlo entero."

BASE_PACKAGES: dict[str, list[Package]] = {
    "fedora": [
        Package("libxcrypt-compat", REASON_CRYPT),
        Package("ocl-icd", REASON_ICD),
        Package("clinfo", REASON_CLINFO, optional=True),
        Package("fuse", REASON_FUSE, alternatives=["fuse-libs"], optional=True),
    ],
    "debian": [
        Package("libxcrypt1", REASON_CRYPT, alternatives=["libcrypt1"]),
        Package("ocl-icd-libopencl1", REASON_ICD),
        Package("libapr1", "Librería de utilidades que usa Resolve.",
                alternatives=["libapr1t64"]),
        Package("libaprutil1", "Complemento de libapr1.", alternatives=["libaprutil1t64"]),
        Package("libasound2", "Audio ALSA para la página Fairlight.",
                alternatives=["libasound2t64"]),
        Package("libxcb-cursor0", "Cursores XCB que exige la interfaz Qt de Resolve."),
        Package("clinfo", REASON_CLINFO, optional=True),
        Package("libfuse2", REASON_FUSE, alternatives=["libfuse2t64"], optional=True),
    ],
    "arch": [
        Package("libxcrypt-compat", REASON_CRYPT),
        Package("ocl-icd", REASON_ICD),
        Package("apr", "Librería de utilidades que usa Resolve."),
        Package("apr-util", "Complemento de apr."),
        Package("clinfo", REASON_CLINFO, optional=True),
        Package("fuse2", REASON_FUSE, optional=True),
    ],
    "suse": [
        Package("libcrypt1", REASON_CRYPT),
        Package("ocl-icd", REASON_ICD, alternatives=["libOpenCL1"]),
        Package("clinfo", REASON_CLINFO, optional=True),
        Package("fuse", REASON_FUSE, optional=True),
    ],
}


# --------------------------------------------------------------------------
# Catálogo: GPU AMD  (el caso que más gente rompe)
# --------------------------------------------------------------------------

AMD_ROCM: dict[str, list[Package]] = {
    "fedora": [
        Package(
            "rocm-opencl",
            "Runtime OpenCL de AMD. Es LA pieza que falta cuando Resolve dice "
            "«no GPU detected» con una Radeon.",
            args=["--allowerasing"],
        ),
        Package("rocm-hip", "Capa de cómputo HIP que Resolve usa para acelerar efectos."),
        Package("rocminfo", "Comprueba que ROCm ve tu tarjeta.", optional=True),
        Package("rocm-clinfo", "Diagnóstico de OpenCL específico de AMD.", optional=True),
    ],
    "arch": [
        Package("rocm-opencl-runtime",
                "Runtime OpenCL de AMD, necesario para que Resolve vea la Radeon."),
        Package("rocminfo", "Comprueba que ROCm ve tu tarjeta.", optional=True),
    ],
    "debian": [],   # ROCm en Debian/Ubuntu exige el repositorio propio de AMD
    "suse": [],
}

AMD_MESA: dict[str, list[Package]] = {
    "fedora": [
        Package("mesa-libOpenCL",
                "Driver OpenCL de Mesa (rusticl/clover). Alternativa ligera a ROCm, "
                "útil en gráficas integradas y APU."),
    ],
    "debian": [
        Package("mesa-opencl-icd",
                "Driver OpenCL de Mesa: da soporte OpenCL a las Radeon sin ROCm."),
    ],
    "arch": [
        Package("opencl-mesa", "Driver OpenCL de Mesa para Radeon.",
                alternatives=["opencl-rusticl-mesa"]),
    ],
    "suse": [
        Package("Mesa-libOpenCL", "Driver OpenCL de Mesa para Radeon."),
    ],
}


# --------------------------------------------------------------------------
# Catálogo: GPU NVIDIA
# --------------------------------------------------------------------------

NVIDIA: dict[str, list[Package]] = {
    "fedora": [
        Package("akmod-nvidia",
                "Driver propietario de NVIDIA, que se recompila solo con cada kernel."),
        Package("xorg-x11-drv-nvidia-cuda",
                "CUDA y el ICD de OpenCL de NVIDIA: sin esto Resolve no acelera nada."),
    ],
    "debian": [
        Package("nvidia-driver", "Driver propietario de NVIDIA."),
        Package("nvidia-opencl-icd", "ICD de OpenCL de NVIDIA.",
                alternatives=["libnvidia-compute-550"], optional=True),
    ],
    "arch": [
        Package("nvidia-dkms",
                "Driver propietario de NVIDIA (DKMS, sobrevive a cambios de kernel)."),
        Package("nvidia-utils", "Utilidades y librería CUDA de NVIDIA."),
        Package("opencl-nvidia", "ICD de OpenCL de NVIDIA."),
    ],
    "suse": [
        Package("nvidia-video-G06", "Driver propietario de NVIDIA."),
        Package("nvidia-compute-G06", "CUDA y OpenCL de NVIDIA."),
    ],
}


# --------------------------------------------------------------------------
# Repositorios de terceros
# --------------------------------------------------------------------------

def rpmfusion_enabled() -> bool:
    return run(["rpm", "-q", "rpmfusion-nonfree-release"])[0] == 0


def rpmfusion_action(distro: Distro) -> Action:
    release = distro.version_id or "$(rpm -E %fedora)"
    base = "https://mirrors.rpmfusion.org"
    return Action(
        id="repo-rpmfusion",
        title=t("Activar los repositorios RPM Fusion"),
        detail=t(
            "Fedora no distribuye el driver de NVIDIA por motivos de licencia. "
            "RPM Fusion es el repositorio de confianza que sí lo tiene."
        ),
        argv=[
            "dnf", "install", "-y",
            f"{base}/free/fedora/rpmfusion-free-release-{release}.noarch.rpm",
            f"{base}/nonfree/fedora/rpmfusion-nonfree-release-{release}.noarch.rpm",
        ],
        weight=2,
    )


# --------------------------------------------------------------------------
# Construcción del bloque de dependencias del plan
# --------------------------------------------------------------------------

@dataclass
class DependencyOptions:
    install_base: bool = True
    install_gpu_runtime: bool = True     # OpenCL / ROCm / CUDA
    install_nvidia_driver: bool = False  # solo si falta el driver del kernel
    amd_backend: str = "rocm"            # "rocm" o "mesa"


@dataclass
class DependencyReport:
    actions: list[Action] = field(default_factory=list)
    missing: list[Package] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _missing_packages(manager: str, packages: list[Package]) -> list[tuple[Package, str]]:
    out: list[tuple[Package, str]] = []
    for package in packages:
        if any(is_installed(manager, c) for c in package.candidates):
            continue
        out.append((package, resolve_name(manager, package)))
    return out


def _install_action(
    action_id: str,
    title: str,
    manager: str,
    items: list[tuple[Package, str]],
    optional: bool = False,
    reboot_hint: bool = False,
) -> Action | None:
    if not items:
        return None
    names = [name for _, name in items]
    extra: list[str] = []
    for package, _ in items:
        for arg in package.args:
            if arg not in extra:
                extra.append(arg)
    # La razón se traduce aquí, no en la tabla: así sigue al idioma activo.
    detail = "\n".join(f"- {name}: {t(package.reason)}" for package, name in items)
    return Action(
        id=action_id,
        title=title,
        detail=detail,
        argv=install_argv(manager, names, extra),
        optional=optional,
        weight=max(2, len(names)),
        reboot_hint=reboot_hint,
    )


def build_dependency_actions(
    distro: Distro,
    gpus: list[Gpu],
    drivers: DriverStatus,
    options: DependencyOptions,
) -> DependencyReport:
    report = DependencyReport()
    manager = manager_for(distro)
    family = distro.family

    if not manager:
        report.notes.append(t(
            "No reconozco el gestor de paquetes de esta distribución, así que no "
            "puedo instalar dependencias automáticamente. La instalación de "
            "Resolve sí puede continuar."
        ))
        return report

    if distro.immutable:
        report.notes.append(t(
            "Este sistema es inmutable (tipo Silverblue o Bazzite). Las "
            "dependencias hay que instalarlas con «rpm-ostree install», así que "
            "aquí se omiten."
        ))
        return report

    # --- paquetes base -----------------------------------------------------
    if options.install_base:
        missing = _missing_packages(manager, BASE_PACKAGES.get(family, []))
        required = [(p, n) for p, n in missing if not p.optional]
        extras = [(p, n) for p, n in missing if p.optional]
        report.missing.extend(p for p, _ in missing)

        action = _install_action(
            "deps-base", t("Instalar las librerías base que Resolve necesita"),
            manager, required,
        )
        if action:
            report.actions.append(action)
        action = _install_action(
            "deps-extra", t("Instalar herramientas de diagnóstico (opcional)"),
            manager, extras, optional=True,
        )
        if action:
            report.actions.append(action)

    # --- NVIDIA ------------------------------------------------------------
    if has_vendor(gpus, "nvidia"):
        if not drivers.nvidia_kernel_ok and options.install_nvidia_driver:
            if family == "fedora" and not rpmfusion_enabled():
                report.actions.append(rpmfusion_action(distro))
            missing = _missing_packages(manager, NVIDIA.get(family, []))
            report.missing.extend(p for p, _ in missing)
            action = _install_action(
                "driver-nvidia",
                t("Instalar el driver de NVIDIA y CUDA"),
                manager,
                [(p, n) for p, n in missing if not p.optional],
                reboot_hint=True,
            )
            if action:
                report.actions.append(action)
                report.notes.append(t(
                    "Tras instalar el driver de NVIDIA hay que REINICIAR el equipo "
                    "antes de abrir Resolve."
                ))
        elif not drivers.nvidia_kernel_ok:
            report.notes.append(t(
                "Detecté una GPU NVIDIA, pero el driver propietario no responde "
                "(nvidia-smi falla). Resolve no va a acelerar nada así. Marca la "
                "casilla del driver de NVIDIA si quieres que lo instale."
            ))
        elif not drivers.cuda_present:
            report.notes.append(t(
                "El driver de NVIDIA está activo, pero no encuentro libcuda. "
                "Instala el paquete CUDA del driver para que Resolve acelere."
            ))

    # --- AMD ---------------------------------------------------------------
    if has_vendor(gpus, "amd") and options.install_gpu_runtime:
        dedicated = has_vendor(gpus, "amd", dedicated_only=True)
        table = AMD_ROCM if options.amd_backend == "rocm" else AMD_MESA
        packages = table.get(family, [])

        if not packages and options.amd_backend == "rocm":
            table = AMD_MESA
            packages = AMD_MESA.get(family, [])
            report.notes.append(t(
                "En esta distribución, ROCm requiere añadir a mano el repositorio "
                "oficial de AMD, así que usaré el driver OpenCL de Mesa."
            ))

        missing = _missing_packages(manager, packages)
        report.missing.extend(p for p, _ in missing)
        label = t("ROCm (OpenCL de AMD)") if table is AMD_ROCM else t("OpenCL de Mesa")
        action = _install_action(
            "gpu-amd",
            t("Instalar {label} para tu Radeon", label=label),
            manager,
            [(p, n) for p, n in missing if not p.optional],
            optional=not dedicated,
        )
        if action:
            report.actions.append(action)
        action = _install_action(
            "gpu-amd-extra", t("Instalar los diagnósticos de AMD (opcional)"),
            manager, [(p, n) for p, n in missing if p.optional], optional=True,
        )
        if action:
            report.actions.append(action)

    # --- avisos generales --------------------------------------------------
    if not drivers.opencl_ok and not report.actions:
        report.notes.append(t(
            "No encuentro ninguna plataforma OpenCL activa. Resolve arrancará, "
            "pero puede quejarse de la GPU al abrir un proyecto."
        ))
    return report
