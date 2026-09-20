"""Miniatura de YouTube (1280x720).

La regla que manda aquí es la legibilidad a 240 píxeles de ancho, que es como
la ve la mayoría de la gente en el móvil: pocas palabras y muy grandes. La
historia es la misma en las dos versiones — el error que reconoces al instante,
tachado, y la palabra que buscabas — porque eso es lo que hace clic a quien
lleva horas peleándose con esto.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from script import language

ROOT = Path(__file__).resolve().parent
LANG = language()
OUT = ROOT / "assets" / LANG / "thumbnail.png"

W, H = 1280, 720

INTER = "/usr/share/fonts/rsms-inter-fonts/Inter-{}.ttf"
DISPLAY = "/usr/share/fonts/rsms-inter-fonts/InterDisplay-{}.ttf"
MONO = "/usr/share/fonts/google-noto/NotoSansMono-{}.ttf"

BG = (11, 12, 16)
WHITE = (245, 247, 250)
MUTED = (150, 158, 173)
RED = (248, 90, 90)
GREEN = (74, 230, 130)
AMBER = (255, 181, 63)

TEXTS = {
    "en": {
        "kicker": "DAVINCI RESOLVE   ·   FEDORA · UBUNTU · ARCH",
        "bad": "zlib ERROR",
        "good": "FIXED",
        "sub": "no terminal · one password",
    },
    "es": {
        "kicker": "DAVINCI RESOLVE   ·   FEDORA · UBUNTU · ARCH",
        "bad": "ERROR zlib",
        "good": "SOLUCIONADO",
        "sub": "sin terminal · una contraseña",
    },
}


def font(path: str, weight: str, size: int):
    return ImageFont.truetype(path.format(weight), size)


def fitted(path: str, weight: str, text: str, max_width: int, start: int):
    """Baja el cuerpo hasta que el texto quepa en `max_width`."""
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = start
    while size > 20:
        f = font(path, weight, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return font(path, weight, 20)


def background() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("L", (W // 3, H // 3), 0)
    ImageDraw.Draw(glow).ellipse([W // 6 - 130, -70, W // 6 + 190, 150], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(26)).resize((W, H), Image.LANCZOS)
    return Image.composite(Image.new("RGB", (W, H), (60, 44, 20)), img, glow)


def app_panel() -> Image.Image:
    """La aplicación trabajando, inclinada, como prueba de que esto existe.

    Se usa la pantalla de progreso y no la de inicio: los tics verdes y la
    barra ámbar se reconocen como «software haciendo algo» incluso cuando la
    miniatura mide dos centímetros, mientras que la pantalla de inicio se
    convierte en una mancha gris.
    """
    frames = sorted((ROOT / "assets" / LANG).glob("run_*.png"))
    source = frames[int(len(frames) * 0.62)] if frames else \
        ROOT / "assets" / LANG / "home.png"
    art = Image.open(source).convert("RGB")
    # Recorte a la tubería de pasos: menos elementos y más grandes.
    art = art.crop((10, 150, art.size[0] - 10, 700))
    target_h = 620
    scale = target_h / art.size[1]
    art = art.resize((int(art.size[0] * scale), target_h), Image.LANCZOS)

    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, art.size[0] - 1, art.size[1] - 1],
                                           14, fill=255)
    panel = Image.new("RGBA", art.size, (0, 0, 0, 0))
    panel.paste(art, (0, 0), mask)
    ImageDraw.Draw(panel).rounded_rectangle(
        [0, 0, art.size[0] - 1, art.size[1] - 1], 14, outline=(92, 100, 118, 255), width=3)
    return panel.rotate(-5, expand=True, resample=Image.BICUBIC)


def error_card() -> Image.Image:
    """Recorte del error real: la forma y el color rojo se reconocen al vuelo."""
    width, height = 620, 168
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], 12,
                           fill=(22, 17, 18, 255), outline=(92, 48, 48, 255), width=2)
    draw.text((28, 24), "Please install the following", font=font(MONO, "Regular", 23),
              fill=(150, 130, 130))
    draw.text((28, 56), "    zlib", font=font(MONO, "Bold", 27), fill=AMBER)
    draw.text((28, 104), "Installation cancelled.", font=font(MONO, "Bold", 32), fill=RED)
    return card.rotate(2.5, expand=True, resample=Image.BICUBIC)


def badge(diameter: int, colour, kind: str) -> Image.Image:
    img = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, diameter - 1, diameter - 1], fill=colour)
    c, u = diameter / 2, diameter / 100
    pen = dict(fill=(14, 16, 20, 255), width=int(9 * u))
    if kind == "x":
        draw.line([c - 22 * u, c - 22 * u, c + 22 * u, c + 22 * u], **pen)
        draw.line([c + 22 * u, c - 22 * u, c - 22 * u, c + 22 * u], **pen)
    else:
        draw.line([c - 24 * u, c + 1 * u, c - 7 * u, c + 19 * u], **pen)
        draw.line([c - 7 * u, c + 19 * u, c + 25 * u, c - 20 * u], **pen)
    return img


def main() -> int:
    text = TEXTS[LANG]
    img = background().convert("RGBA")

    # --- la ventana, sangrando por el borde derecho ------------------------
    panel = app_panel()
    shadow = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 170), (0, 0), panel.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    img.alpha_composite(shadow, (W - 512, 54))
    img.alpha_composite(panel, (W - 528, 40))

    # Velo solo en la costura: a partir de ahí la ventana se ve limpia, para
    # que se lea como "aquí está la aplicación" y no como ruido de fondo.
    veil = Image.new("L", (W, 1))
    for x in range(W):
        veil.putpixel((x, 0), max(0, min(255, int(255 - (x - 630) * 1.30))))
    shade = Image.new("RGBA", (W, H), BG + (255,))
    shade.putalpha(veil.resize((W, H)))
    img.alpha_composite(shade)

    draw = ImageDraw.Draw(img)
    left, right_edge = 60, 790

    # --- antetítulo --------------------------------------------------------
    draw.text((left, 46), text["kicker"], font=font(INTER, "Bold", 29), fill=MUTED)

    # --- el error, tachado -------------------------------------------------
    bad_font = fitted(DISPLAY, "Black", text["bad"], right_edge - left - 130, 118)
    bad_y = 108
    draw.text((left, bad_y), text["bad"], font=bad_font, fill=RED)
    box = draw.textbbox((left, bad_y), text["bad"], font=bad_font)
    middle = (box[1] + box[3]) / 2 + 4
    draw.line([box[0] - 12, middle, box[2] + 12, middle], fill=RED, width=13)

    stamp = badge(116, RED + (255,), "x")
    img.alpha_composite(stamp, (box[2] + 38, int(bad_y) + 8))

    # --- la palabra que la gente busca -------------------------------------
    good_font = fitted(DISPLAY, "Black", text["good"], right_edge - left - 40, 152)
    good_y = 262
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((left, good_y), text["good"], font=good_font,
                              fill=GREEN + (120,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
    draw.text((left, good_y), text["good"], font=good_font, fill=GREEN)

    good_box = draw.textbbox((left, good_y), text["good"], font=good_font)
    img.alpha_composite(badge(104, GREEN + (255,), "check"),
                        (good_box[2] + 30, good_y + 26))

    # --- el error real, como prueba ---------------------------------------
    card = error_card()
    img.alpha_composite(card, (left - 6, 462))

    # --- pie ---------------------------------------------------------------
    draw.text((left, 658), text["sub"], font=font(INTER, "Bold", 31), fill=AMBER)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, quality=95)
    kb = OUT.stat().st_size // 1024
    print(f"  [{LANG}] {OUT.relative_to(ROOT)}  {W}x{H}  {kb} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
