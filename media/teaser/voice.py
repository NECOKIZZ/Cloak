"""Voice-over: synthesizes each VO line with Kokoro (local, no API) and caches it in build/vo/."""
import hashlib
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(HERE, "build", "models"))
CACHE = os.path.join(HERE, "build", "vo")
VOICE = dict(name="am_michael", speed=1.0, lang="en-us")

_kokoro = None


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    return _kokoro


def line(text):
    """Mono float32 at 48 kHz, leading/trailing silence trimmed."""
    key = hashlib.sha1(f"{VOICE}|{text}".encode()).hexdigest()[:12]
    path = os.path.join(CACHE, f"{key}.wav")
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        samples, sr = _engine().create(text, voice=VOICE["name"], speed=VOICE["speed"], lang=VOICE["lang"])
        audio = resample_poly(samples.astype(np.float64), SR, sr).astype(np.float32)
        loud = np.flatnonzero(np.abs(audio) > 0.01)
        audio = audio[max(loud[0] - 480, 0): loud[-1] + 2400]
        sf.write(path, audio, SR)
    audio, _ = sf.read(path, dtype="float32")
    return audio


if __name__ == "__main__":
    for text in sys.argv[1:]:
        print(f"{len(line(text)) / SR:.2f}s  {text}")
