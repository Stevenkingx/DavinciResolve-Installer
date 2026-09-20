# Títulos y descripciones para publicar el vídeo

Pensados para que los encuentre quien está buscando el error, no para quien ya
conoce el proyecto. El texto del error aparece literal a propósito: es lo que
la gente copia y pega en el buscador.

---

## Español

### Título (recomendado)

```
DaVinci Resolve en Linux: soluciona el error zlib e instálalo sin terminal
```

Alternativas:

```
"Installation cancelled" en DaVinci Resolve Linux: la solución (Fedora, Ubuntu, Arch)
```

```
Por qué DaVinci Resolve no instala en Linux — y cómo arreglarlo en 4 minutos
```

### Descripción

```
¿El instalador de DaVinci Resolve se te para justo aquí?

    Error: Missing or outdated system packages detected.
    Please install the following missing packages:
        zlib
    Installation cancelled.

No te falta ningún paquete. El instalador de Blackmagic busca un nombre que las
distribuciones actuales ya no usan: en Fedora ese paquete se llama
zlib-ng-compat. La comprobación está mal, y aborta la instalación antes de
empezar.

En este vídeo te enseño una aplicación gratuita y de código abierto que se
encarga de todo: arrastras a la ventana el .zip que descargaste de Blackmagic y
ella hace el resto.

QUÉ RESUELVE

• El error de zlib — ejecuta el instalador oficial con la comprobación rota
  desactivada (SKIP_PACKAGE_CHECK=1), en modo silencioso.
• La GPU — instala ROCm si tienes Radeon, o el driver propietario y CUDA si
  tienes NVIDIA (activando RPM Fusion en Fedora). Si ya te funcionan, no toca
  nada.
• Los cierres inesperados — Resolve trae copias antiguas de libglib, libgio y
  libgmodule que lo cierran al exportar o al abrir un diálogo de archivos. Las
  aparta, y puedes deshacerlo con un clic.
• Los permisos — el instalador corre como root y deja carpetas tuyas a nombre
  de root. Eso es lo que hace que Resolve arranque y se cierre al instante sin
  ningún mensaje.

Te pide la contraseña UNA sola vez, y te enseña la lista completa de lo que va
a hacer antes de tocar nada.

INSTALARLA

    git clone https://github.com/Stevenkingx/DavinciResolve-Installer.git
    cd DavinciResolve-Installer
    ./install.sh

DESCARGAS

Proyecto (gratis, código abierto, licencia MIT):
https://github.com/Stevenkingx/DavinciResolve-Installer

DaVinci Resolve (web oficial de Blackmagic):
https://www.blackmagicdesign.com/support/family/davinci-resolve-and-fusion

CAPÍTULOS

0:00 El error que te trajo aquí
0:15 Por qué falla (no falta ningún paquete)
0:35 Los otros dos problemas
0:59 La solución: DaVinci Resolve Manager
1:11 Instalar la herramienta (3 comandos)
1:28 Revisa tu equipo y tu GPU
1:47 Gratuita o Studio: cuál elegir
2:10 Arrastrar el .zip y ver el plan
2:37 La instalación, paso a paso
2:56 Listo: Resolve instalado
3:09 Reparar una instalación rota
3:30 Enlaces

PREGUNTAS FRECUENTES

¿Resolve arranca y se cierra al instante, sin decir nada?
Son los permisos de ~/.local/share/DaVinciResolve. Usa "Revisar y reparar".

¿Se te cierra al exportar o al abrir un diálogo de archivos?
Es el conflicto de libglib. Usa "Revisar y reparar".

¿Dice "no GPU detected"?
Te falta el runtime de OpenCL de tu marca. La app te lo dice en la tarjeta
"Driver y cómputo" y te lo instala.

¿Instalaste Studio y no arranca?
Studio necesita clave de activación o llave USB. Sin licencia, descarga la
edición Gratuita.

¿Instalaste el driver de NVIDIA y sigue sin ir?
Hay que reiniciar: el driver es un módulo del kernel y no se carga hasta el
siguiente arranque.

¿Se pierden mis proyectos al actualizar?
No. Viven en tu carpeta personal, no en /opt/resolve. La aplicación no los toca.

Probado en Fedora 44. Cubre también Debian, Ubuntu, Arch y openSUSE.
La aplicación está en español y en inglés.

#DaVinciResolve #Linux #Fedora #Ubuntu #ArchLinux #DavinciResolveLinux
#EdicionDeVideo #CodigoAbierto #Blackmagic #Tutorial #NVIDIA #AMD #ROCm
#LinuxEspañol #Debian #openSUSE
```

### Etiquetas (campo de tags)

```
davinci resolve linux, davinci resolve fedora, davinci resolve no instala,
error zlib davinci resolve, installation cancelled davinci resolve,
missing or outdated system packages, instalar davinci resolve linux,
davinci resolve ubuntu, davinci resolve arch, davinci resolve se cierra solo,
davinci resolve no abre linux, davinci resolve no gpu detected,
skip_package_check, zlib-ng-compat, davinci resolve studio linux,
editar video en linux, rocm davinci resolve, davinci resolve nvidia linux
```

---

## English

### Title (recommended)

```
DaVinci Resolve on Linux: fix the zlib error and install it without the terminal
```

Alternatives:

```
"Installation cancelled" in DaVinci Resolve Linux — here's the actual fix
```

```
Why DaVinci Resolve won't install on Linux — and how to fix it in 3 minutes
```

### Description

```
Does the DaVinci Resolve installer stop right here?

    Error: Missing or outdated system packages detected.
    Please install the following missing packages:
        zlib
    Installation cancelled.

No package is missing. Blackmagic's installer looks for a name that modern
distributions no longer use: on Fedora that package is called zlib-ng-compat.
The check is simply wrong, and it aborts before the install even starts.

This video shows a free, open-source app that handles all of it: you drag the
.zip you downloaded from Blackmagic onto the window, and it does the rest.

WHAT IT FIXES

• The zlib error — runs the official installer with the broken check disabled
  (SKIP_PACKAGE_CHECK=1), silently.
• Your GPU — installs ROCm for Radeon, or the proprietary driver and CUDA for
  NVIDIA (enabling RPM Fusion on Fedora). If yours already work, it touches
  nothing.
• The random crashes — Resolve ships old copies of libglib, libgio and
  libgmodule that make it quit when you export or open a file dialog. It sets
  them aside, and one click undoes it.
• Folder ownership — the installer runs as root and leaves your own folders
  owned by root. That is why Resolve sometimes starts and vanishes with no
  message at all.

It asks for your password ONCE, and shows you the full list of what it is about
to do before touching anything.

INSTALL IT

    git clone https://github.com/Stevenkingx/DavinciResolve-Installer.git
    cd DavinciResolve-Installer
    ./install.sh

LINKS

Project (free, open source, MIT licence):
https://github.com/Stevenkingx/DavinciResolve-Installer

DaVinci Resolve (official Blackmagic download):
https://www.blackmagicdesign.com/support/family/davinci-resolve-and-fusion

CHAPTERS

0:00 The error that brought you here
0:14 Why it fails (no package is missing)
0:30 The other two problems
0:50 The fix: DaVinci Resolve Manager
1:02 Installing the tool (3 commands)
1:14 It checks your system and GPU
1:33 Free or Studio: which one
1:52 Dragging the .zip and the plan
2:16 The install, step by step
2:32 Done: Resolve installed
2:44 Repairing a broken install
3:04 Links

FAQ

Resolve starts and closes instantly, with no message?
That's the permissions on ~/.local/share/DaVinciResolve. Use "Check and repair".

It quits when exporting or opening a file dialog?
That's the libglib clash. Use "Check and repair".

It says "no GPU detected"?
Your card's OpenCL runtime is missing. The app tells you in the "Driver and
compute" card, and installs it.

Installed Studio and it won't start?
Studio needs an activation key or a USB dongle. Without a licence, download the
Free edition instead.

Installed the NVIDIA driver and it still doesn't work?
Reboot. The driver is a kernel module and isn't loaded until the next boot.

Do I lose my projects when updating?
No. They live in your home folder, not in /opt/resolve. The app never touches
them.

Tested on Fedora 44. Also covers Debian, Ubuntu, Arch and openSUSE.
The app itself is available in English and Spanish.

#DaVinciResolve #Linux #Fedora #Ubuntu #ArchLinux #DavinciResolveLinux
#VideoEditing #OpenSource #Blackmagic #Tutorial #NVIDIA #AMD #ROCm #Debian
#openSUSE
```

### Tags

```
davinci resolve linux, davinci resolve fedora, davinci resolve won't install,
davinci resolve zlib error, installation cancelled davinci resolve,
missing or outdated system packages, install davinci resolve linux,
davinci resolve ubuntu, davinci resolve arch, davinci resolve crashes on export,
davinci resolve won't open linux, davinci resolve no gpu detected,
skip_package_check, zlib-ng-compat, davinci resolve studio linux,
video editing on linux, rocm davinci resolve, davinci resolve nvidia linux
```
