"""Genera miniaturas con gpt-image-2.5. Texto incluido en la propia imagen."""
from __future__ import annotations
import base64, json, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ai"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "1536x864"          # 16:9 exacto: se escala a 1280x720 sin recortar


def api_key() -> str:
    for candidate in (ROOT.parent / ".env", ROOT / ".env"):
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                if line.strip().startswith("OPENAI_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No encuentro OPENAI_API_KEY")


COMMON = ("Professional YouTube thumbnail, 16:9, extremely crisp and high contrast, "
          "designed to be readable as a small phone-sized thumbnail. "
          "All text must be spelled exactly as written, with correct accents. "
          "No watermarks, no logos, no text other than what is listed.")

def graphic(kicker, bad, good, terminal_line):
    return (f"{COMMON} Dark cinematic tech graphic design. "
            f"LEFT TWO THIRDS, bold heavy sans-serif typography stacked vertically: "
            f"a small light-grey uppercase line at the top reading exactly "
            f"\"{kicker}\"; below it huge bright red uppercase text reading exactly "
            f"\"{bad}\" with a thick red horizontal strike-through line drawn across "
            f"it and a solid red circular X badge to its right; below that, enormous "
            f"bright green uppercase text reading exactly \"{good}\" with a solid "
            f"green circular check-mark badge to its right; at the bottom left a "
            f"small dark rounded terminal panel with monospace text, an amber line "
            f"reading \"zlib\" and a red line reading exactly \"{terminal_line}\". "
            f"RIGHT THIRD: a sleek dark application window tilted slightly, showing a "
            f"vertical checklist with glowing green check marks and a bright amber "
            f"progress bar. Background near-black with a warm amber glow behind the "
            f"title. Polished, modern, deep blacks.")

def photo(kicker, bad, good):
    return (f"{COMMON} Photographic and cinematic: a dark colour-grading suite at "
            f"night shot on 35mm, a large monitor on the right glowing with a red "
            f"terminal error, warm amber key light and cool teal rim light, "
            f"volumetric haze, shallow depth of field, rich film contrast. "
            f"Overlaid on the left third, huge bold uppercase graphic typography: a "
            f"small grey line reading exactly \"{kicker}\", below it bright red text "
            f"reading exactly \"{bad}\" with a thick red strike-through across it, "
            f"and under that enormous bright green text reading exactly \"{good}\". "
            f"The overlaid typography is razor sharp and perfectly legible.")


JOBS = {
    "en_graphic": graphic("DAVINCI RESOLVE · FEDORA · UBUNTU · ARCH",
                          "zlib ERROR", "FIXED", "Installation cancelled."),
    "en_photo":   photo("DAVINCI RESOLVE ON LINUX", "zlib ERROR", "FIXED"),
    "es_graphic": graphic("DAVINCI RESOLVE · FEDORA · UBUNTU · ARCH",
                          "ERROR zlib", "SOLUCIONADO", "Installation cancelled."),
    "es_photo":   photo("DAVINCI RESOLVE EN LINUX", "ERROR zlib", "SOLUCIONADO"),
}


def generate(name: str, prompt: str, key: str) -> None:
    body = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "n": 1}).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            item = json.load(response)["data"][0]
    except urllib.error.HTTPError as exc:
        print(f"  ERROR {name}: {exc.code} {exc.read()[:200]}")
        return
    raw = (base64.b64decode(item["b64_json"]) if "b64_json" in item
           else urllib.request.urlopen(item["url"], timeout=120).read())
    target = OUT / f"{name}.png"
    target.write_bytes(raw)
    print(f"  {name:12s} {len(raw)//1024:5d} KB  {time.time() - start:4.0f}s")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    key = api_key()
    wanted = [a for a in sys.argv[1:] if a in JOBS] or list(JOBS)
    for name in wanted:
        generate(name, JOBS[name], key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
