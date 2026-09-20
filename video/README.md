# Tutorial video pipeline

The tutorial video is built from scratch by these scripts: the app screenshots
are rendered from the real application (never mocked up), the narration is
synthesised with ElevenLabs, and the frames are composed in Python and encoded
with ffmpeg.

Watch the result: **[download the video](https://github.com/Stevenkingx/DavinciResolve-Installer/releases/download/v1.0.0/DaVinci-Resolve-Manager-tutorial.mp4)** (1080p, 3:15, English).

## Regenerating it

```bash
export ELEVENLABS_API_KEY=...       # or put it in a .env one level up
cd video
python3 narrate.py                  # 1. voiceover, one mp3 per scene
python3 render_app.py               # 2. app screenshots + the animated run sequence
python3 make_assets.py              # 3. terminal windows and explainer cards
python3 build.py                    # 4. compose frames, encode with ffmpeg
```

Output: `DaVinci-Resolve-Manager-tutorial.mp4` (1920×1080, 30 fps, AAC at −16 LUFS).

Requires `ffmpeg`, `Pillow`, PyQt6 and the Inter and Noto Sans Mono fonts.

## Files

| File | What it does |
|---|---|
| `script.py` | The narration script and the visual plan, one entry per scene |
| `narrate.py` | Text to speech via ElevenLabs; writes `audio/*.mp3` and their durations |
| `render_app.py` | Drives the real app offscreen: screenshots, the animated progress sequence, and the on-screen geometry used for the close-up shots |
| `make_assets.py` | Terminal windows and explainer cards, drawn with Pillow |
| `build.py` | Frame compositor and encoder. Each scene is a pure function of (scene, t), which is what makes the cross-fades possible |

## Making a Spanish version

The app is already bilingual, so most of the work is the script:

1. Translate the `text` and `headline` fields in `script.py`.
2. Pick a Spanish voice in `narrate.py` (`VOICE_ID`) — the model used,
   `eleven_multilingual_v2`, handles Spanish well.
3. In `render_app.py`, change `i18n.set_language("en")` to `"es"`.
4. Re-run the four steps above.
