"""Traducción español / inglés.

El idioma de origen del código es el español: `t()` devuelve el propio texto
cuando el idioma activo es "es", y lo busca en la tabla EN cuando es "en". Si
falta una entrada devuelve el original, así que una traducción incompleta nunca
rompe la interfaz: como mucho se ve una frase en español.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

LANGUAGES = {"es": "Español", "en": "English"}
DEFAULT = "en"

CONFIG_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    / "davinci-resolve-manager"
    / "config.json"
)

_current: str | None = None


# --------------------------------------------------------------------------
# Selección de idioma
# --------------------------------------------------------------------------

def detect_language() -> str:
    """Idioma del sistema. Español si la configuración regional lo es."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return "es" if value.lower().startswith("es") else "en"
    return DEFAULT


def _read_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_config(data: dict) -> None:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # que no se pueda guardar la preferencia no es motivo para fallar


def current() -> str:
    global _current
    if _current is None:
        saved = _read_config().get("language")
        _current = saved if saved in LANGUAGES else detect_language()
    return _current


def set_language(language: str) -> None:
    global _current
    if language not in LANGUAGES:
        return
    _current = language
    data = _read_config()
    data["language"] = language
    _write_config(data)


# --------------------------------------------------------------------------
# Traducción
# --------------------------------------------------------------------------

def N_(text: str) -> str:
    """Marca un texto para traducir más tarde, sin traducirlo ahora.

    Se usa en tablas de datos a nivel de módulo, que se construyen una sola vez
    al importar: ahí hay que guardar el original y traducir al mostrarlo.
    """
    return text


def t(text: str, **kwargs) -> str:
    """Traduce `text` al idioma activo y aplica los sustituciones con format()."""
    out = text if current() == "es" else EN.get(text, text)
    return out.format(**kwargs) if kwargs else out


# --------------------------------------------------------------------------
# Tabla español -> inglés
# --------------------------------------------------------------------------

EN: dict[str, str] = {
    # -- interfaz general --------------------------------------------------
    "DaVinci Resolve Manager": "DaVinci Resolve Manager",
    "Instala, actualiza y repara Resolve en Linux":
        "Install, update and repair Resolve on Linux",
    "Estado de tu equipo": "Your system",
    "Sistema": "System",
    "Tarjeta gráfica": "Graphics card",
    "Driver y cómputo": "Driver and compute",
    "DaVinci Resolve": "DaVinci Resolve",
    "GPUs": "GPUs",
    "Instalar o actualizar": "Install or update",
    "Qué edición quieres": "Which edition you want",
    "Qué voy a hacer": "What I am going to do",
    "Ajustes": "Settings",
    "Empezar": "Start",
    "Atrás": "Back",
    "Cancelar": "Cancel",
    "Cancelando…": "Cancelling…",
    "Cambiar": "Change",
    "Preparando": "Getting ready",
    "Trabajando": "Working",
    "Analizando…": "Scanning…",
    "Volver a analizar": "Scan again",
    "Copiar diagnóstico": "Copy diagnostics",
    "Copiar registro": "Copy log",
    "Copiado": "Copied",
    "Mostrar detalles técnicos": "Show technical details",
    "Ocultar detalles técnicos": "Hide technical details",
    "Revisar y reparar": "Check and repair",
    "Revisar y reparar instalación": "Check and repair installation",
    "Aplicar seleccionados": "Apply selected",
    "Deshacer este arreglo": "Undo this fix",
    "Volver al inicio": "Back to start",
    "Abrir DaVinci Resolve": "Open DaVinci Resolve",
    "Todo listo": "All set",
    "No se pudo completar": "Could not finish",
    "No se puede continuar": "Cannot continue",
    "necesario": "required",
    "hace falta": "needed",
    "ya aplicado": "already applied",
    "no aplica": "not applicable",
    "sí": "yes",
    "no": "no",
    "familia": "family",
    "no detectado": "not detected",
    "sin plataformas": "no platforms",
    "sin OpenCL": "no OpenCL",
    "ninguna detectada": "none detected",
    "No detectada": "Not detected",
    "No instalado": "Not installed",
    "versión desconocida": "unknown version",
    "Tu sistema": "Your system",

    # -- zona de arrastre y edición ----------------------------------------
    "Arrastra aquí el archivo de DaVinci Resolve": "Drop your DaVinci Resolve file here",
    "el .zip que descargaste de Blackmagic  ·  o pulsa para buscarlo":
        "the .zip you downloaded from Blackmagic  ·  or click to browse",
    "Arrastra aquí {file}": "Drop {file} here",
    "o pulsa para buscarlo en tu equipo": "or click to browse your computer",
    "Elige el paquete de DaVinci Resolve": "Choose the DaVinci Resolve package",
    "Paquete de Resolve (*.zip *.run);;Todos los archivos (*)":
        "Resolve package (*.zip *.run);;All files (*)",
    "Descarga el paquete de Linux desde blackmagicdesign.com y suéltalo aquí sin "
    "descomprimir. Sirve tanto para instalar por primera vez como para actualizar: "
    "tus proyectos no se tocan.":
        "Download the Linux package from blackmagicdesign.com and drop it here "
        "without unzipping it. This works both for a first install and for an "
        "update: your projects are left alone.",
    "¿Todavía no lo has descargado?": "Haven't downloaded it yet?",
    "Descargar de Blackmagic Design": "Download from Blackmagic Design",
    "Gratuita": "Free",
    "DaVinci_Resolve_<versión>_Linux.zip": "DaVinci_Resolve_<version>_Linux.zip",
    "DaVinci_Resolve_Studio_<versión>_Linux.zip":
        "DaVinci_Resolve_Studio_<version>_Linux.zip",
    "Studio": "Studio",
    "Gratis, sin licencia ni registro": "Free, no licence and no sign-up",
    "De pago: necesita clave de activación o llave USB":
        "Paid: needs an activation key or a USB dongle",
    "La versión gratuita es un programa completo de edición, color, efectos y "
    "audio. Para la mayoría de la gente es la correcta. Exporta hasta 4K a 60 fps.":
        "The free edition is a complete editing, colour, effects and audio "
        "application. For most people it is the right one. It exports up to 4K "
        "at 60 fps.",
    "Studio añade las herramientas de IA (Magic Mask, seguimiento facial), "
    "reducción de ruido, HDR, exportación por encima de 4K y colaboración en red. "
    "Si no tienes licencia, no arrancará.":
        "Studio adds the AI tools (Magic Mask, face tracking), noise reduction, "
        "HDR, export above 4K and networked collaboration. Without a licence it "
        "will not start.",
    "Elegiste la edición {wanted}, pero el paquete que soltaste es el de la "
    "edición {got}. Se instalará {got}: si no es lo que quieres, descarga el "
    "archivo correcto ({hint}).":
        "You picked the {wanted} edition, but the package you dropped is the "
        "{got} one. {got} will be installed: if that is not what you want, "
        "download the right file ({hint}).",
    "DaVinci Resolve Studio necesita una clave de activación o una llave USB. "
    "Sin licencia se instalará, pero no arrancará.":
        "DaVinci Resolve Studio needs an activation key or a USB dongle. Without "
        "a licence it will install, but it will not start.",

    # -- estado del equipo --------------------------------------------------
    "También detecté: {others}": "Also detected: {others}",
    "No pude leer las tarjetas con lspci. Instala «pciutils».":
        "Could not read your graphics cards with lspci. Install \u201cpciutils\u201d.",
    "Distribución no reconocida: instalaré Resolve, pero las dependencias tendrás "
    "que ponerlas tú.":
        "Unrecognised distribution: I will install Resolve, but you will have to "
        "add the dependencies yourself.",
    "Suelta el paquete abajo para instalarlo.": "Drop the package below to install it.",
    "NVIDIA sin driver": "NVIDIA with no driver",
    "Radeon sin ROCm": "Radeon without ROCm",
    "OpenCL activo: {platforms}": "OpenCL active: {platforms}",
    "El driver de NVIDIA no responde: Resolve no va a acelerar.":
        "The NVIDIA driver is not responding: Resolve will not accelerate.",
    "Sin OpenCL, Resolve se quejará de la GPU al abrir proyectos.":
        "Without OpenCL, Resolve will complain about the GPU when opening projects.",
    "Tienes una NVIDIA sin driver propietario activo. Es la causa número uno de "
    "que Resolve no arranque. Puedo instalarlo durante la instalación, o desde "
    "«Revisar y reparar».":
        "You have an NVIDIA card with no proprietary driver active. That is the "
        "number one reason Resolve fails to start. I can install it during the "
        "installation, or from \u201cCheck and repair\u201d.",
    "No hay ninguna plataforma OpenCL activa en este equipo. Resolve necesita "
    "OpenCL (o CUDA) para funcionar.":
        "There is no active OpenCL platform on this computer. Resolve needs "
        "OpenCL (or CUDA) to work.",
    "Diagnóstico de DaVinci Resolve Manager": "DaVinci Resolve Manager diagnostics",
    "Distribución": "Distribution",
    "Kernel": "Kernel",
    "Resolve": "Resolve",
    "Driver NVIDIA": "NVIDIA driver",
    "ROCm": "ROCm",
    "OpenCL": "OpenCL",

    # -- situación -----------------------------------------------------------
    "Instalar {what}": "Install {what}",
    "Actualizar a {what}": "Update to {what}",
    "Reinstalar {what}": "Reinstall {what}",
    "Volver a {what}": "Roll back to {what}",
    "No hay ninguna versión de DaVinci Resolve en este equipo. Voy a hacer la "
    "instalación completa, drivers incluidos.":
        "There is no version of DaVinci Resolve on this computer. I will do the "
        "full installation, drivers included.",
    "No consigo comparar las versiones con seguridad, así que trataré esto como "
    "una reinstalación limpia sobre la actual.":
        "I cannot compare the versions reliably, so I will treat this as a clean "
        "reinstall over the current one.",
    "Tienes la {current} y este paquete trae la {new}.":
        "You have {current} and this package brings {new}.",
    "Además cambia de edición: {before} → {after}.":
        "It also changes edition: {before} → {after}.",
    "Tus proyectos y tu base de datos no se tocan.":
        "Your projects and your database are left alone.",
    "Ya tienes exactamente la {current} instalada. Reinstalar sirve para reparar "
    "una instalación que se rompió.":
        "You already have exactly {current} installed. Reinstalling is for "
        "repairing an installation that broke.",
    "Tienes la {current}, que es MÁS NUEVA que la {new} de este paquete. Instalar "
    "una versión anterior puede impedir que abras proyectos guardados con la "
    "versión nueva.":
        "You have {current}, which is NEWER than the {new} in this package. "
        "Installing an older version may stop you from opening projects saved "
        "with the newer one.",
    "Vas a instalar una versión más antigua que la que ya tienes. Haz copia de tu "
    "base de datos de proyectos antes de continuar.":
        "You are about to install an older version than the one you have. Back up "
        "your project database before continuing.",
    "Instalar una versión anterior": "Install an older version",
    "Vas a instalar una versión más antigua que la que tienes.\n\nLos proyectos "
    "guardados con la versión nueva pueden dejar de abrirse. ¿Seguro que quieres "
    "continuar?":
        "You are about to install an older version than the one you have.\n\n"
        "Projects saved with the newer version may stop opening. Are you sure you "
        "want to continue?",

    # -- pasos del plan -------------------------------------------------------
    "Descomprimir el instalador ({size} GB)": "Unpack the installer ({size} GB)",
    "El .zip guarda el instalador sin comprimir, así que esto es básicamente una "
    "copia de disco. Es el paso más lento.":
        "The .zip stores the installer uncompressed, so this is basically a disk "
        "copy. It is the slowest step.",
    "Ejecuta el instalador oficial de Blackmagic en modo silencioso.":
        "Runs Blackmagic's official installer in silent mode.",
    "Comando:": "Command:",
    "Desinstalar DaVinci Resolve": "Uninstall DaVinci Resolve",
    "Usa el desinstalador oficial. No borra tus proyectos ni tu base de datos, "
    "que viven en tu carpeta personal.":
        "Uses the official uninstaller. It does not delete your projects or your "
        "database, which live in your home folder.",

    # -- dependencias ---------------------------------------------------------
    "Instalar las librerías base que Resolve necesita":
        "Install the base libraries Resolve needs",
    "Instalar herramientas de diagnóstico (opcional)":
        "Install diagnostic tools (optional)",
    "Instalar el driver de NVIDIA y CUDA": "Install the NVIDIA driver and CUDA",
    "Instalar {label} para tu Radeon": "Install {label} for your Radeon",
    "Instalar los diagnósticos de AMD (opcional)": "Install AMD diagnostics (optional)",
    "ROCm (OpenCL de AMD)": "ROCm (AMD's OpenCL)",
    "OpenCL de Mesa": "Mesa OpenCL",
    "Activar los repositorios RPM Fusion": "Enable the RPM Fusion repositories",
    "Fedora no distribuye el driver de NVIDIA por motivos de licencia. RPM Fusion "
    "es el repositorio de confianza que sí lo tiene.":
        "Fedora does not ship the NVIDIA driver for licensing reasons. RPM Fusion "
        "is the trusted repository that does have it.",
    "Provee libcrypt.so.1, que Resolve necesita para arrancar y que las "
    "distribuciones actuales ya no instalan por defecto.":
        "Provides libcrypt.so.1, which Resolve needs in order to start and which "
        "current distributions no longer install by default.",
    "Cargador OpenCL: es como Resolve encuentra tu GPU.":
        "OpenCL loader: this is how Resolve finds your GPU.",
    "Herramienta de diagnóstico de OpenCL.": "OpenCL diagnostic tool.",
    "Permite montar el instalador AppImage sin descomprimirlo entero.":
        "Lets the AppImage installer mount itself without unpacking it whole.",
    "Librería de utilidades que usa Resolve.": "Utility library that Resolve uses.",
    "Complemento de libapr1.": "Companion to libapr1.",
    "Complemento de apr.": "Companion to apr.",
    "Audio ALSA para la página Fairlight.": "ALSA audio for the Fairlight page.",
    "Cursores XCB que exige la interfaz Qt de Resolve.":
        "XCB cursors required by Resolve's Qt interface.",
    "Runtime OpenCL de AMD. Es LA pieza que falta cuando Resolve dice "
    "«no GPU detected» con una Radeon.":
        "AMD's OpenCL runtime. It is THE missing piece when Resolve says "
        "\u201cno GPU detected\u201d with a Radeon.",
    "Capa de cómputo HIP que Resolve usa para acelerar efectos.":
        "HIP compute layer that Resolve uses to accelerate effects.",
    "Comprueba que ROCm ve tu tarjeta.": "Checks that ROCm can see your card.",
    "Diagnóstico de OpenCL específico de AMD.": "AMD-specific OpenCL diagnostics.",
    "Runtime OpenCL de AMD, necesario para que Resolve vea la Radeon.":
        "AMD's OpenCL runtime, needed for Resolve to see the Radeon.",
    "Driver OpenCL de Mesa (rusticl/clover). Alternativa ligera a ROCm, útil en "
    "gráficas integradas y APU.":
        "Mesa's OpenCL driver (rusticl/clover). A lightweight alternative to "
        "ROCm, useful on integrated graphics and APUs.",
    "Driver OpenCL de Mesa: da soporte OpenCL a las Radeon sin ROCm.":
        "Mesa's OpenCL driver: gives Radeon cards OpenCL support without ROCm.",
    "Driver OpenCL de Mesa para Radeon.": "Mesa's OpenCL driver for Radeon.",
    "Driver propietario de NVIDIA, que se recompila solo con cada kernel.":
        "NVIDIA's proprietary driver, which rebuilds itself with every kernel.",
    "CUDA y el ICD de OpenCL de NVIDIA: sin esto Resolve no acelera nada.":
        "NVIDIA's CUDA and OpenCL ICD: without this Resolve accelerates nothing.",
    "Driver propietario de NVIDIA.": "NVIDIA's proprietary driver.",
    "ICD de OpenCL de NVIDIA.": "NVIDIA's OpenCL ICD.",
    "Driver propietario de NVIDIA (DKMS, sobrevive a cambios de kernel).":
        "NVIDIA's proprietary driver (DKMS, survives kernel changes).",
    "Utilidades y librería CUDA de NVIDIA.": "NVIDIA's utilities and CUDA library.",
    "CUDA y OpenCL de NVIDIA.": "NVIDIA's CUDA and OpenCL.",
    "No reconozco el gestor de paquetes de esta distribución, así que no puedo "
    "instalar dependencias automáticamente. La instalación de Resolve sí puede "
    "continuar.":
        "I do not recognise this distribution's package manager, so I cannot "
        "install dependencies automatically. Installing Resolve itself can still "
        "go ahead.",
    "Este sistema es inmutable (tipo Silverblue o Bazzite). Las dependencias hay "
    "que instalarlas con «rpm-ostree install», así que aquí se omiten.":
        "This is an immutable system (Silverblue or Bazzite style). Dependencies "
        "have to be installed with \u201crpm-ostree install\u201d, so they are "
        "skipped here.",
    "Tras instalar el driver de NVIDIA hay que REINICIAR el equipo antes de abrir "
    "Resolve.":
        "After installing the NVIDIA driver you must REBOOT before opening Resolve.",
    "Detecté una GPU NVIDIA, pero el driver propietario no responde (nvidia-smi "
    "falla). Resolve no va a acelerar nada así. Marca la casilla del driver de "
    "NVIDIA si quieres que lo instale.":
        "I detected an NVIDIA GPU, but the proprietary driver is not responding "
        "(nvidia-smi fails). Resolve will not accelerate anything like this. Tick "
        "the NVIDIA driver box if you want me to install it.",
    "El driver de NVIDIA está activo, pero no encuentro libcuda. Instala el "
    "paquete CUDA del driver para que Resolve acelere.":
        "The NVIDIA driver is active, but I cannot find libcuda. Install the "
        "driver's CUDA package so that Resolve accelerates.",
    "En esta distribución, ROCm requiere añadir a mano el repositorio oficial de "
    "AMD, así que usaré el driver OpenCL de Mesa.":
        "On this distribution ROCm requires adding AMD's official repository by "
        "hand, so I will use Mesa's OpenCL driver instead.",
    "No encuentro ninguna plataforma OpenCL activa. Resolve arrancará, pero puede "
    "quejarse de la GPU al abrir un proyecto.":
        "I cannot find any active OpenCL platform. Resolve will start, but it may "
        "complain about the GPU when opening a project.",

    # -- reparaciones ---------------------------------------------------------
    "Apartar las librerías glib que trae Resolve":
        "Set aside the glib libraries bundled with Resolve",
    "Resolve incluye su propia copia (antigua) de libglib, libgio y libgmodule. "
    "En las distribuciones actuales esa copia choca con la del sistema y hace que "
    "el programa se cierre solo al abrir un diálogo de archivos o al exportar. Se "
    "mueven a «disabled-libraries» para que use las del sistema. Es reversible "
    "con un clic.":
        "Resolve ships its own (old) copy of libglib, libgio and libgmodule. On "
        "current distributions that copy clashes with the system one and makes "
        "the program quit by itself when opening a file dialog or exporting. They "
        "are moved to \u201cdisabled-libraries\u201d so the system ones get used. "
        "One click undoes it.",
    "Devolverte la propiedad de tus carpetas de Resolve":
        "Give your Resolve folders back to you",
    "El instalador se ejecuta como root y a veces deja carpetas de configuración "
    "a nombre de root. Cuando pasa, Resolve arranca y se cierra al instante sin "
    "ningún mensaje. Se devuelven a «{user}».":
        "The installer runs as root and sometimes leaves configuration folders "
        "owned by root. When that happens, Resolve starts and closes instantly "
        "with no message at all. They are handed back to \u201c{user}\u201d.",
    "Reparar el acceso directo del menú de aplicaciones":
        "Repair the application menu shortcut",
    "Rehace el lanzador de DaVinci Resolve para que aparezca en el menú con su "
    "icono y abra los proyectos con doble clic.":
        "Rebuilds the DaVinci Resolve launcher so it shows up in the menu with "
        "its icon and opens projects on double-click.",
    "Restaurar las librerías glib originales de Resolve":
        "Restore Resolve's original glib libraries",
    "Devuelve las librerías desde «disabled-libraries» a su sitio.":
        "Moves the libraries back from \u201cdisabled-libraries\u201d to where "
        "they were.",
    "Estos son los arreglos conocidos que hacen que DaVinci Resolve funcione bien "
    "en Linux. Marco solos los que hacen falta en tu equipo.":
        "These are the known fixes that make DaVinci Resolve behave on Linux. I "
        "tick only the ones your computer actually needs.",
    "Afecta a: {items}": "Affects: {items}",
    "Nada que hacer": "Nothing to do",
    "No has marcado ninguna reparación.": "You have not ticked any repair.",

    # -- ajustes --------------------------------------------------------------
    "Carpeta de trabajo para descomprimir:": "Working folder for unpacking:",
    "Carpeta donde descomprimir el instalador":
        "Folder to unpack the installer into",
    "Cómputo para GPU AMD:": "Compute backend for AMD GPUs:",
    "ROCm (recomendado para Radeon dedicadas)":
        "ROCm (recommended for discrete Radeon cards)",
    "OpenCL de Mesa (más ligero, bueno para APU integradas)":
        "Mesa OpenCL (lighter, good for integrated APUs)",
    "Instalar también el driver propietario de NVIDIA":
        "Also install NVIDIA's proprietary driver",
    "Requiere reiniciar el equipo al terminar.":
        "Requires a reboot when it finishes.",

    # -- ejecución ------------------------------------------------------------
    "Puedes dejar esto trabajando. El paso más largo es descomprimir el "
    "instalador: son más de 10 GB.":
        "You can leave this running. The longest step is unpacking the "
        "installer: it is over 10 GB.",
    "Descomprimiendo el instalador": "Unpacking the installer",
    "descomprimiendo… {percent}%  ({gb} GB)": "unpacking… {percent}%  ({gb} GB)",
    "instalador listo en {path}": "installer ready at {path}",
    "Pidiendo permisos de administrador": "Requesting administrator permission",
    "Esperando tu autorización": "Waiting for your authorisation",
    "Comprobando el resultado": "Checking the result",
    "Confirma la ventana de contraseña del sistema para que pueda instalar. Es la "
    "única vez que te la va a pedir.":
        "Confirm the system password dialog so I can install. This is the only "
        "time you will be asked.",
    "Permisos de administrador": "Administrator permission",
    "Escribe tu contraseña de usuario para poder instalar:":
        "Type your user password so the installation can run:",
    "Si cancelas a medias puede quedar una instalación incompleta.\n\n¿Cancelar "
    "de todas formas?":
        "Cancelling halfway can leave an incomplete installation.\n\nCancel anyway?",
    "Hay una instalación en curso": "An installation is in progress",
    "Si cierras ahora puede quedar a medias. ¿Cerrar igualmente?":
        "Closing now may leave it half done. Close anyway?",
    "Hay una operación en curso": "An operation is in progress",
    "Espera a que termine para cambiar de idioma.":
        "Wait for it to finish before switching language.",
    "Espera": "Hold on",
    "Todavía estoy analizando el equipo.": "I am still scanning your computer.",
    "No puedo usar ese archivo": "I cannot use that file",
    "No encuentro Resolve": "I cannot find Resolve",
    "No existe {path}.": "{path} does not exist.",
    "{what} está instalado y configurado.": "{what} is installed and configured.",
    "Se instaló un driver de kernel: reinicia el equipo antes de abrir DaVinci "
    "Resolve.":
        "A kernel driver was installed: reboot before opening DaVinci Resolve.",
    "Se va a instalar un driver de kernel: reinicia el equipo antes de abrir "
    "DaVinci Resolve.":
        "A kernel driver is about to be installed: reboot before opening DaVinci "
        "Resolve.",

    # -- errores --------------------------------------------------------------
    "No encuentro el archivo:": "I cannot find the file:",
    "Ese archivo no me sirve.\n\nSuelta aquí el .zip que descargaste de "
    "Blackmagic Design (por ejemplo DaVinci_Resolve_Studio_21.1_Linux.zip) o el "
    ".run que hay dentro.":
        "That file is no use to me.\n\nDrop the .zip you downloaded from "
        "Blackmagic Design here (for example "
        "DaVinci_Resolve_Studio_21.1_Linux.zip), or the .run inside it.",
    "Este .zip no contiene ningún instalador .run.\n\nAsegúrate de haber "
    "descargado el paquete de Linux desde blackmagicdesign.com y no el de Windows "
    "o macOS.":
        "This .zip contains no .run installer.\n\nMake sure you downloaded the "
        "Linux package from blackmagicdesign.com and not the Windows or macOS one.",
    "El .zip está dañado o incompleto.\n\nLo más probable es que la descarga se "
    "cortara. Descárgalo otra vez.":
        "The .zip is damaged or incomplete.\n\nMost likely the download was cut "
        "short. Download it again.",
    "No hay espacio suficiente en {workdir}.\n\nHacen falta unos {needed} GB "
    "libres para descomprimir el instalador y solo quedan {available} GB. Libera "
    "espacio o elige otra carpeta de trabajo.":
        "Not enough space in {workdir}.\n\nUnpacking the installer needs about "
        "{needed} GB free and only {available} GB are left. Free up space or pick "
        "another working folder.",
    "Quedan solo {free} GB libres en /opt y la instalación necesita unos {needed} GB.":
        "Only {free} GB are free in /opt and the installation needs about {needed} GB.",
    "Estás en un sistema inmutable (Silverblue, Bazzite, SteamOS…). Resolve se "
    "instalará en /opt, pero las dependencias del sistema tendrás que añadirlas "
    "con rpm-ostree.":
        "You are on an immutable system (Silverblue, Bazzite, SteamOS…). Resolve "
        "will be installed in /opt, but you will have to add the system "
        "dependencies with rpm-ostree.",
    "Este equipo no tiene FUSE, así que el instalador se auto-extraerá en "
    "{workdir}. Necesitarás el doble de espacio temporal.":
        "This computer has no FUSE, so the installer will self-extract into "
        "{workdir}. You will need twice the temporary space.",
    "Extracción cancelada.": "Unpacking cancelled.",
    "No pude descomprimir el instalador:": "I could not unpack the installer:",
    "No hay ningún paquete que descomprimir.": "There is no package to unpack.",
    "Operación cancelada.": "Operation cancelled.",
    "Cancelado por el usuario.": "Cancelled by the user.",
    "Error inesperado:": "Unexpected error:",
    "Fallo en:": "Failed at:",
    "La instalación no pudo completarse.": "The installation could not be completed.",
    "Los pasos terminaron sin error, pero no encuentro DaVinci Resolve en "
    "/opt/resolve. Revisa los detalles técnicos.":
        "The steps finished without error, but I cannot find DaVinci Resolve in "
        "/opt/resolve. Check the technical details.",
    "Este sistema no tiene ni pkexec ni sudo, así que no puedo pedir permisos de "
    "administrador. Ejecuta la aplicación con sudo.":
        "This system has neither pkexec nor sudo, so I cannot request "
        "administrator permission. Run the application with sudo.",
    "No encuentro forma de pedir permisos de administrador (ni pkexec ni sudo).":
        "I cannot find a way to request administrator permission (no pkexec, no "
        "sudo).",
    "No pude lanzar el ayudante:": "I could not start the helper:",
    "No se autorizó la operación.\n\nSe canceló el diálogo de contraseña, o tu "
    "usuario no tiene permisos de administrador en este equipo.":
        "The operation was not authorised.\n\nThe password dialog was "
        "cancelled, or your user does not have administrator rights on this "
        "computer.",
    "No encontré pkexec/sudo para elevar privilegios.":
        "I could not find pkexec or sudo to elevate privileges.",
    "Contraseña incorrecta.": "Wrong password.",
    "El ayudante falló (código {rc}):": "The helper failed (code {rc}):",
    "El ayudante terminó inesperadamente (código {rc}).":
        "The helper exited unexpectedly (code {rc}).",
}
