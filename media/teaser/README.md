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

All audio comes from [Openverse](https://openverse.org), limited to CC0 and CC BY licenses. Openverse's Freesound files are not reachable from the build environment. Wikimedia files rate-limit shared IPs, so any effect that hasn't downloaded yet plays a synthesized stand-in. The build prints which effects are real. Run `tools/fetch_sfx.sh`, then `build.py --audio-only`, to swap the real recordings in.

## Credits (required: CC BY)

- Music: "The mind trap - Part 1" by zero-project, [Jamendo](https://www.jamendo.com/track/1710142), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Edited: re-cut, filtered and looped.
- "Thunder" by Bidgee, [Wikimedia Commons](https://commons.wikimedia.org/w/index.php?curid=3770387), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Edited: low-passed and used as an impact.

Every other downloaded effect's credit is in `sfx/credits.json`. Add those to this list when they're in the mix.
