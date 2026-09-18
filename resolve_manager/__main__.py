"""Punto de entrada: python3 -m resolve_manager"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "Falta PyQt6. Instalalo con uno de estos comandos, según tu distro:\n"
            "  Fedora        : sudo dnf install python3-pyqt6\n"
            "  Ubuntu/Debian : sudo apt install python3-pyqt6\n"
            "  Arch          : sudo pacman -S python-pyqt6\n"
            "  openSUSE      : sudo zypper install python3-qt6\n"
        )
        return 1

    from .ui import theme
    from .ui.widgets import app_icon
    from .ui.window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("DaVinci Resolve Manager")
    app.setApplicationDisplayName("DaVinci Resolve Manager")
    app.setDesktopFileName("davinci-resolve-manager")
    app.setStyle("Fusion")
    app.setFont(theme.ui_font(10))
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
