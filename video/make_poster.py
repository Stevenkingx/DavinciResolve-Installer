"""Miniatura del vídeo para el README: un fotograma con botón de reproducción."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from script import language

ROOT = Path(__file__).resolve().parent
LANG = language()
VIDEO = ROOT / f"DaVinci-Resolve-Manager-tutorial-{LANG}.mp4"
OUT = ROOT / "assets" / LANG / "video-poster.png"

INTER = "/usr/share/fonts/rsms-inter-fonts/Inter-{}.ttf"
DISPLAY = "/usr/share/fonts/rsms-inter-fonts/InterDisplay-{}.ttf"

TEXTS = {
    "en": {
        "title": "How to install DaVinci Resolve on Linux",
        "sub": "…even when the official installer refuses",
        "chips": ["3 minutes", "English narration", "1080p"],
        "at": "58",
    },
    "es": {
        "title": "Cómo instalar DaVinci Resolve en Linux",
        "sub": "…aunque el instalador oficial se niegue",
        "chips": ["4 minutos", "Narración en español", "1080p"],
        "at": "62",
    },
}


def font(path: str, weight: str, size: int):
    return ImageFont.truetype(path.format(weight), size)


def main() -> int:
    text = TEXTS[LANG]
    frame = ROOT / "check" / f"poster_src_{LANG}.png"
    frame.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", text["at"],
                    "-i", str(VIDEO), "-frames:v", "1", str(frame)], check=True)

    base = Image.open(frame).convert("RGBA")
    W, H = base.size
    base.alpha_composite(Image.new("RGBA", (W, H), (8, 9, 12, 120)))

    # Degradado inferior: deja el texto limpio sin apagar toda la imagen.
    grad = Image.new("L", (1, H))
    for y in range(H):
        value = 0 if y < H * 0.52 else int(235 * ((y - H * 0.52) / (H * 0.48)) ** 1.35)
        grad.putpixel((0, y), value)
    shade = Image.new("RGBA", (W, H), (8, 9, 12, 255))
    shade.putalpha(grad.resize((W, H)))
    base.alpha_composite(shade)

    draw = ImageDraw.Draw(base)
    cx, cy, r = W // 2, int(H * 0.40), 84
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - r - 16, cy - r - 16, cx + r + 16, cy + r + 16],
                                 fill=(255, 181, 63, 80))
    base.alpha_composite(halo.filter(ImageFilter.GaussianBlur(24)))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 181, 63, 255))
    draw.polygon([(cx - 25, cy - 39), (cx - 25, cy + 39), (cx + 39, cy)],
                 fill=(26, 20, 5, 255))

    draw.text((cx, H - 300), text["title"], font=font(DISPLAY, "Bold", 62),
              fill=(240, 242, 246), anchor="ma")
    draw.text((cx, H - 212), text["sub"], font=font(INTER, "Regular", 34),
              fill=(190, 196, 208), anchor="ma")

    chip_f = font(INTER, "Medium", 26)
    widths = [int(draw.textlength(c, font=chip_f)) + 52 for c in text["chips"]]
    x = (W - sum(widths) - 18 * (len(widths) - 1)) // 2
    for chip, width in zip(text["chips"], widths):
        pill = Image.new("RGBA", (width, 56), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([0, 0, width - 1, 55], 28, fill=(32, 36, 44, 235),
                             outline=(66, 72, 88, 255), width=1)
        pd.text((width // 2, 28), chip, font=chip_f, fill=(200, 206, 218), anchor="mm")
        base.alpha_composite(pill, (x, H - 140))
        x += width + 18

    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(OUT)
    print(f"  [{LANG}] {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
