"""Imágenes que no salen de la aplicación: terminales y tarjetas explicativas.

Los textos de terminal son salida real capturada, no inventada.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script import language          # noqa: E402

ROOT = Path(__file__).resolve().parent
LANG = language()
OUT = ROOT / "assets" / LANG

INTER = "/usr/share/fonts/rsms-inter-fonts/Inter-{}.ttf"
DISPLAY = "/usr/share/fonts/rsms-inter-fonts/InterDisplay-{}.ttf"
MONO = "/usr/share/fonts/google-noto/NotoSansMono-{}.ttf"

BG        = (14, 16, 20)
TERM_BG   = (18, 20, 26)
TERM_BAR  = (31, 35, 43)
BORDER    = (47, 52, 65)
TEXT      = (233, 235, 239)
MUTED     = (154, 162, 177)
FAINT     = (108, 116, 133)
ACCENT    = (255, 181, 63)
GREEN     = (74, 222, 128)
RED       = (248, 113, 113)
BLUE      = (96, 165, 250)


def font(path: str, weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path.format(weight), size)


def rounded(size, radius, fill, outline=None, width=1) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius, fill=fill,
        outline=outline, width=width)
    return img


# --------------------------------------------------------------------------
# Terminal
# --------------------------------------------------------------------------

def terminal(lines, width=1280, title="user@fedora:~", pad=28,
             line_height=30, size=19) -> Image.Image:
    """`lines` es una lista de (texto, color) o de texto suelto."""
    mono = font(MONO, "Regular", size)
    monob = font(MONO, "Bold", size)
    bar = 44
    height = bar + pad * 2 + line_height * len(lines)

    img = rounded((width, height), 12, TERM_BG, BORDER, 1)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, width - 1, bar + 12], 12, fill=TERM_BAR)
    draw.rectangle([0, bar, width - 1, bar + 12], fill=TERM_BG)
    draw.line([0, bar, width, bar], fill=BORDER)
    for i, colour in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        draw.ellipse([20 + i * 22, bar // 2 - 6, 32 + i * 22, bar // 2 + 6], fill=colour)
    draw.text((width // 2, bar // 2), title, font=font(INTER, "Medium", 15),
              fill=FAINT, anchor="mm")

    # La fuente monoespaciada no trae el glifo ✓, así que ese carácter se
    # dibuja con Inter y el resto de la línea sigue en mono, sin desalinearse.
    tick = font(INTER, "Bold", size - 1)

    y = bar + pad
    for entry in lines:
        text, colour, bold = entry if isinstance(entry, tuple) else (entry, MUTED, False)
        face = monob if bold else mono
        if "✓" in text:
            before, _, after = text.partition("✓")
            x = pad + draw.textlength(before, font=face)
            draw.text((x, y + 1), "✓", font=tick, fill=colour)
            draw.text((pad, y), before + " " + after, font=face, fill=colour)
        else:
            draw.text((pad, y), text, font=face, fill=colour)
        y += line_height
    return img


def terminal_error() -> Image.Image:
    # Salida literal del instalador oficial en Fedora 44.
    lines = [
        ("$ ./DaVinci_Resolve_Studio_21.1_Linux.run", TEXT, True),
        ("egrep: warning: egrep is obsolescent; using grep -E", FAINT, False),
        ("", MUTED, False),
        ("Error: Missing or outdated system packages detected.", RED, True),
        ("", MUTED, False),
        ("Please install the following missing packages:", MUTED, False),
        ("    zlib", ACCENT, True),
        ("", MUTED, False),
        ("Use SKIP_PACKAGE_CHECK=1 to bypass the system package check.", FAINT, False),
        ("", MUTED, False),
        ("***********************", FAINT, False),
        ("Installation cancelled.", RED, True),
    ]
    return terminal(lines, width=1280)


# install.sh es bilingüe: esto es su salida real en cada idioma.
INSTALL_OUTPUT = {
    "en": ["Cloning into 'DavinciResolve-Installer'...",
           "  Installing DaVinci Resolve Manager",
           "python3 3.14", "PyQt6 available", "Command installed",
           "Icon generated", "Menu entry created",
           "Done. Look for it in your applications menu."],
    "es": ["Cloning into 'DavinciResolve-Installer'...",
           "  Instalando DaVinci Resolve Manager",
           "python3 3.14", "PyQt6 disponible", "Comando instalado",
           "Icono generado", "Entrada de menú creada",
           "Listo. Búscalo en tu menú de aplicaciones."],
}


def terminal_install() -> Image.Image:
    clone, heading, *steps = INSTALL_OUTPUT[LANG]
    lines = [
        ("$ git clone https://github.com/Stevenkingx/DavinciResolve-Installer.git",
         TEXT, True),
        (clone, FAINT, False),
        ("$ cd DavinciResolve-Installer", TEXT, True),
        ("$ ./install.sh", TEXT, True),
        ("", MUTED, False),
        (heading, MUTED, False),
        ("", MUTED, False),
    ]
    for step in steps[:-1]:
        lines.append((f"  ✓ {step}", GREEN, False))
    lines.append(("", MUTED, False))
    lines.append((f"  ✓ {steps[-1]}", GREEN, False))
    return terminal(lines, width=1320)


# --------------------------------------------------------------------------
# Tarjeta de los tres problemas
# --------------------------------------------------------------------------

def three_problems() -> Image.Image:
    width, card_h, gap = 1500, 168, 22
    items = {
        "en": [
            ("01", "The package check is wrong", ACCENT,
             "It looks for a package called zlib. Fedora ships zlib-ng-compat,\n"
             "so the installer aborts before it starts."),
            ("02", "The GPU runtime is missing", BLUE,
             "Radeon cards need ROCm, NVIDIA needs the proprietary driver and CUDA.\n"
             "Without it Resolve reports “no GPU detected”."),
            ("03", "Bundled libraries clash", RED,
             "Resolve ships old copies of libglib, libgio and libgmodule that make it\n"
             "quit when you export or open a file dialog."),
        ],
        "es": [
            ("01", "La comprobación de paquetes está mal", ACCENT,
             "Busca un paquete llamado zlib. Fedora lo distribuye como\n"
             "zlib-ng-compat, así que el instalador aborta antes de empezar."),
            ("02", "Falta el runtime de la GPU", BLUE,
             "Las Radeon necesitan ROCm; NVIDIA, el driver propietario y CUDA.\n"
             "Sin eso, Resolve dice «no GPU detected»."),
            ("03", "Las librerías que trae dentro chocan", RED,
             "Resolve incluye copias antiguas de libglib, libgio y libgmodule que\n"
             "lo cierran al exportar o al abrir un diálogo de archivos."),
        ],
    }[LANG]
    height = len(items) * card_h + (len(items) - 1) * gap
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    num_f = font(DISPLAY, "Bold", 44)
    title_f = font(DISPLAY, "SemiBold", 34)
    body_f = font(INTER, "Regular", 23)

    for index, (num, title, colour, body) in enumerate(items):
        y = index * (card_h + gap)
        card = rounded((width, card_h), 14, (29, 32, 39, 255), (38, 42, 51), 1)
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle([0, 0, 4, card_h - 1], 2, fill=colour)
        draw.text((46, card_h // 2), num, font=num_f, fill=colour, anchor="lm")
        draw.text((140, 42), title, font=title_f, fill=TEXT)
        draw.multiline_text((140, 92), body, font=body_f, fill=MUTED, spacing=10)
        img.paste(card, (0, y), card)
    return img


# --------------------------------------------------------------------------
# Cierre
# --------------------------------------------------------------------------

def outro() -> Image.Image:
    width, height = 1500, 520
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.text((width // 2, 40), "DaVinci Resolve Manager",
              font=font(DISPLAY, "Bold", 62), fill=TEXT, anchor="ma")
    subtitle = {"en": "Install · Update · Repair",
                "es": "Instalar · Actualizar · Reparar"}[LANG]
    draw.text((width // 2, 128), subtitle,
              font=font(INTER, "Regular", 30), fill=MUTED, anchor="ma")

    url = "github.com/Stevenkingx/DavinciResolve-Installer"
    url_f = font(MONO, "Regular", 30)
    box_w = int(draw.textlength(url, font=url_f)) + 72
    box = rounded((box_w, 78), 12, (42, 35, 24, 255), ACCENT, 2)
    ImageDraw.Draw(box).text((box_w // 2, 39), url, font=url_f, fill=ACCENT, anchor="mm")
    img.paste(box, ((width - box_w) // 2, 210), box)

    chips = {"en": ["Free & open source", "MIT licence", "English · Español"],
             "es": ["Gratuito y de código abierto", "Licencia MIT",
                    "English · Español"]}[LANG]
    chip_f = font(INTER, "Medium", 22)
    widths = [int(draw.textlength(c, font=chip_f)) + 44 for c in chips]
    x = (width - sum(widths) - 16 * (len(chips) - 1)) // 2
    for chip, chip_w in zip(chips, widths):
        pill = rounded((chip_w, 48), 24, (29, 32, 39, 255), (47, 52, 65), 1)
        ImageDraw.Draw(pill).text((chip_w // 2, 24), chip, font=chip_f,
                                  fill=MUTED, anchor="mm")
        img.paste(pill, (x, 336), pill)
        x += chip_w + 16
    return img


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in (("term_error", terminal_error),
                          ("term_install", terminal_install),
                          ("three_problems", three_problems),
                          ("outro", outro)):
        image = builder()
        image.save(OUT / f"{name}.png")
        print(f"  [{LANG}] {name}.png  {image.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
