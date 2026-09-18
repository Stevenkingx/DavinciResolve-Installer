#!/usr/bin/env bash
# Installs DaVinci Resolve Manager into your applications menu.
# Instala DaVinci Resolve Manager en tu menú de aplicaciones.
# No root needed: everything goes into your home folder.
set -euo pipefail

APP_ID="davinci-resolve-manager"
APP_NAME="DaVinci Resolve Manager"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

# ---------------------------------------------------------------- idioma
# El script habla el idioma del sistema, igual que la aplicación.
case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
    es*) LANG_ES=1 ;;
    *)   LANG_ES=0 ;;
esac

say() {  # say <english> <español>
    if [[ "${LANG_ES}" == "1" ]]; then printf '%s' "$2"; else printf '%s' "$1"; fi
}

c_ok()   { printf '\033[1;32m  ✓\033[0m %s\n' "$1"; }
c_info() { printf '\033[1;34m  →\033[0m %s\n' "$1"; }
c_warn() { printf '\033[1;33m  !\033[0m %s\n' "$1"; }
c_err()  { printf '\033[1;31m  ✗\033[0m %s\n' "$1" >&2; }

# ---------------------------------------------------------------- uninstall
if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "${BIN_DIR}/${APP_ID}" \
          "${DESKTOP_DIR}/${APP_ID}.desktop" \
          "${ICON_DIR}/${APP_ID}.png"
    rm -rf "${HOME}/.cache/${APP_ID}"
    command -v update-desktop-database >/dev/null 2>&1 &&
        update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
    c_ok "$(say 'Uninstalled. (DaVinci Resolve itself was not touched.)' \
                'Desinstalado. (DaVinci Resolve no se ha tocado.)')"
    exit 0
fi

echo
echo "  $(say 'Installing' 'Instalando') ${APP_NAME}"
echo

# ------------------------------------------------------------------- python
if ! command -v python3 >/dev/null 2>&1; then
    c_err "$(say 'python3 is not installed. Install it and try again.' \
                 'No hay python3 en este sistema. Instálalo y vuelve a intentarlo.')"
    exit 1
fi
c_ok "python3 $(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"

# --------------------------------------------------------------------- PyQt6
if ! python3 -c 'import PyQt6.QtWidgets' >/dev/null 2>&1; then
    c_warn "$(say 'PyQt6 is missing; it is the interface library.' \
                  'Falta PyQt6, que es la biblioteca de la interfaz.')"

    if   command -v dnf     >/dev/null 2>&1; then PKG="sudo dnf install -y python3-pyqt6"
    elif command -v apt-get >/dev/null 2>&1; then PKG="sudo apt-get install -y python3-pyqt6"
    elif command -v pacman  >/dev/null 2>&1; then PKG="sudo pacman -S --needed --noconfirm python-pyqt6"
    elif command -v zypper  >/dev/null 2>&1; then PKG="sudo zypper --non-interactive install python3-qt6"
    else PKG=""; fi

    if [[ -n "${PKG}" ]]; then
        c_info "$(say 'I am going to run:' 'Voy a ejecutar:') ${PKG}"
        read -r -p "  $(say 'Continue? [Y/n] ' '¿Continuar? [S/n] ')" answer
        if [[ ! "${answer}" =~ ^[NnDd] ]]; then
            eval "${PKG}"
        else
            c_err "$(say 'Without PyQt6 the application cannot start.' \
                         'Sin PyQt6 la aplicación no puede arrancar.')"
            exit 1
        fi
    else
        c_err "$(say 'Unknown package manager. Please install PyQt6 by hand.' \
                     'No reconozco tu gestor de paquetes. Instala PyQt6 a mano.')"
        exit 1
    fi
fi
c_ok "$(say 'PyQt6 available' 'PyQt6 disponible')"

# ---------------------------------------------------------------- launchers
mkdir -p "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}"

# The package runs from where it lives, so updating it is just copying the new
# folder over this one; the launcher does not change.
cat > "${BIN_DIR}/${APP_ID}" <<LAUNCHER
#!/usr/bin/env bash
cd "${SRC_DIR}" || { echo "Cannot find ${SRC_DIR}" >&2; exit 1; }
exec python3 -m resolve_manager "\$@"
LAUNCHER
chmod +x "${BIN_DIR}/${APP_ID}"
c_ok "$(say 'Command installed at' 'Comando instalado en') ${BIN_DIR}/${APP_ID}"

# The icon is generated with the very same code the window uses.
python3 - "${SRC_DIR}" "${ICON_DIR}/${APP_ID}.png" <<'PYICON'
import os, sys

src_dir, target = sys.argv[1], sys.argv[2]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, src_dir)

from PyQt6.QtWidgets import QApplication

app = QApplication([])
from resolve_manager.ui.widgets import app_icon

app_icon(256).pixmap(256, 256).save(target)
PYICON
c_ok "$(say 'Icon generated' 'Icono generado')"

cat > "${DESKTOP_DIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
GenericName=DaVinci Resolve installer
GenericName[es]=Instalador de DaVinci Resolve
Comment=Install, update and repair DaVinci Resolve on Linux
Comment[es]=Instala, actualiza y repara DaVinci Resolve en Linux
Exec=${BIN_DIR}/${APP_ID}
Icon=${APP_ID}
Terminal=false
Categories=AudioVideo;Video;Settings;
Keywords=davinci;resolve;blackmagic;video;install;update;instalar;actualizar;
StartupNotify=true
DESKTOP
chmod +x "${DESKTOP_DIR}/${APP_ID}.desktop"
command -v update-desktop-database >/dev/null 2>&1 &&
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
c_ok "$(say 'Menu entry created' 'Entrada de menú creada')"

echo
c_ok "$(say "Done. Look for «${APP_NAME}» in your applications menu." \
             "Listo. Búscalo como «${APP_NAME}» en tu menú de aplicaciones.")"
if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    c_warn "$(say "${BIN_DIR} is not in your PATH; the menu entry works anyway." \
                  "${BIN_DIR} no está en tu PATH; desde el menú funcionará igual.")"
fi
echo "  $(say 'You can also start it with:' 'También puedes abrirlo con:')  ${BIN_DIR}/${APP_ID}"
echo
