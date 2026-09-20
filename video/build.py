"""Compone el vídeo: fotogramas en Python, codificación con ffmpeg.

Cada escena es una función pura de (escena, t) -> imagen, de modo que las
transiciones entre escenas se calculan mezclando las dos funciones.
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from script import REPO, SCENES

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
AUDIO = ROOT / "audio"
OUT = ROOT / "DaVinci-Resolve-Manager-tutorial.mp4"

W, H, FPS = 1920, 1080, 30
LEAD, TAIL = 0.30, 0.60      # silencio antes y después de cada locución
FADE = 0.45                  # duración del encadenado entre escenas
RATE = 48000

INTER = "/usr/share/fonts/rsms-inter-fonts/Inter-{}.ttf"
DISPLAY = "/usr/share/fonts/rsms-inter-fonts/InterDisplay-{}.ttf"
MONO = "/usr/share/fonts/google-noto/NotoSansMono-{}.ttf"

BG = (14, 16, 20)
TEXT = (233, 235, 239)
MUTED = (154, 162, 177)
ACCENT = (255, 181, 63)

STAGE_TOP_TITLED = (110, 168, 1810, 1016)     # x0, y0, x1, y1
STAGE_TOP_PLAIN = (140, 96, 1780, 984)


def font(path: str, weight: str, size: int):
    return ImageFont.truetype(path.format(weight), size)


def ease(t: float) -> float:
    """Suavizado clásico: arranca y frena despacio."""
    return t * t * (3 - 2 * t)


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


# --------------------------------------------------------------------------
# Fondo
# --------------------------------------------------------------------------

def make_background() -> Image.Image:
    """Fondo oscuro con un halo cálido arriba, para que no sea un plano gris."""
    bg = Image.new("RGB", (W, H), BG)
    glow = Image.new("L", (W // 4, H // 4), 0)
    draw = ImageDraw.Draw(glow)
    draw.ellipse([W // 8 - 260, -170, W // 8 + 260, 190], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(60)).resize((W, H), Image.LANCZOS)
    warm = Image.new("RGB", (W, H), (58, 44, 22))
    return Image.composite(warm, bg, glow)


BACKGROUND = make_background()


# --------------------------------------------------------------------------
# Marco de la "pantalla"
# --------------------------------------------------------------------------

def framed(image: Image.Image, radius: int = 14) -> Image.Image:
    """Esquinas redondeadas y borde fino, como una ventana recortada."""
    image = image.convert("RGB")
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, image.size[0] - 1, image.size[1] - 1], radius, fill=255)
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    ImageDraw.Draw(out).rounded_rectangle(
        [0, 0, image.size[0] - 1, image.size[1] - 1], radius,
        outline=(58, 64, 78, 255), width=1)
    return out


def shadow_for(size, radius: int = 14) -> Image.Image:
    spread = 48
    layer = Image.new("RGBA", (size[0] + spread * 2, size[1] + spread * 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [spread, spread + 10, spread + size[0], spread + size[1] + 10],
        radius, fill=(0, 0, 0, 165))
    return layer.filter(ImageFilter.GaussianBlur(26))


def fit_box(size, box) -> tuple[int, int]:
    x0, y0, x1, y1 = box
    scale = min((x1 - x0) / size[0], (y1 - y0) / size[1])
    return max(1, int(size[0] * scale)), max(1, int(size[1] * scale))


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------

def headline_layer(text: str) -> Image.Image | None:
    if not text:
        return None
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    size = 46 if len(text) < 46 else 40
    draw.text((W // 2, 74), text, font=font(DISPLAY, "SemiBold", size),
              fill=TEXT, anchor="ma")
    return layer


# --------------------------------------------------------------------------
# Escenas
# --------------------------------------------------------------------------

class Stage:
    """Cachea todo lo caro de una escena: escalados, sombras y textos."""

    def __init__(self, scene: dict):
        self.scene = scene
        self.visual = scene["visual"]
        self.head = headline_layer(scene.get("headline", ""))
        self.box = STAGE_TOP_TITLED if self.head else STAGE_TOP_PLAIN
        self._cache: dict = {}

    # -- utilidades -----------------------------------------------------

    def _asset(self, name: str) -> Image.Image:
        if name not in self._cache:
            self._cache[name] = Image.open(ASSETS / name).convert("RGB")
        return self._cache[name]

    def _place(self, canvas: Image.Image, art: Image.Image, zoom: float = 1.0,
               dy: int = 0) -> None:
        target = fit_box(art.size, self.box)
        target = (max(1, int(target[0] * zoom)), max(1, int(target[1] * zoom)))
        key = ("shadow", target)
        if key not in self._cache:
            self._cache[key] = shadow_for(target)
        scaled = framed(art.resize(target, Image.LANCZOS))

        x0, y0, x1, y1 = self.box
        x = x0 + ((x1 - x0) - target[0]) // 2
        y = y0 + ((y1 - y0) - target[1]) // 2 + dy
        shadow = self._cache[key]
        canvas.paste(shadow, (x - 48, y - 48), shadow)
        canvas.paste(scaled, (x, y), scaled)

    def _focus_crop(self, image: Image.Image, region, amount: float) -> Image.Image:
        """Interpola entre la ventana entera y un recorte sobre `region`."""
        rx, ry, rw, rh = region
        aspect = (self.box[2] - self.box[0]) / (self.box[3] - self.box[1])
        cx, cy = rx + rw / 2, ry + rh / 2
        th = max(rh, rw / aspect)
        tw = th * aspect
        full_w, full_h = image.size
        fh = max(full_h, full_w / aspect)
        fw = fh * aspect

        w = fw + (tw - fw) * amount
        h = fh + (th - fh) * amount
        ccx = full_w / 2 + (cx - full_w / 2) * amount
        ccy = full_h / 2 + (cy - full_h / 2) * amount
        left = max(0, min(full_w - 1, ccx - w / 2))
        top = max(0, min(full_h - 1, ccy - h / 2))
        right = min(full_w, left + w)
        bottom = min(full_h, top + h)
        return image.crop((int(left), int(top), int(right), int(bottom)))

    def _dim_outside(self, image: Image.Image, region, alpha: float) -> Image.Image:
        if alpha <= 0.01:
            return image
        rx, ry, rw, rh = region
        out = image.convert("RGB").copy()
        veil = Image.new("RGBA", out.size, (10, 11, 14, int(180 * alpha)))
        hole = Image.new("L", out.size, 255)
        ImageDraw.Draw(hole).rounded_rectangle([rx, ry, rx + rw, ry + rh], 12, fill=0)
        veil.putalpha(Image.eval(hole, lambda v: int(v * alpha * 0.72)))
        out.paste(veil, (0, 0), veil)
        ImageDraw.Draw(out).rounded_rectangle(
            [rx, ry, rx + rw, ry + rh], 12,
            outline=(255, 181, 63, int(255 * alpha)), width=3)
        return out

    # -- render ---------------------------------------------------------

    def frame(self, t: float) -> Image.Image:
        canvas = BACKGROUND.copy()
        handler = getattr(self, f"_v_{self.visual}", None)
        if handler is None:
            handler = self._v_still
        handler(canvas, t)
        if self.head is not None:
            canvas.paste(self.head, (0, 0), self.head)
        return canvas

    # cada _v_* dibuja sobre el lienzo -----------------------------------

    def _v_still(self, canvas, t, name=None):
        art = self._asset(name or self._still_name())
        self._place(canvas, art, 1.0 + 0.028 * ease(clamp01(t)))

    def _still_name(self) -> str:
        return {
            "terminal_error": "term_error.png",
            "terminal_install": "term_install.png",
            "three_problems": "three_problems.png",
            "app_home": "home.png",
            "app_plan": "plan.png",
            "app_done": "done.png",
            "app_repair": "repair.png",
            "outro": "outro.png",
        }[self.visual]

    def _v_terminal_error_annotated(self, canvas, t):
        art = self._asset("term_error.png").copy()
        appear = clamp01((t - 0.18) / 0.25)
        if appear > 0:
            draw = ImageDraw.Draw(art, "RGBA")
            # Recuadro sobre la línea de "zlib".
            draw.rounded_rectangle([64, 250, 140, 284], 6,
                                   outline=(255, 181, 63, int(255 * appear)), width=3)
            label = "Fedora ships this as  zlib-ng-compat"
            small = font(INTER, "SemiBold", 21)
            width = int(draw.textlength(label, font=small)) + 40
            x, y = 190, 248
            draw.rounded_rectangle([x, y, x + width, y + 40], 8,
                                   fill=(42, 35, 24, int(240 * appear)),
                                   outline=(255, 181, 63, int(255 * appear)), width=2)
            draw.line([146, 267, x - 6, 267], fill=(255, 181, 63, int(255 * appear)), width=3)
            draw.text((x + width // 2, y + 20), label, font=small,
                      fill=(255, 181, 63, int(255 * appear)), anchor="mm")
        self._place(canvas, art, 1.0 + 0.02 * ease(clamp01(t)))

    def _v_three_problems(self, canvas, t):
        art = self._asset("three_problems.png").copy()
        # Las tres tarjetas entran una a una.
        card_h = art.size[1] // 3
        veil = Image.new("RGBA", art.size, (0, 0, 0, 0))
        for i in range(3):
            visible = clamp01((t - 0.06 - i * 0.17) / 0.18)
            if visible < 1:
                alpha = int(255 * (1 - visible))
                ImageDraw.Draw(veil).rectangle(
                    [0, i * card_h, art.size[0], (i + 1) * card_h],
                    fill=(14, 16, 20, alpha))
        art = art.convert("RGBA")
        art.alpha_composite(veil)
        self._place(canvas, art.convert("RGB"), 1.0 + 0.015 * ease(clamp01(t)))

    def _focus_scene(self, canvas, t, region_key, base="home.png", hold=0.34):
        region = REGIONS[region_key]
        amount = ease(clamp01(t / hold))
        image = self._dim_outside(self._asset(base), region, amount)
        self._place(canvas, self._focus_crop(image, region, amount),
                    1.0 + 0.02 * ease(clamp01(t)))

    def _v_zoom_cards(self, canvas, t):
        self._focus_scene(canvas, t, "cards")

    def _v_zoom_edition(self, canvas, t):
        self._focus_scene(canvas, t, "edition")

    def _v_drop_animation(self, canvas, t):
        region = REGIONS["drop"]
        amount = ease(clamp01(t / 0.28))
        arrive = clamp01((t - 0.22) / 0.46)
        base = "home_drag.png" if arrive > 0.80 else "home.png"
        image = self._dim_outside(self._asset(base), region, amount)

        if arrive > 0:              # el archivo entrando en la zona
            chip = self._chip()
            rx, ry, rw, rh = region
            # El punto de partida va dentro del recorte visible, si no el
            # archivo aparece cortado por el borde del encuadre.
            start = (rx + rw - 520, ry - 120)
            end = (rx + rw // 2 - chip.size[0] // 2, ry + rh // 2 - chip.size[1] // 2)
            e = ease(arrive)
            pos = (int(start[0] + (end[0] - start[0]) * e),
                   int(start[1] + (end[1] - start[1]) * e))
            # Se desvanece justo al soltarlo, cuando la zona ya se ilumina.
            fade = 1.0 - clamp01((t - 0.80) / 0.14)
            if fade < 1:
                chip = chip.copy()
                chip.putalpha(chip.getchannel("A").point(lambda v: int(v * fade)))
            image = image.convert("RGBA")
            image.alpha_composite(chip, pos)
            image = image.convert("RGB")

        self._place(canvas, self._focus_crop(image, region, amount))

    def _chip(self) -> Image.Image:
        if "chip" in self._cache:
            return self._cache["chip"]
        label = "DaVinci_Resolve_Studio_21.1_Linux.zip"
        small = font(MONO, "Regular", 19)
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        width = int(dummy.textlength(label, font=small)) + 76
        chip = Image.new("RGBA", (width, 62), (0, 0, 0, 0))
        draw = ImageDraw.Draw(chip)
        draw.rounded_rectangle([0, 0, width - 1, 61], 10, fill=(37, 41, 50, 246),
                               outline=(255, 181, 63, 255), width=2)
        draw.rounded_rectangle([18, 17, 40, 45], 4, fill=(255, 181, 63, 255))
        draw.text((54, 31), label, font=small, fill=TEXT, anchor="lm")
        self._cache["chip"] = chip
        return chip

    def _push_in(self, canvas, t, region_key, asset, reach=0.82):
        """Acercamiento lento hacia lo importante, sin perder el contexto."""
        amount = ease(clamp01(t)) * reach
        art = self._focus_crop(self._asset(asset), REGIONS[region_key], amount)
        self._place(canvas, art)

    def _v_app_plan(self, canvas, t):
        self._push_in(canvas, t, "plan_steps", "plan.png", reach=0.78)

    def _v_app_repair(self, canvas, t):
        self._push_in(canvas, t, "repair_fixes", "repair.png", reach=0.80)

    def _v_app_done(self, canvas, t):
        self._push_in(canvas, t, "done_block", "done.png", reach=0.30)

    def _v_app_home(self, canvas, t):
        # Plano de situación: la ventana entera, con un empuje muy leve.
        self._place(canvas, self._asset("home.png"), 1.0 + 0.03 * ease(clamp01(t)))

    def _v_app_run(self, canvas, t):
        index = min(RUN_COUNT - 1, max(0, int(t * RUN_COUNT)))
        art = self._asset(f"run_{index:04d}.png")
        self._place(canvas, art)

    def _v_outro(self, canvas, t):
        art = self._asset("outro.png")
        target = fit_box(art.size, (360, 300, 1560, 820))
        scaled = art.resize(target, Image.LANCZOS).convert("RGBA")
        appear = ease(clamp01(t / 0.5))
        if appear < 1:
            scaled.putalpha(Image.eval(scaled.getchannel("A"),
                                       lambda v: int(v * appear)))
        x = (W - target[0]) // 2
        y = (H - target[1]) // 2 - int(28 * (1 - appear))
        canvas.paste(scaled, (x, y), scaled)


REGIONS = json.loads((ASSETS / "regions.json").read_text())
RUN_COUNT = len(list(ASSETS.glob("run_*.png")))


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------

def decode(path: Path) -> bytes:
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le",
         "-ar", str(RATE), "-ac", "2", "-"],
        capture_output=True, check=True)
    return out.stdout


def build_audio(durations: dict) -> Path:
    silence = lambda seconds: b"\x00" * (int(RATE * seconds) * 4)
    chunks = []
    for scene in SCENES:
        chunks.append(silence(LEAD))
        chunks.append(decode(AUDIO / f"{scene['id']}.mp3"))
        chunks.append(silence(TAIL))
    target = AUDIO / "narration.wav"
    with wave.open(str(target), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(chunks))
    return target


# --------------------------------------------------------------------------
# Montaje
# --------------------------------------------------------------------------

def main() -> int:
    timings = json.loads((AUDIO / "timings.json").read_text())
    durations = [timings[s["id"]] + LEAD + TAIL for s in SCENES]
    total = sum(durations)
    frames_total = int(total * FPS)

    print(f"  {len(SCENES)} escenas · {total:.1f}s · {frames_total} fotogramas")
    wav = build_audio(timings)
    print(f"  audio montado: {wav.name}")

    stages = [Stage(scene) for scene in SCENES]
    starts, acc = [], 0.0
    for d in durations:
        starts.append(acc)
        acc += d

    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest", str(OUT),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)

    scene_index = 0
    for number in range(frames_total):
        now = number / FPS
        while scene_index + 1 < len(SCENES) and now >= starts[scene_index + 1]:
            scene_index += 1

        local = (now - starts[scene_index]) / durations[scene_index]
        frame = stages[scene_index].frame(clamp01(local))

        # Encadenado con la escena anterior durante los primeros FADE segundos.
        elapsed = now - starts[scene_index]
        if scene_index > 0 and elapsed < FADE:
            previous = stages[scene_index - 1].frame(1.0)
            frame = Image.blend(previous, frame, ease(elapsed / FADE))

        encoder.stdin.write(frame.tobytes())
        if number % 300 == 0:
            print(f"    {number:5d}/{frames_total}  ({number / frames_total * 100:4.1f}%)",
                  flush=True)

    encoder.stdin.close()
    if encoder.wait() != 0:
        print("ffmpeg falló", file=sys.stderr)
        return 1
    print(f"\n  listo: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
