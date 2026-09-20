# Tutorial video pipeline

The tutorial videos are built from scratch by these scripts: the app
screenshots are rendered from the real application (never mocked up), the
narration is synthesised with ElevenLabs, and the frames are composed in Python
and encoded with ffmpeg.

| | Language | Length | Voice |
|---|---|---|---|
| **[▶ Watch](https://github.com/Stevenkingx/DavinciResolve-Installer/releases/download/v1.0.0/DaVinci-Resolve-Manager-tutorial-en.mp4)** | English | 3:15 | Alice — Clear, Engaging Educator |
| **[▶ Ver](https://github.com/Stevenkingx/DavinciResolve-Installer/releases/download/v1.0.0/DaVinci-Resolve-Manager-tutorial-es.mp4)** | Español | 3:44 | Gabriela — Spanish from Mexico, Professional |

## Building a video

Every script takes the language as its first argument (`en` or `es`, default
`en`), so the two versions never collide: audio, assets and output file all live
under their own language.

```bash
export ELEVENLABS_API_KEY=...       # or put it in a .env one level up
cd video
python3 narrate.py     es           # 1. voiceover, one mp3 per scene
python3 render_app.py  es           # 2. app screenshots + animated run sequence
python3 make_assets.py es           # 3. terminal windows and explainer cards
python3 build.py       es           # 4. compose frames, encode with ffmpeg
python3 make_poster.py es           # 5. README thumbnail
```

Output: `DaVinci-Resolve-Manager-tutorial-es.mp4` (1920×1080, 30 fps, AAC
normalised to −16 LUFS).

Requires `ffmpeg`, `Pillow`, PyQt6, and the Inter and Noto Sans Mono fonts.

## Files

| File | What it does |
|---|---|
| `script.py` | Narration and visual plan for both languages, one entry per scene. Scene ids and visuals are identical across languages; only the text changes |
| `narrate.py` | Text to speech via ElevenLabs. Raw audio is cached under `audio/<lang>/raw/`, so changing the pacing costs no extra API calls |
| `render_app.py` | Drives the real app offscreen: screenshots, the animated progress sequence, and the widget geometry used to frame the close-up shots |
| `make_assets.py` | Terminal windows and explainer cards, drawn with Pillow |
| `build.py` | Frame compositor and encoder |
| `make_poster.py` | Thumbnail with a play button, for the README |

## Notes worth keeping

- **Nothing is mocked up.** The screenshots come from driving the real
  application, and the terminal output on screen is captured, not typed out:
  both the official installer's error and `install.sh`'s output are real.
- **The close-ups never drift.** `render_app.py` asks the app where each widget
  actually is and writes it to `regions.json`; the zoom shots crop from those
  coordinates, so a layout change does not require re-framing anything by hand.
- **Each scene is a pure function of (scene, t).** That is what makes the
  cross-fades possible: a transition is just both scenes evaluated at the right
  moment and blended, with no intermediate footage.
- **Pacing is normalised per language.** The Spanish voice narrates at about
  115 words per minute against the English voice's 160, so `narrate.py` applies
  a 10% `atempo` to the Spanish audio. It does not shift the pitch.
- **Screenshots carry no personal data**: the user name and the working folder
  are replaced with generic values before rendering.

## Adding another language

1. Add a `SCENES_<LANG>` list to `script.py` and register it in `ALL`, keeping
   the same scene ids and `visual` values.
2. Add the language's strings to `LABELS` in `script.py`, to `INSTALL_OUTPUT`
   and the card texts in `make_assets.py`, and to `TEXTS` in `make_poster.py`.
3. Pick a voice in `narrate.py` (`VOICES`) and set its `SPEED` if it narrates
   noticeably faster or slower than the others.
4. If the app itself supports the language, that is all: `render_app.py` takes
   its screenshots through the app's own translation layer.
