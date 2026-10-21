"""Voice-over: synthesizes each VO line with Kokoro (local, no API) and caches it in build/vo/."""
import hashlib
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(HERE, "build", "models"))
CACHE = os.path.join(HERE, "build", "vo")
# am_onyx is Kokoro's deepest voice (~89 Hz); PITCH lowers it a further ~2.4 semitones (formants kept, so it stays natural)
VOICE = dict(name="am_onyx", speed=1.08, lang="en-us")
PITCH = 0.87

_kokoro = None


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    return _kokoro


def line(text):
    """Mono float32 at 48 kHz, leading/trailing silence trimmed."""
    key = hashlib.sha1(f"{VOICE}|{PITCH}|{text}".encode()).hexdigest()[:12]
    path = os.path.join(CACHE, f"{key}.wav")
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        samples, sr = _engine().create(text, voice=VOICE["name"], speed=VOICE["speed"], lang=VOICE["lang"])
        audio = resample_poly(samples.astype(np.float64), SR, sr).astype(np.float32)
        audio = deepen(audio)
        loud = np.flatnonzero(np.abs(audio) > 0.01)
        audio = audio[max(loud[0] - 480, 0): loud[-1] + 2400]
        sf.write(path, audio, SR)
    audio, _ = sf.read(path, dtype="float32")
    return audio


def deepen(audio):
    """Pitch down with rubberband (ffmpeg), keeping formants and duration."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                          "-af", f"rubberband=pitch={PITCH}:formant=preserved:pitchq=quality",
                          "-f", "f32le", "-"], input=audio.tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


if __name__ == "__main__":
    for text in sys.argv[1:]:
        print(f"{len(line(text)) / SR:.2f}s  {text}")
