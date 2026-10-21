"""Sound: the score (one Jamendo track, re-edited to the picture), sound effects from Openverse, and the voice-over.

Each effect is a real recording from sfx/ (see sfx/credits.json). If a file hasn't been downloaded yet, a
synthesized stand-in plays instead, so the mix always builds; re-run once the downloads land.
"""
import os

import subprocess

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, sosfilt_zi

import voice
from edit import (BEAM_STRIKE, BEAT, CUT_TO_BLACK, DROP, DURATION, END_IN, FLIPS, GLASS_LANDS, MARK_IN, MUSIC_OUT,
                  beat)

SR = 48000
N = int(DURATION * SR)
HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(HERE, "sfx")
rng = np.random.default_rng(5)

MUSIC = "m_mind_trap"     # "The mind trap - Part 1", 130 BPM
MUSIC_DROP = 48.29        # where the drop's downbeat sits in the track
BEHIND_GLASS = 420.0      # low-pass while the world is behind the glass (Hz)
ORBS = [16.42, 17.75, 19.44]  # shot 4: each bid enters the monolith

VO = [
    (0.55, "Every launch is watched."),
    (5.60, "Every trade, traced."),
    (12.40, "Until now."),
    (15.95, "Bids go in sealed."),
    (17.70, "Not even the sequencer can see them."),
    (21.95, "Bidding closes."),
    (24.30, "Everyone pays one price."),
    (26.40, "Then trade from a private balance."),
    (28.75, "Your wallet never shows up."),
    (31.40, "Launch sealed."),
    (32.30, "Trade unseen."),
    (33.30, "Live on Elysium."),
    (34.40, "Built for Hyperliquid."),
    (35.95, "Cloak."),
]


# ─── helpers ────────────────────────────────────────────────────────────────
def sos(kind, hz, order=2):
    return butter(order, hz, kind, fs=SR, output="sos")


def filt(x, kind, hz, order=2):
    return sosfilt(sos(kind, hz, order), x, axis=0)


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def sfx(name):
    """A downloaded effect as stereo float32, or None if it isn't here yet."""
    for f in os.listdir(SFX):
        if os.path.splitext(f)[0] == name and os.path.getsize(os.path.join(SFX, f)) > 0:
            return decode(os.path.join(SFX, f))
    return None


def stereo(x):
    x = np.asarray(x, np.float32)
    return np.stack([x, x], 1) if x.ndim == 1 else x


def norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak


def first_hit(x, length, pre=0.005):
    """Cut a single event out of a recording: from just before its first transient, `length` seconds."""
    env = np.abs(x).max(1)
    i = int(np.argmax(env > env.max() * 0.3))
    a = max(0, i - int(pre * SR))
    out = x[a: a + int(length * SR)].copy()
    out[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))[:, None]
    return out


def repitch(x, semitones):
    """Pitch by resampling (changes length too, like a tape)."""
    ratio = 2 ** (semitones / 12)
    up, down = 1000, int(round(1000 * ratio))
    return resample_poly(x, up, down, axis=0).astype(np.float32)


def tail(x, seconds):
    n = int(seconds * SR)
    x = x[:n].copy()
    x[-min(len(x), int(0.3 * SR)):] *= np.linspace(1, 0, min(len(x), int(0.3 * SR)))[:, None] ** 2
    return x


class Bus:
    def __init__(self):
        self.buf = np.zeros((N, 2), np.float32)

    def add(self, t, x, gain=1.0, pan=0.0):
        x = stereo(x)
        if pan:
            x = x * np.array([min(1, 1 - pan), min(1, 1 + pan)], np.float32)
        i = int(round(t * SR))
        if i < 0:
            x, i = x[-i:], 0
        if i >= N:
            return
        x = x[: N - i]
        self.buf[i: i + len(x)] += x * gain


def reverb_ir(seconds=2.8, damp=6000):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t * 6.9 / seconds)[:, None]
    ir = filt(ir, "low", damp)
    ir[: int(0.015 * SR)] = 0
    return (ir / np.sqrt((ir ** 2).sum(0))).astype(np.float32)


# ─── synthesized stand-ins (only used while a recording is missing) ────────
def syn_noise_burst(length, lo=1500, hi=9000, decay=0.004):
    n = int(length * SR)
    return filt(rng.standard_normal(n), "band", [lo, hi]) * np.exp(-np.arange(n) / (decay * SR))


def syn_shutter():
    a = syn_noise_burst(0.02, 1500, 8000, 0.004)
    out = np.zeros(int(0.12 * SR))
    out[: len(a)] += a
    out[int(0.06 * SR): int(0.06 * SR) + len(a)] += a * 0.7
    return out


def syn_glitch(length=0.18):
    n = int(length * SR)
    x = np.sign(np.sin(2 * np.pi * rng.uniform(200, 1800) * np.arange(n) / SR)) * 0.5
    x += rng.standard_normal(n) * 0.5
    step = int(rng.integers(8, 40))
    x = np.repeat(x[::step], step)[:n]  # sample-and-hold crunch
    return x * (np.arange(n) < n * rng.uniform(0.4, 1.0))


def syn_boom(length=3.0, f0=70, f1=28):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    thump = filt(rng.standard_normal(n), "low", 200) * np.exp(-t * 14) * 0.6
    return body + thump


def syn_braam(length=3.5):
    n = int(length * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in (36.7, 55.0, 73.4, 110.0):
        for d in (-0.6, 0, 0.7):
            x += np.sign(np.sin(2 * np.pi * (f + d) * t)) / (1 + f / 60)
    x = filt(np.tanh(x * 0.8), "low", 900)
    return x * np.minimum(1, t / 0.05) * np.exp(-t * 0.9)


def syn_whoosh(length=0.7, f0=600, f1=6000, up=True):
    n = int(length * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blocks = 64
    edges = np.linspace(0, n, blocks + 1).astype(int)
    zi = None
    for b in range(blocks):
        u = b / blocks
        fc = f0 * (f1 / f0) ** (u if up else 1 - u)
        s = sos("band", [max(80, fc * 0.5), min(SR / 2.2, fc * 1.6)])
        if zi is None:
            zi = sosfilt_zi(s) * 0
        y, zi = sosfilt(s, x[edges[b]: edges[b + 1]], zi=zi)
        out[edges[b]: edges[b + 1]] = y
    env = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out * env


def syn_riser(length=2.3):
    return syn_whoosh(length, 300, 9000, True) * np.linspace(0.2, 1, int(length * SR)) ** 2


def syn_bell(f0=880, length=4.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * d)
            for r, a, d in [(1, 1, 1.2), (2.0, 0.5, 1.8), (2.76, 0.35, 2.4), (5.4, 0.2, 3.5)])
    return x * (1 - np.exp(-t * 900))


def syn_tap():
    x = syn_bell(2600, 0.6) * 0.5
    c = syn_noise_burst(0.02, 3000, 12000, 0.002)
    x[: len(c)] += c
    return x


def syn_flap():
    out = np.zeros(int(0.35 * SR))
    for k in range(5):
        c = syn_noise_burst(0.01, 1200, 6000, 0.0015)
        i = int(k * 0.045 * SR)
        out[i: i + len(c)] += c * (1 - k * 0.12)
    return out


def syn_buzz(length):
    n = int(length * SR)
    t = np.arange(n) / SR
    gate = (np.sin(2 * np.pi * 217 * t) > 0.6).astype(float)
    burst = (np.sin(2 * np.pi * 8 * t) > -0.2).astype(float)
    return filt(gate * burst, "band", [150, 4000]) * 0.6


def syn_data(length):
    n = int(length * SR)
    out = np.zeros(n)
    t = 0.0
    while t < length:
        c = syn_noise_burst(0.004, 3000, 10000, 0.001)
        i = int(t * SR)
        out[i: i + len(c)] += c[: n - i] * rng.uniform(0.3, 1)
        t += rng.exponential(1 / 22)
    return out


# ─── effects, real or stand-in ──────────────────────────────────────────────
def get(name, fallback):
    x = sfx(name)
    return (norm(x), True) if x is not None else (norm(stereo(fallback())), False)


def peak_time(x):
    env = uniform_filter1d(np.abs(x).max(1), int(0.02 * SR))
    return np.argmax(env) / SR


def build_effects():
    fx, wet = Bus(), Bus()
    used = {}

    def take(name, fallback, shape=None):
        x, real = get(name, fallback)
        used[name] = real
        return shape(x) if (real and shape) else x

    def hit(t, x, gain, pan=0.0, rev=0.0):
        """A one-shot whose transient lands on t."""
        fx.add(t, x, gain, pan)
        if rev:
            wet.add(t, x, gain * rev)

    def build(t, x, gain, rev=0.0, not_before=None, stop_at_peak=False):
        """A swell (riser, whoosh) whose loudest moment lands on t. Optionally starts no earlier than
        `not_before` (with a short fade in) and/or stops dead at its peak."""
        p = peak_time(x)
        start = t - p
        if stop_at_peak:
            x = x[: int(p * SR)].copy()
        if not_before is not None and start < not_before:
            x = x[int((not_before - start) * SR):].copy()
            k = min(len(x), int(0.08 * SR))
            x[:k] *= np.linspace(0, 1, k)[:, None]
            start = not_before
        fx.add(start, x, gain)
        if rev:
            wet.add(start, x, gain * rev)

    onset = lambda length: (lambda x: first_hit(x, length))
    shutter = take("shutter", syn_shutter, onset(0.3))
    glitches = [take(n, syn_glitch, onset(0.6)) for n in ("glitch_fail", "glitch_place", "glitch_collect")]
    glitch_logo = take("glitch_logo", lambda: syn_glitch(0.6), onset(2.5))
    static = take("static", lambda: rng.standard_normal(int(0.5 * SR)) * 0.5, lambda x: x[: int(1.2 * SR)])
    braam = take("braam", syn_braam, lambda x: tail(first_hit(x, 6.0), 6.0))
    horn = take("horn", syn_braam, onset(4.5))
    thunder = take("thunder", syn_boom, lambda x: filt(first_hit(x, 5.0), "low", 300))
    impact = take("impact_big", syn_boom)                       # has its own lead-in: placed by peak
    trailer_hit = take("trailer_hit", syn_boom, onset(4.0))
    tap = take("glass_tap", syn_tap, onset(0.5))
    glass_hit = take("glass_hit", syn_tap, onset(4.5))
    riser = take("riser", syn_riser)
    riser_long = take("riser_long", lambda: syn_riser(3.0), lambda x: x[int(22.5 * SR): int(26.3 * SR)])
    bell = take("gong", lambda: syn_bell(196, 6.0), onset(7.0))
    sparkle = take("tubebells", lambda: syn_bell(1318, 4.0), onset(4.5))
    slide = take("splitflap", syn_flap, onset(0.8))
    click = take("ui_click", syn_flap, onset(0.2))
    buzz = take("gsm_buzz", lambda: syn_buzz(4.0), lambda x: x[int(1 * SR): int(5 * SR)])
    data = take("teleprinter", lambda: syn_data(4.0), onset(3.3))
    whoosh = take("whoosh", lambda: syn_whoosh(1.0))
    whoosh_long = take("whoosh_long", lambda: syn_whoosh(2.0), onset(5.0))
    stutter = take("whoosh_stutter", lambda: syn_whoosh(2.0))
    slam = take("slam", lambda: syn_glitch(0.4), onset(1.3))
    sub = take("sub", lambda: syn_boom(1.2, 90, 40), onset(1.0))

    # 1 · WATCHED
    hit(0.0, static, 0.5)
    hit(0.0, glitches[0], 0.35)
    for t in (beat(3), beat(8), beat(9), beat(9.5)):
        hit(t, shutter, 0.7, pan=rng.uniform(-0.5, 0.5), rev=0.2)
    for i, t in enumerate((beat(5), beat(11.5))):
        hit(t, glitches[(i + 1) % 3], 0.5)
    for t in (beat(6), beat(13)):  # title slams
        hit(t, slam, 0.55)
        hit(t, sub, 0.7)
    # 2 · TRACED: the network listens, interference builds
    hit(beat(12), data, 0.3)
    hit(beat(12) + 2.0, data, 0.25)
    b = buzz[: int((CUT_TO_BLACK - beat(16)) * SR)]
    fx.add(beat(16), b * np.linspace(0, 1, len(b))[:, None] ** 2, 0.35)
    for i, n in enumerate(range(16, 23)):
        hit(beat(n), glitches[i % 3], 0.2 + 0.05 * i, pan=0.4 * (-1) ** i)
    build(CUT_TO_BLACK, riser_long, 0.45, stop_at_peak=True)
    # 3 · UNTIL NOW: the glass comes down and lands
    # dead air after the feed dies; the fall starts with the picture at 11.3
    build(GLASS_LANDS, stutter, 0.6, not_before=11.25)
    build(GLASS_LANDS, impact, 0.9, rev=0.3, not_before=11.25)
    hit(GLASS_LANDS, braam, 0.85, rev=0.25)
    hit(GLASS_LANDS, glass_hit, 0.55, rev=0.5)
    hit(GLASS_LANDS + 0.02, glitch_logo, 0.3)  # SIGNAL LOST
    # 4 · SEALED: each bid goes in with a glass tap, swallowed
    for i, t in enumerate(ORBS):
        x = repitch(tap, [-3, 0, -5][i])
        hit(t, filt(x, "low", 6000), 0.55, pan=[-0.3, 0.3, 0][i], rev=0.9)
        hit(t, sub, 0.35)
    # 5 · ONE PRICE
    build(BEAM_STRIKE, whoosh, 0.5)
    hit(BEAM_STRIKE, bell, 0.6, rev=0.4)
    hit(BEAM_STRIKE, sub, 0.6)
    build(DROP, riser, 0.65)
    hit(DROP, trailer_hit, 0.8, rev=0.2)
    hit(DROP, thunder, 0.45)
    hit(DROP, sparkle, 0.4, rev=0.4)
    # 6 · NO TRACE
    for i, t in enumerate((26.25, 27.64, 28.67, 29.95)):
        hit(t, glitches[i % 3], 0.25)
        hit(t, click, 0.25)
    hit(28.42, glitch_logo, 0.3)
    hit(28.42, shutter, 0.5)
    # 7 · END
    hit(END_IN - 0.1, whoosh_long, 0.5, rev=0.3)
    hit(MARK_IN, tap, 0.6, rev=0.7)
    hit(MARK_IN, glitch_logo, 0.3)
    hit(MARK_IN, sparkle, 0.35, rev=0.4)
    for f in FLIPS:
        hit(f, slide, 0.55, rev=0.15)
        hit(f + 0.16, click, 0.4)
    hit(FLIPS[-1] + 0.16, horn, 0.6, rev=0.2)
    hit(FLIPS[-1] + 0.16, sub, 0.7)
    hit(MUSIC_OUT, impact[int(peak_time(impact) * SR) - int(0.01 * SR):], 0.8, rev=0.3)
    hit(MUSIC_OUT, braam, 0.5, rev=0.3)
    return fx, wet, used


# ─── the score ──────────────────────────────────────────────────────────────
def score():
    track = decode(os.path.join(SFX, MUSIC + ".mp3"))
    off = int((MUSIC_DROP - DROP) * SR)
    m = track[off: off + N].copy()
    if len(m) < N:
        m = np.concatenate([m, np.zeros((N - len(m), 2), np.float32)])
    t = np.arange(N) / SR
    gain = np.ones(N, np.float32)
    gain *= np.clip((t - beat(1) + 0.15) / 0.15, 0, 1)  # in after the static burst
    gain[t < CUT_TO_BLACK] *= 1.6  # the arpeggio section sits low in the track; lift it
    # the feed sticks: last bar before the cut loops a 16th
    a, b = int(beat(21) * SR), int(CUT_TO_BLACK * SR)
    q = int(BEAT / 4 * SR)
    loop = m[a: a + q].copy()
    for i in range(a, b, q):
        m[i: min(i + q, b)] = loop[: min(q, b - i)]
    # dead air, then the world comes back behind the glass and slowly opens up
    gain[(t >= CUT_TO_BLACK) & (t < GLASS_LANDS)] = 0
    gain *= np.where(t >= GLASS_LANDS, np.clip((t - GLASS_LANDS) / 0.6, 0, 1), 1)
    open_at, full_at = 18.6, beat(45)
    blk = 1024
    z = None
    for i in range(int(GLASS_LANDS * SR), int(full_at * SR), blk):
        tt = i / SR
        fc = BEHIND_GLASS if tt < open_at else BEHIND_GLASS * (16000 / BEHIND_GLASS) ** ((tt - open_at) / (full_at - open_at))
        s = sos("low", min(fc, SR / 2.3), 4)
        if z is None:
            z = np.zeros((s.shape[0], 2, 2))
        m[i: i + blk], z = sosfilt(s, m[i: i + blk], axis=0, zi=z)
    m[int(GLASS_LANDS * SR): int(full_at * SR)] *= 1.6  # make up what the filter takes
    # the music stops dead on the last kick; only its reverb carries on
    stop = int(MUSIC_OUT * SR)
    gain[stop:] = 0
    m *= gain[:, None]
    ir = reverb_ir(3.5, 5000)
    last = m[stop - int(0.5 * SR): stop]
    rev_tail = np.stack([fftconvolve(last[:, c], ir[:, c]) for c in range(2)], 1)[: N - stop + int(0.5 * SR)]
    m[stop - int(0.5 * SR): stop - int(0.5 * SR) + len(rev_tail)] += rev_tail * 0.5
    return m


def vo_track():
    out = np.zeros(N, np.float32)
    for start, text in VO:
        a = voice.line(text)
        a = a / (np.abs(a).max() + 1e-6) * 0.8
        i = int(start * SR)
        out[i: i + len(a)] += a[: N - i]
    out = filt(out, "high", 55)  # the deep voice's fundamental sits ~80 Hz: keep it
    out = filt(out, "band", [90, 220]) * 0.35 + filt(out, "high", 2500) * 0.25 + out  # chest + presence
    out = np.tanh(out * 1.8) / np.tanh(1.8)
    return out


def mix(path):
    music = score()
    fx, wet, used = build_effects()
    vo = vo_track()
    ir = reverb_ir()
    rev = np.stack([fftconvolve(wet.buf[:, c], ir[:, c])[:N] for c in range(2)], 1)
    vo_rev = fftconvolve(vo, reverb_ir(1.2, 7000)[:, 0])[:N]
    # duck the music under the voice
    env = maximum_filter1d(np.abs(vo), int(0.03 * SR))
    env = uniform_filter1d(env, int(0.25 * SR))
    duck = 1 - 0.45 * np.clip(env / 0.12, 0, 1)
    out = music * 0.62 * duck[:, None] + fx.buf * 0.8 + rev * 0.5 + np.stack([vo, vo], 1) * 1.0 + vo_rev[:, None] * 0.08
    out = filt(out, "high", 22)
    meter = pyloudnorm.Meter(SR)
    out = pyloudnorm.normalize.loudness(out, meter.integrated_loudness(out), -14.0)
    knee = 0.88
    over = np.abs(out) > knee
    out[over] = np.sign(out[over]) * (knee + (1 - knee) * np.tanh((np.abs(out[over]) - knee) / (1 - knee)))
    fade = int(1.2 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    sf.write(path, out.astype(np.float32), SR, subtype="PCM_24")
    return used
