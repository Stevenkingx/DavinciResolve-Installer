"""Guion del vídeo tutorial, en inglés y en español.

Cada escena lleva su locución y la especificación de lo que se ve. Las
duraciones salen del audio real, no de aquí. El campo `visual` es el mismo en
los dos idiomas: solo cambia el texto.
"""

from __future__ import annotations

import os
import sys

REPO = "github.com/Stevenkingx/DavinciResolve-Installer"

SCENES_EN = [
    dict(
        id="01_hook", visual="terminal_error", headline="",
        text="If you have ever tried to install DaVinci Resolve on Linux, "
             "there is a good chance you have seen this. The installer stops, "
             "tells you a package called zlib is missing, and cancels. "
             "That is all you get.",
    ),
    dict(
        id="02_why", visual="terminal_error_annotated",
        headline="The package is not actually missing",
        text="But the package is not missing. Resolve's installer looks for a "
             "name that modern distributions no longer use. On Fedora it is "
             "called zlib-ng-compat. The check is simply wrong, and it stops "
             "the installation before it even starts.",
    ),
    dict(
        id="03_three", visual="three_problems",
        headline="Three things stand between you and a working Resolve",
        text="Get past that, and two more problems are waiting. Your graphics "
             "card needs the right compute runtime, and it is a different one "
             "for AMD and for NVIDIA. And Resolve ships its own old copies of "
             "three system libraries that make it quit when you export, or "
             "when you open a file dialog.",
    ),
    dict(
        id="04_meet", visual="app_home", headline="DaVinci Resolve Manager",
        text="This app handles all three. It is small, free and open source. "
             "You drag the zip file you downloaded from Blackmagic onto the "
             "window, and it takes care of the rest.",
    ),
    dict(
        id="05_install", visual="terminal_install",
        headline="Installing it takes three commands",
        text="Getting it is three commands. Clone the repository, run install "
             "dot s h, and it adds itself to your applications menu. No root "
             "needed here: everything goes into your home folder.",
    ),
    dict(
        id="06_scan", visual="zoom_cards",
        headline="First, it reads your system",
        text="When it opens, it checks your machine. Your distribution, your "
             "graphics card, whether the driver is actually responding, and "
             "which OpenCL platforms are active. If something here is wrong, "
             "Resolve will not run, and you find out before you install "
             "anything.",
    ),
    dict(
        id="07_edition", visual="zoom_edition",
        headline="Free or Studio",
        text="Then you pick your edition. Free and Studio are two different "
             "downloads. Studio needs an activation key or a USB dongle: "
             "without a licence it will install, but it will not start. The "
             "app links you to the right file, and warns you if you drop the "
             "other one.",
    ),
    dict(
        id="08_drop", visual="drop_animation",
        headline="Drag the zip onto the window",
        text="Now drag the zip onto the window. Do not unzip it first.",
    ),
    dict(
        id="09_plan", visual="app_plan",
        headline="It tells you what it will do, before doing it",
        text="Before touching anything, it shows you the whole plan. Here it "
             "will unpack the installer, run it with that broken package check "
             "disabled, set aside the conflicting libraries, and fix the "
             "folder ownership. Every step explains why it is there. The "
             "optional ones you can simply untick.",
    ),
    dict(
        id="10_run", visual="app_run",
        headline="One password, then it works through the list",
        text="Press start and enter your password once. Everything that needs "
             "permission is sent in a single batch, so you are never asked "
             "again. If you want to watch, the technical details drawer shows "
             "the full output of every command as it runs.",
    ),
    dict(
        id="11_done", visual="app_done",
        headline="Installed, patched and ready",
        text="When it finishes, Resolve is installed, patched and ready to "
             "open. Your projects and your database were never touched. They "
             "live in your home folder, not in opt.",
    ),
    dict(
        id="12_repair", visual="app_repair",
        headline="Already installed and misbehaving?",
        text="If Resolve is already installed and misbehaving, check and "
             "repair applies the fixes on their own. Starts and closes "
             "instantly with no message? That is folder ownership. Quits when "
             "you export? That is the libraries. It ticks only the ones your "
             "machine actually needs.",
    ),
    dict(
        id="13_outro", visual="outro", headline="",
        text="It is tested on Fedora, and it covers Debian, Ubuntu, Arch and "
             "openSUSE as well. Free and open source. You will find it at the "
             "link on screen.",
    ),
]

SCENES_ES = [
    dict(
        id="01_hook", visual="terminal_error", headline="",
        text="Si alguna vez has intentado instalar DaVinci Resolve en Linux, "
             "es muy probable que hayas visto esto. El instalador se detiene, "
             "te dice que falta un paquete llamado zlib, y cancela. Eso es "
             "todo lo que te dice.",
    ),
    dict(
        id="02_why", visual="terminal_error_annotated",
        headline="El paquete no falta",
        text="Pero el paquete no falta. El instalador de Resolve busca un "
             "nombre que las distribuciones actuales ya no usan. En Fedora se "
             "llama zlib-ene-ge-compat. La comprobación simplemente está mal, "
             "y detiene la instalación antes de que empiece.",
    ),
    dict(
        id="03_three", visual="three_problems",
        headline="Tres cosas te separan de un Resolve funcionando",
        text="Y si logras pasar eso, te esperan dos problemas más. Tu tarjeta "
             "gráfica necesita el runtime de cómputo correcto, y es distinto "
             "para AMD y para NVIDIA. Además, Resolve trae sus propias copias "
             "antiguas de tres librerías del sistema que hacen que se cierre "
             "al exportar, o al abrir un diálogo de archivos.",
    ),
    dict(
        id="04_meet", visual="app_home", headline="DaVinci Resolve Manager",
        text="Esta aplicación se encarga de las tres. Es pequeña, gratuita y "
             "de código abierto. Arrastras a la ventana el archivo zip que "
             "descargaste de Blackmagic, y ella hace el resto.",
    ),
    dict(
        id="05_install", visual="terminal_install",
        headline="Instalarla son tres comandos",
        text="Conseguirla son tres comandos. Clonas el repositorio, ejecutas "
             "install punto ese hache, y se añade sola a tu menú de "
             "aplicaciones. Aquí no hace falta root: todo va a tu carpeta "
             "personal.",
    ),
    dict(
        id="06_scan", visual="zoom_cards",
        headline="Primero revisa tu equipo",
        text="Al abrirse, revisa tu máquina. Tu distribución, tu tarjeta "
             "gráfica, si el driver responde de verdad, y qué plataformas "
             "OpenCL están activas. Si algo de esto está mal, Resolve no va a "
             "funcionar, y te enteras antes de instalar nada.",
    ),
    dict(
        id="07_edition", visual="zoom_edition",
        headline="Gratuita o Studio",
        text="Después eliges tu edición. Gratuita y Studio son dos descargas "
             "distintas. Studio necesita una clave de activación o una llave "
             "USB: sin licencia se instala, pero no arranca. La aplicación te "
             "enlaza al archivo correcto, y te avisa si sueltas el otro.",
    ),
    dict(
        id="08_drop", visual="drop_animation",
        headline="Arrastra el zip a la ventana",
        text="Ahora arrastra el zip a la ventana. No lo descomprimas antes.",
    ),
    dict(
        id="09_plan", visual="app_plan",
        headline="Te dice lo que va a hacer, antes de hacerlo",
        text="Antes de tocar nada, te muestra el plan completo. Aquí va a "
             "descomprimir el instalador, ejecutarlo con esa comprobación rota "
             "desactivada, apartar las librerías que chocan, y arreglar los "
             "permisos de las carpetas. Cada paso explica por qué está ahí. "
             "Los opcionales los puedes desmarcar.",
    ),
    dict(
        id="10_run", visual="app_run",
        headline="Una contraseña, y trabaja sola",
        text="Pulsas empezar y escribes tu contraseña una sola vez. Todo lo "
             "que necesita permisos se manda de golpe, así que no te la vuelve "
             "a pedir. Y si quieres mirar, el desplegable de detalles técnicos "
             "muestra la salida completa de cada comando mientras corre.",
    ),
    dict(
        id="11_done", visual="app_done",
        headline="Instalado, parcheado y listo",
        text="Cuando termina, Resolve está instalado, parcheado y listo para "
             "abrir. Tus proyectos y tu base de datos no se tocaron. Viven en "
             "tu carpeta personal, no en opt.",
    ),
    dict(
        id="12_repair", visual="app_repair",
        headline="¿Ya lo tienes instalado y se porta mal?",
        text="Si Resolve ya está instalado y se porta mal, revisar y reparar "
             "aplica los arreglos por su cuenta. ¿Arranca y se cierra al "
             "instante sin ningún mensaje? Eso son los permisos de las "
             "carpetas. ¿Se cierra al exportar? Eso son las librerías. Marca "
             "solo los que tu equipo necesita de verdad.",
    ),
    dict(
        id="13_outro", visual="outro", headline="",
        text="Está probado en Fedora, y cubre también Debian, Ubuntu, Arch y "
             "openSUSE. Gratuito y de código abierto. Lo encuentras en el "
             "enlace que aparece en pantalla.",
    ),
]

ALL = {"en": SCENES_EN, "es": SCENES_ES}

# Textos sueltos que dibuja el compositor sobre las imágenes.
LABELS = {
    "en": {
        "annotation": "Fedora ships this as  zlib-ng-compat",
        "phase_ready": "Getting ready",
    },
    "es": {
        "annotation": "Fedora lo llama  zlib-ng-compat",
        "phase_ready": "Preparando",
    },
}


def language() -> str:
    """Idioma del pase actual: argumento de línea de órdenes o VIDEO_LANG."""
    for arg in sys.argv[1:]:
        if arg in ALL:
            return arg
    value = os.environ.get("VIDEO_LANG", "en")
    return value if value in ALL else "en"


def scenes(lang: str | None = None) -> list[dict]:
    return ALL[lang or language()]


# Compatibilidad con la primera versión del pipeline.
SCENES = scenes()
