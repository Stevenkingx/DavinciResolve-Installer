"""Renderiza las pantallas de la aplicación como imágenes para el vídeo.

Usa la aplicación de verdad, no maquetas: lo que se ve en el vídeo es
exactamente lo que el usuario se va a encontrar. Se sustituye el nombre de
usuario y la carpeta de trabajo por valores genéricos.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent / "resolve-manager"
OUT = ROOT / "assets"
sys.path.insert(0, str(APP))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication            # noqa: E402

from resolve_manager import i18n                    # noqa: E402
from resolve_manager.core import fixes as fx        # noqa: E402

# Nada personal en un vídeo público.
_real_user = fx.real_user
fx.real_user = lambda: ("user", _real_user()[1], _real_user()[2])

from resolve_manager.core import (archive, installer,     # noqa: E402
                                  packages, system)
from resolve_manager.ui import theme                      # noqa: E402
from resolve_manager.ui.window import (MainWindow, PAGE_DONE,  # noqa: E402
                                       PAGE_PLAN, PAGE_REPAIR, PAGE_RUN)

ZIP = ROOT.parent / "DaVinci_Resolve_Studio_21.1_Linux.zip"
WORKDIR = Path("/home/user/Downloads")
FPS = 30


def clean_machine(report):
    """Un equipo recién instalado: sin Resolve todavía."""
    fresh = copy.deepcopy(report)
    fresh.resolve = system.ResolveInstall(installed=False)
    return fresh


def demo_plan(window, report):
    """Plan típico de una primera instalación en Fedora."""
    info = archive.inspect(ZIP)
    window.info = info
    window.workdir = WORKDIR
    window.edition = "studio"
    window.fixes = fx.detect_fixes(False)
    options = installer.InstallOptions(workdir=WORKDIR, preferred_edition="studio")
    plan = installer.build_plan(info, report, window.fixes, options)

    # En un equipo recién instalado faltan las librerías base. Este paso lo
    # genera el mismo código que en producción, con su texto real.
    manager = packages.manager_for(report.distro)
    base = packages.BASE_PACKAGES[report.distro.family]
    missing = [(p, p.name) for p in base if not p.optional]
    action = packages._install_action(
        "deps-base", i18n.t("Instalar las librerías base que Resolve necesita"),
        manager, missing,
    )
    if action:
        plan.actions.insert(0, action)

    window.plan = plan
    window.situation = installer.assess(info, report)
    window.plan_page.load(window.situation, plan, info, WORKDIR, "rocm", False)
    return plan


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    timings = json.loads((ROOT / "audio" / "timings.json").read_text())

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(theme.ui_font(10))
    app.setStyleSheet(theme.stylesheet())
    i18n.set_language("en")

    report = system.collect()
    fresh = clean_machine(report)

    window = MainWindow()
    window.resize(1360, 1150)
    window.show()
    window.report = fresh
    window.home.set_report(fresh)
    window.home.chooser.select("studio")
    app.processEvents()
    window.grab().save(str(OUT / "home.png"))
    print("  home.png")

    # Geometría real de cada zona, para los planos detalle del vídeo: así los
    # recortes nunca se descuadran aunque cambie la maquetación.
    def region(widget, margin=18):
        top_left = widget.mapTo(window, widget.rect().topLeft())
        return [max(0, top_left.x() - margin), max(0, top_left.y() - margin),
                widget.width() + margin * 2, widget.height() + margin * 2]

    home = window.home
    cards = home.card_system.mapTo(window, home.card_system.rect().topLeft())
    last = home.card_resolve.mapTo(window, home.card_resolve.rect().bottomRight())
    regions = {
        "cards": [cards.x() - 22, cards.y() - 46,
                  last.x() - cards.x() + 44, last.y() - cards.y() + 68],
        "edition": region(home.chooser, 24),
        "drop": region(home.drop, 24),
    }
    (OUT / "regions.json").write_text(json.dumps(regions, indent=2))
    print("  regions.json", regions)

    # La zona de arrastre con un archivo encima: es el estado real del widget,
    # no un montaje.
    home.drop._dragging = True
    home.drop.update()
    app.processEvents()
    window.grab().save(str(OUT / "home_drag.png"))
    home.drop._dragging = False
    home.drop.update()
    print("  home_drag.png")

    plan = demo_plan(window, fresh)
    window.resize(1360, 1000)
    window.stack.setCurrentIndex(PAGE_PLAN)
    app.processEvents()
    window.grab().save(str(OUT / "plan.png"))

    def bbox(first, last, pad_top=44, pad=20):
        a = first.mapTo(window, first.rect().topLeft())
        b = last.mapTo(window, last.rect().bottomRight())
        return [max(0, a.x() - pad), max(0, a.y() - pad_top),
                b.x() - a.x() + pad * 2, b.y() - a.y() + pad_top + pad]

    steps = window.plan_page.steps_holder
    extra = json.loads((OUT / "regions.json").read_text())
    extra["plan_steps"] = bbox(steps.itemAt(0).widget(),
                               steps.itemAt(steps.count() - 1).widget())
    (OUT / "regions.json").write_text(json.dumps(extra, indent=2))
    print("  plan.png + región de pasos", extra["plan_steps"])

    # ---- secuencia animada de la pantalla de ejecución --------------------
    steps = plan.active()
    names = [a.id for a in steps]
    window.run_page.prepare(plan)
    window.stack.setCurrentIndex(PAGE_RUN)
    window.run_page.log.set_expanded(True)

    LOG = [
        (0.10, "$ pkexec resolve-manager-helper"),
        (0.13, "$ dnf install -y libxcrypt-compat ocl-icd"),
        (0.17, "Installing       : libxcrypt-compat-4.5.2-3.fc44.x86_64"),
        (0.20, "Complete!"),
        (0.24, "unpacking... 15%  (1.6 GB)"),
        (0.33, "unpacking... 45%  (4.7 GB)"),
        (0.42, "unpacking... 80%  (8.3 GB)"),
        (0.50, "installer ready at /home/user/Downloads"),
        (0.56, "$ SKIP_PACKAGE_CHECK=1 DaVinci_Resolve_Studio_21.1_Linux.run -i -y -a"),
        (0.62, "Extracting archive..."),
        (0.70, "Installing to /opt/resolve"),
        (0.78, "Copying 12840 files..."),
        (0.88, "moved aside: libglib-2.0.so"),
        (0.91, "moved aside: libgio-2.0.so"),
        (0.94, "ownership fixed: /home/user/.local/share/DaVinciResolve"),
    ]
    # Cuándo empieza y acaba cada paso, en fracción de la escena.
    BOUNDS = [(0.06, 0.22), (0.22, 0.52), (0.52, 0.86), (0.86, 0.93), (0.93, 0.98)]
    bounds = BOUNDS[:len(steps)]

    seconds = timings["10_run"] + 1.2
    frames = int(seconds * FPS)
    weights = [a.weight for a in steps]
    total_weight = sum(weights) or 1

    for index in range(frames):
        t = index / max(frames - 1, 1)
        done_weight = 0.0
        phase = i18n.t("Getting ready") if t < bounds[0][0] else ""
        for i, (start, end) in enumerate(bounds):
            if t >= end:
                window.run_page.steps.set_state(names[i], "ok")
                done_weight += weights[i]
            elif t >= start:
                window.run_page.steps.set_state(names[i], "running")
                done_weight += weights[i] * (t - start) / (end - start)
                phase = steps[i].title
        if phase:
            window.run_page.phase.setText(phase)
        window.run_page.bar.set_value(done_weight / total_weight)

        while LOG and LOG[0][0] <= t:
            window.run_page.log.append(LOG.pop(0)[1])

        app.processEvents()
        window.grab().save(str(OUT / f"run_{index:04d}.png"))
    print(f"  run_*.png ({frames} fotogramas)")

    # ---- resultado --------------------------------------------------------
    window.done_page.show_result(
        True, i18n.t("Todo listo"),
        i18n.t("{what} está instalado y configurado.",
               what="DaVinci Resolve Studio 21.1"),
        notes=[i18n.t("DaVinci Resolve Studio necesita una clave de activación "
                      "o una llave USB. Sin licencia se instalará, pero no "
                      "arrancará.")],
    )
    window.stack.setCurrentIndex(PAGE_DONE)
    app.processEvents()
    window.grab().save(str(OUT / "done.png"))
    extra = json.loads((OUT / "regions.json").read_text())
    extra["done_block"] = bbox(window.done_page.mark, window.done_page.message,
                               pad_top=60, pad=90)
    (OUT / "regions.json").write_text(json.dumps(extra, indent=2))
    print("  done.png")

    # ---- reparación: un equipo con los dos problemas clásicos -------------
    broken = fx.detect_fixes(True)
    for fix in broken:
        if fix.id in ("shield-glib", "fix-perms"):
            fix.status = fx.STATUS_NEEDED
            fix.evidence = fix.evidence or [
                "libglib-2.0.so", "libgio-2.0.so", "libgmodule-2.0.so",
            ] if fix.id == "shield-glib" else [
                "/home/user/.local/share/DaVinciResolve",
            ]
    window.repair_page.load(broken)
    window.stack.setCurrentIndex(PAGE_REPAIR)
    app.processEvents()
    window.grab().save(str(OUT / "repair.png"))
    holder = window.repair_page.holder
    extra = json.loads((OUT / "regions.json").read_text())
    extra["repair_fixes"] = bbox(holder.itemAt(0).widget(),
                                 holder.itemAt(holder.count() - 1).widget())
    (OUT / "regions.json").write_text(json.dumps(extra, indent=2))
    print("  repair.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
