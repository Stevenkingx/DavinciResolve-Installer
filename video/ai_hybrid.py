"""Miniatura híbrida: dirección de arte generada + captura real de la aplicación.

El modelo compone el fondo y la tipografía, y deja libre el tercio derecho.
Ahí se pega la ventana real de la aplicación, no una inventada: quien haga clic
verá exactamente eso al abrirla.
"""
from __future__ import annotations
import base64, json, sys, time, urllib.error, urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ai"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "1536x864"

TEXTS = {
    "en": ("DAVINCI RESOLVE · FEDORA · UBUNTU · ARCH", "zlib ERROR", "FIXED"),
    "es": ("DAVINCI RESOLVE · FEDORA · UBUNTU · ARCH", "ERROR zlib", "SOLUCIONADO"),
}


def api_key() -> str:
    for candidate in (ROOT.parent / ".env", ROOT / ".env"):
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                if line.strip().startswith("OPENAI_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No encuentro OPENAI_API_KEY")


def prompt_for(lang: str) -> str:
    kicker, bad, good = TEXTS[lang]
    return (
        "Professional YouTube thumbnail background, 16:9, extremely crisp, high "
        "contrast, readable as a small phone thumbnail. All text spelled exactly "
        "as written, with correct accents. No watermarks. "
        "LEFT HALF: dark cinematic tech design with bold heavy sans-serif "
        f"typography stacked vertically: a small light-grey uppercase line reading "
        f"exactly \"{kicker}\"; below it huge bright red uppercase text reading "
        f"exactly \"{bad}\" with a thick red strike-through line across it and a "
        f"solid red circular X badge to its right; below that enormous bright green "
        f"uppercase text reading exactly \"{good}\" with a solid green circular "
        "check-mark badge to its right; at the bottom left a small dark rounded "
        "terminal panel with monospace text, an amber line reading \"zlib\" and a "
        "red line reading exactly \"Installation cancelled.\". "
        "RIGHT HALF: completely empty negative space. No window, no screen, no "
        "interface, no text, no objects at all. Just deep black with a soft warm "
        "amber glow and gentle out-of-focus bokeh, so an interface can be placed "
        "there later."
    )


def generate(lang: str, key: str) -> Path:
    body = json.dumps({"model": MODEL, "prompt": prompt_for(lang),
                       "size": SIZE, "n": 1}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    start = time.time()
    with urllib.request.urlopen(request, timeout=300) as response:
        item = json.load(response)["data"][0]
    raw = (base64.b64decode(item["b64_json"]) if "b64_json" in item
           else urllib.request.urlopen(item["url"], timeout=120).read())
    target = OUT / f"{lang}_hybrid_bg.png"
    target.write_bytes(raw)
    print(f"  fondo {lang}: {len(raw)//1024} KB en {time.time() - start:.0f}s")
    return target


def real_panel(lang: str, width: int) -> Image.Image:
    """La pantalla de progreso real, recortada a la tubería de pasos.

    Se dimensiona por ANCHO: el recorte es muy apaisado y ajustarlo por alto
    lo desbordaba hasta tapar la tipografía.
    """
    frames = sorted((ROOT / "assets" / lang).glob("run_*.png"))
    art = Image.open(frames[int(len(frames) * 0.62)]).convert("RGB")
    art = art.crop((14, 148, 790, 700))          # dots, títulos y barra
    scale = width / art.size[0]
    art = art.resize((width, int(art.size[1] * scale)), Image.LANCZOS)

    from PIL import ImageDraw
    mask = Image.new("L", art.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, art.size[0] - 1, art.size[1] - 1],
                                           14, fill=255)
    panel = Image.new("RGBA", art.size, (0, 0, 0, 0))
    panel.paste(art, (0, 0), mask)
    ImageDraw.Draw(panel).rounded_rectangle(
        [0, 0, art.size[0] - 1, art.size[1] - 1], 14,
        outline=(120, 128, 148, 255), width=3)
    return panel.rotate(-5, expand=True, resample=Image.BICUBIC)


def compose(lang: str, background: Path) -> Path:
    canvas = Image.open(background).convert("RGBA")
    W, H = canvas.size
    panel = real_panel(lang, int(W * 0.40))

    shadow = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 190), (0, 0), panel.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))

    # Sangra un poco por el borde derecho y deja libre toda la mitad izquierda.
    x = W - panel.size[0] + int(panel.size[0] * 0.16)
    y = (H - panel.size[1]) // 2
    canvas.alpha_composite(shadow, (x + 14, y + 16))
    canvas.alpha_composite(panel, (x, y))

    target = OUT / f"{lang}_hybrid.png"
    canvas.convert("RGB").resize((1280, 720), Image.LANCZOS).save(target, quality=95)
    print(f"  {target.name}  {target.stat().st_size // 1024} KB")
    return target


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    key = api_key()
    for lang in ([a for a in sys.argv[1:] if a in TEXTS] or list(TEXTS)):
        compose(lang, generate(lang, key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
