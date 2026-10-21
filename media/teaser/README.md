# Cloak teaser

A 40 s teaser cut from the seven Veo shots in [NECOKIZZ/motion-design](https://github.com/NECOKIZZ/motion-design), with glitch work, a surveillance HUD, kinetic titles, an end-card flip sequence (Cloak → Elysium → Hyperliquid → Cloak), a voice-over and sound design. Everything is rendered from code, so any change is one command away.

```bash
pip install numpy scipy opencv-python-headless pillow soundfile pyloudnorm kokoro-onnx
# clips/1.mp4 … clips/7.mp4 = the seven Veo shots, in story order (see docs/TEASER.md)
python3 build.py              # → build/cloak-teaser.mp4 (master) and build/cloak-teaser-share.mp4
python3 build.py --audio-only # re-mix the sound under the last rendered picture
```

The voice is [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), run locally. Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `build/models/`.

| File | What it decides |
|---|---|
| `edit.py` | the cut (which clip, when, how fast), effects, titles, HUD, end card |
| `audio.py` | the score edit, every sound effect cue, voice-over lines, the mix |
| `voice.py` | voice-over synthesis and caching |
| `tools/openverse.py` | searches Openverse and downloads picks with their license info into `sfx/` |
| `tools/fetch_sfx.sh` | downloads the full sound-effect list |
| `tools/analyze.py` | spectrogram, loudness and tempo of any audio file (how the music was chosen and cut) |

## Timing

The music is 130 BPM, and its drop is pinned to the frame where the amber line snaps together (`DROP` in `edit.py`). Acts 1–3 cut on the beat grid (`beat(n)`). Acts 6–7 cut on the drop's detected kicks (`DROP_KICKS`). The final "Cloak" lock lands on the hardest kick.

## Sound

- **Music** is from [Openverse](https://openverse.org) (Jamendo), chosen with `tools/analyze.py`.
- **Sound effects** are mostly from [Mixkit](https://mixkit.co/free-sound-effects/), browsed and downloaded with `tools/mixkit.py`. A few come from Openverse (Wikimedia Commons). Freesound isn't reachable from the build environment.
- **Missing files:** if an effect isn't in `sfx/`, a synthesized stand-in plays, and the build prints which ones.
- **Voice** is Kokoro's deepest voice (`am_onyx`), pitched down about 2.4 semitones with rubberband (formants kept), with chest and presence EQ. Change `VOICE` / `PITCH` in `voice.py`.

## Credits

- Music: "The mind trap - Part 1" by zero-project, [Jamendo](https://www.jamendo.com/track/1710142), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Edited: re-cut, filtered and looped. **Credit required.**
- "Thunder" by Bidgee, [Wikimedia Commons](https://commons.wikimedia.org/w/index.php?curid=3770387), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Edited: low-passed. **Credit required.**
- "647712 unfa braam" by Unfa, [Wikimedia Commons](https://commons.wikimedia.org/w/index.php?curid=129960732), CC0.
- Other sound effects from [Mixkit](https://mixkit.co), under the [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) (no attribution required). Item IDs are in `sfx/credits.json`.

Suggested credit line for the video description:

> Music: "The mind trap - Part 1" by zero-project (CC BY 3.0). Sound: "Thunder" by Bidgee (CC BY 3.0), Unfa (CC0), Mixkit.
