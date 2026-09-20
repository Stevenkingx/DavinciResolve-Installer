"""Genera la locución de cada escena con ElevenLabs."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from script import SCENES

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / "audio"
VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"      # Alice — Clear, Engaging Educator
MODEL = "eleven_multilingual_v2"


def api_key() -> str:
    for candidate in (ROOT.parent / ".env", ROOT / ".env"):
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                if line.strip().startswith("ELEVENLABS_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No encuentro ELEVENLABS_API_KEY en .env")


def synthesize(text: str, target: Path, key: str) -> None:
    body = json.dumps({
        "text": text,
        "model_id": MODEL,
        # Estable y sin dramatismo: es una voz que explica, no que actúa.
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }).encode()
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        data=body,
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                target.write_bytes(response.read())
            return
        except urllib.error.HTTPError as exc:
            if attempt == 2:
                raise SystemExit(f"TTS falló: {exc.code} {exc.read()[:200]!r}")
            time.sleep(3 * (attempt + 1))


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> int:
    key = api_key()
    AUDIO.mkdir(parents=True, exist_ok=True)
    timings = {}
    total = 0.0

    for scene in SCENES:
        target = AUDIO / f"{scene['id']}.mp3"
        if not target.exists() or "--force" in sys.argv:
            synthesize(scene["text"], target, key)
        seconds = duration(target)
        timings[scene["id"]] = seconds
        total += seconds
        words = len(scene["text"].split())
        print(f"  {scene['id']:<12} {seconds:6.2f}s  ({words:3d} palabras, "
              f"{words / seconds * 60:5.1f} ppm)")

    (AUDIO / "timings.json").write_text(json.dumps(timings, indent=2))
    print(f"\nlocución total: {total:.1f}s ({total / 60:.2f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
