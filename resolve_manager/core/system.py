"""Detección del entorno: distribución, GPU, drivers y DaVinci Resolve instalado.

Todo lo de este módulo se ejecuta SIN privilegios de root. Solo lee.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field

from ..i18n import t
from pathlib import Path

RESOLVE_DIR = Path("/opt/resolve")
WELCOME_TXT = RESOLVE_DIR / "docs" / "Welcome.txt"
README_HTML = RESOLVE_DIR / "docs" / "ReadMe.html"


def run(cmd: list[str], timeout: int = 15) -> tuple[int, str]:
    """Ejecuta un comando y devuelve (código, salida). Nunca lanza excepcion."""
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return 127, ""


# --------------------------------------------------------------------------
# Distribución
# --------------------------------------------------------------------------

FAMILY_BY_ID = {
    "fedora": "fedora",
    "rhel": "fedora",
    "centos": "fedora",
    "rocky": "fedora",
    "almalinux": "fedora",
    "nobara": "fedora",
    "bazzite": "fedora",
    "debian": "debian",
    "ubuntu": "debian",
    "linuxmint": "debian",
    "pop": "debian",
    "zorin": "debian",
    "elementary": "debian",
    "arch": "arch",
    "manjaro": "arch",
    "endeavouros": "arch",
    "cachyos": "arch",
    "garuda": "arch",
    "opensuse": "suse",
    "opensuse-tumbleweed": "suse",
    "opensuse-leap": "suse",
    "sles": "suse",
}


@dataclass
class Distro:
    id: str = "unknown"
    version_id: str = ""
    pretty: str = "Linux"
    id_like: list[str] = field(default_factory=list)
    immutable: bool = False  # Silverblue / Bazzite / SteamOS: /opt no es escribible igual

    @property
    def family(self) -> str:
        if self.id in FAMILY_BY_ID:
            return FAMILY_BY_ID[self.id]
        for like in self.id_like:
            if like in FAMILY_BY_ID:
                return FAMILY_BY_ID[like]
        return "unknown"

    @property
    def supported(self) -> bool:
        return self.family != "unknown"


def detect_distro() -> Distro:
    data: dict[str, str] = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    data[key.strip()] = value.strip().strip('"').strip("'")
            break
        except OSError:
            continue

    distro = Distro(
        id=data.get("ID", "unknown").lower(),
        version_id=data.get("VERSION_ID", ""),
        pretty=data.get("PRETTY_NAME") or data.get("NAME") or "Linux",
        id_like=[x.lower() for x in data.get("ID_LIKE", "").split()],
    )
    # Sistemas atómicos: /usr es de solo lectura y dnf no instala en vivo.
    distro.immutable = Path("/run/ostree-booted").exists()
    return distro


# --------------------------------------------------------------------------
# GPU
# --------------------------------------------------------------------------

VENDOR_BY_PCI = {"10de": "nvidia", "1002": "amd", "1022": "amd", "8086": "intel"}

# Clases PCI que corresponden a una tarjeta gráfica.
_GPU_CLASS_RE = re.compile(r"\[030[02]\]")
_PCI_LINE_RE = re.compile(
    r"^(?P<slot>\S+)\s+.*?\[(?P<cls>[0-9a-f]{4})\]:\s+(?P<desc>.*?)\s+"
    r"\[(?P<vendor>[0-9a-f]{4}):(?P<device>[0-9a-f]{4})\]",
    re.IGNORECASE,
)


@dataclass
class Gpu:
    vendor: str = "unknown"      # nvidia | amd | intel | unknown
    name: str = "GPU desconocida"
    slot: str = ""
    pci_id: str = ""
    vram_mb: int = 0             # 0 = desconocido
    integrated: bool = False

    @property
    def label(self) -> str:
        tag = "integrada" if self.integrated else "dedicada"
        return f"{self.name} ({tag})"


def _vram_for_slot(slot: str) -> int:
    """Lee la VRAM desde sysfs (solo amdgpu la expone de forma fiable)."""
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*")):
        device = card / "device"
        try:
            if os.path.basename(os.path.realpath(device)) not in slot:
                continue
        except OSError:
            continue
        for name in ("mem_info_vram_total", "mem_info_vis_vram_total"):
            try:
                return int((device / name).read_text().strip()) // (1024 * 1024)
            except (OSError, ValueError):
                continue
    return 0


# Prefijos corporativos que lspci antepone y que al usuario no le dicen nada.
_VENDOR_PREFIX_RE = re.compile(
    r"^(NVIDIA Corporation|Advanced Micro Devices, Inc\.|Intel Corporation|ATI Technologies Inc)\s*",
    re.IGNORECASE,
)


def clean_gpu_name(desc: str) -> str:
    """'NVIDIA Corporation GB203 [GeForce RTX 5080]' -> 'GeForce RTX 5080'."""
    text = re.sub(r"\s*\[[0-9a-f]{4}:[0-9a-f]{4}\]\s*$", "", desc).strip()
    text = _VENDOR_PREFIX_RE.sub("", text)
    text = re.sub(r"\[AMD/ATI\]\s*", "", text)

    brackets = re.findall(r"\[([^\]]+)\]", text)
    if brackets:
        model = brackets[-1].strip()
        rest = re.sub(r"\s*\[[^\]]*\]\s*", " ", text).strip()
        # El nombre comercial va delante; el nombre en clave, entre parentesis.
        if rest and rest.lower() not in model.lower():
            return f"{model} ({rest})"
        return model
    return text or desc.strip()


def detect_gpus() -> list[Gpu]:
    rc, out = run(["lspci", "-nn"])
    if rc != 0:
        return []

    gpus: list[Gpu] = []
    for line in out.splitlines():
        if not _GPU_CLASS_RE.search(line):
            continue
        m = _PCI_LINE_RE.match(line)
        if not m:
            continue
        vendor_id = m.group("vendor").lower()
        name = clean_gpu_name(m.group("desc"))
        gpu = Gpu(
            vendor=VENDOR_BY_PCI.get(vendor_id, "unknown"),
            name=name,
            slot=m.group("slot"),
            pci_id=f"{vendor_id}:{m.group('device').lower()}",
        )
        gpu.vram_mb = _vram_for_slot(gpu.slot)
        # Heuristica: menos de 2 GB de VRAM propia => gráfica integrada al CPU.
        if gpu.vendor == "intel":
            gpu.integrated = True
        elif gpu.vram_mb and gpu.vram_mb < 2048:
            gpu.integrated = True
        elif gpu.vendor == "amd" and re.search(
            r"granite ridge|raphael|cezanne|renoir|phoenix|rembrandt|barcelo|lucienne|hawk point|strix",
            name,
            re.IGNORECASE,
        ):
            gpu.integrated = True
        gpus.append(gpu)
    return gpus


def has_vendor(gpus: list[Gpu], vendor: str, dedicated_only: bool = False) -> bool:
    return any(g.vendor == vendor and (not dedicated_only or not g.integrated) for g in gpus)


# --------------------------------------------------------------------------
# Drivers y cómputo (OpenCL / CUDA)
# --------------------------------------------------------------------------

@dataclass
class DriverStatus:
    nvidia_driver: str = ""       # versión según nvidia-smi
    nvidia_kernel_ok: bool = False
    rocm_present: bool = False
    opencl_platforms: list[str] = field(default_factory=list)
    cuda_present: bool = False

    @property
    def opencl_ok(self) -> bool:
        return bool(self.opencl_platforms)


def detect_drivers() -> DriverStatus:
    status = DriverStatus()

    rc, out = run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    if rc == 0 and out.strip():
        status.nvidia_driver = out.strip().splitlines()[0].strip()
        status.nvidia_kernel_ok = True

    if shutil.which("clinfo"):
        rc, out = run(["clinfo", "-l"], timeout=20)
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if line.lower().startswith("platform #"):
                    _, _, label = line.partition(":")
                    label = label.strip()
                    if label:
                        status.opencl_platforms.append(label)

    # ROCm se reparte de forma distinta en cada distro; la señal fiable de que
    # está operativo es que exponga su plataforma OpenCL.
    status.rocm_present = any(
        "amd accelerated parallel processing" in p.lower() or "rocm" in p.lower()
        for p in status.opencl_platforms
    ) or (bool(shutil.which("rocminfo")) and Path("/opt/rocm").exists())

    status.cuda_present = any(
        Path(p).exists()
        for p in ("/usr/lib64/libcuda.so.1", "/usr/lib/x86_64-linux-gnu/libcuda.so.1")
    )
    return status


# --------------------------------------------------------------------------
# DaVinci Resolve instalado
# --------------------------------------------------------------------------

_VERSION_RE = re.compile(r"DaVinci Resolve(?:\s+Studio)?\s+(\d+(?:\.\d+)+)")


@dataclass
class ResolveInstall:
    installed: bool = False
    version: str = ""
    studio: bool = False
    path: Path = RESOLVE_DIR

    @property
    def edition(self) -> str:
        return "Studio" if self.studio else "Free"

    @property
    def label(self) -> str:
        if not self.installed:
            return t("No instalado")
        version = self.version or t("versión desconocida")
        return f"DaVinci Resolve {self.edition} {version}"


def detect_resolve() -> ResolveInstall:
    binary = RESOLVE_DIR / "bin" / "resolve"
    if not binary.exists():
        return ResolveInstall(installed=False)

    info = ResolveInstall(installed=True)

    # Welcome.txt es el origen más fiable: lo escribe el propio instalador.
    for source in (WELCOME_TXT, README_HTML):
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _VERSION_RE.search(text)
        if m:
            info.version = m.group(1)
            info.studio = "Studio" in m.group(0)
            break

    # Welcome.txt no siempre dice "Studio", así que hay que preguntar en otros
    # sitios: primero al sistema, y si calla, a nuestra propia memoria de lo que
    # instalamos la última vez.
    if not info.studio:
        info.studio = (RESOLVE_DIR / "bin" / "resolve-studio").exists() or any(
            RESOLVE_DIR.glob("DaVinci Resolve Studio*")
        )
    if not info.studio:
        from . import state

        record = state.last_install()
        if record.get("studio") and record.get("version") == info.version:
            info.studio = True
    return info


# --------------------------------------------------------------------------
# Versiones y disco
# --------------------------------------------------------------------------

def parse_version(text: str) -> tuple[int, ...]:
    """'21.0.4' -> (21, 0, 4). Sirve para comparar de forma numerica."""
    parts = re.findall(r"\d+", text or "")
    return tuple(int(p) for p in parts) or (0,)


def compare_versions(a: str, b: str) -> int:
    """-1 si a < b, 0 si iguales, 1 si a > b."""
    va, vb = parse_version(a), parse_version(b)
    size = max(len(va), len(vb))
    va += (0,) * (size - len(va))
    vb += (0,) * (size - len(vb))
    return (va > vb) - (va < vb)


def free_space_gb(path: str | Path) -> float:
    target = Path(path)
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        return shutil.disk_usage(target).free / (1024 ** 3)
    except OSError:
        return 0.0


# --------------------------------------------------------------------------
# Informe completo
# --------------------------------------------------------------------------

@dataclass
class SystemReport:
    distro: Distro
    gpus: list[Gpu]
    drivers: DriverStatus
    resolve: ResolveInstall

    def as_text(self) -> str:
        """Informe en texto plano, para el botón 'Copiar diagnóstico'."""
        def row(label: str, value: str) -> str:
            return f"{t(label):<13}: {value}"

        platforms = ", ".join(self.drivers.opencl_platforms)
        lines = [
            "=== " + t("Diagnóstico de DaVinci Resolve Manager") + " ===",
            row("Distribución", f"{self.distro.pretty} (id={self.distro.id}, "
                                f"{t('familia')}={self.distro.family})"),
            row("Kernel", os.uname().release),
            row("Resolve", self.resolve.label),
            row("Driver NVIDIA", self.drivers.nvidia_driver or t("no detectado")),
            row("ROCm", t("sí") if self.drivers.rocm_present else t("no")),
            row("OpenCL", platforms or t("sin plataformas")),
            f"{t('GPUs'):<13}:",
        ]
        for gpu in self.gpus or []:
            vram = f", {gpu.vram_mb} MB VRAM" if gpu.vram_mb else ""
            lines.append(f"  - [{gpu.vendor}] {gpu.name} ({gpu.pci_id}{vram})")
        if not self.gpus:
            lines.append("  - " + t("ninguna detectada"))
        return "\n".join(lines)


def collect() -> SystemReport:
    return SystemReport(
        distro=detect_distro(),
        gpus=detect_gpus(),
        drivers=detect_drivers(),
        resolve=detect_resolve(),
    )
