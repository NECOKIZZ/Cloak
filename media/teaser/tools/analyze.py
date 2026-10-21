"""Look at audio without ears: spectrogram + loudness strip, tempo and beat grid.

  python3 tools/analyze.py out.png a.mp3 [b.mp3 ...]   → one strip per file, plus a text summary
"""
import subprocess
import sys

import cv2
import numpy as np

SR = 22050


def load(path, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def spec(x, n=2048, hop=512):
    w = np.hanning(n).astype(np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * w
    return np.abs(np.fft.rfft(frames, axis=1)).T, hop / SR  # (bins, frames), seconds per frame


def onset_env(S):
    logS = np.log1p(S * 10)
    flux = np.maximum(np.diff(logS, axis=1), 0).sum(0)
    return np.concatenate([[0], flux])


def tempo(onset, dt):
    o = onset - onset.mean()
    ac = np.correlate(o, o, "full")[len(o) - 1:]
    lags = np.arange(len(ac)) * dt
    ok = (lags > 60 / 180) & (lags < 60 / 70)
    lag = lags[ok][np.argmax(ac[ok])]
    return 60 / lag


def strip(x, name, width=1600, height=220):
    S, dt = spec(x)
    freqs = np.fft.rfftfreq(2048, 1 / SR)
    bands = np.geomspace(30, 10000, 96)
    idx = np.clip(np.searchsorted(freqs, bands), 0, len(freqs) - 1)
    img = np.log1p(S[idx] * 5)
    img = (img / (np.percentile(img, 99.5) + 1e-6)).clip(0, 1)[::-1]
    img = cv2.resize(img.astype(np.float32), (width, height))
    rgb = cv2.applyColorMap((img * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(SR // 10) / (SR // 10), "same"))[:: SR // 20]
    db = 20 * np.log10(rms + 1e-5)
    ys = np.interp(db, [-50, 0], [height - 1, 0])
    xs = np.linspace(0, width - 1, len(ys))
    cv2.polylines(rgb, [np.stack([xs, ys], 1).astype(np.int32)], False, (255, 255, 255), 1)
    dur = len(x) / SR
    for s in range(0, int(dur), 5):
        X = int(s / dur * width)
        cv2.line(rgb, (X, height - 12 if s % 10 else height - 24), (X, height), (0, 255, 0), 1)
        if s % 30 == 0:
            cv2.putText(rgb, f"{s}s", (X + 2, height - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    bpm = tempo(onset_env(S), dt)
    cv2.putText(rgb, f"{name}  {dur:.0f}s  ~{bpm:.0f} BPM", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return rgb, dur, bpm, db


if __name__ == "__main__":
    out, files = sys.argv[1], sys.argv[2:]
    rows = []
    for f in files:
        x = load(f)
        rgb, dur, bpm, db = strip(x, f.split("/")[-1])
        rows.append(rgb)
        sec = db[::20][: int(dur)]
        print(f"{f.split('/')[-1]:<28} {dur:5.0f}s ~{bpm:4.0f}BPM  loudness/2s: " +
              " ".join(f"{v:.0f}" for v in sec[::2]))
    cv2.imwrite(out, np.vstack(rows))
