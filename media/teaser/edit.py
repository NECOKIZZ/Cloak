"""The cut. Everything you see is decided here: which clip plays when, how fast, and what happens on top.

Story (41 s):
  WATCHED   0.4–5.5   spotlights find the figure. Surveillance HUD, shutter flashes, negative frames.
  TRACED    5.5–10.6  the swarm closes in, glitches build, then a hard cut to black and silence.
  UNTIL NOW 10.6–15.6 the glass slams down. The HUD dies. The figure turns to teal behind the flutes.
  SEALED    15.6–20.3 bids drift into the monolith and vanish (the music is muffled, behind glass).
  ONE PRICE 20.3–26.3 the beam strikes, the bids open, and the line snaps together on the drop.
  NO TRACE  26.3–30.6 people pass behind the glass, cut on the kicks.
  END       30.6–41.0 light sweep, the mark builds out of flutes, then it flips: Cloak → Elysium → Hyperliquid → Cloak.
"""
import math
import os
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 24
DURATION = 39.6
N_FRAMES = int(DURATION * FPS)

# Brand
INK = np.array([11, 16, 19], np.float32) / 255
TEAL = np.array([45, 115, 136], np.float32) / 255
TEAL_L = np.array([108, 182, 203], np.float32) / 255
PAPER = np.array([248, 247, 244], np.float32) / 255
AMBER = np.array([227, 169, 90], np.float32) / 255  # dark-theme seal: reads on black

FONT_BIG = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
FONT_MED = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
FONT_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf"

# Story beats (seconds on the final timeline). audio.py places its hits on the same marks.
# The music ("The mind trap - Part 1") is 130 BPM; its drop is pinned to DROP, so beat(n) is on the grid.
BEAT = 60 / 130
DROP = 23.95          # the amber line snaps together; the music drops here


def beat(n):
    return DROP + (n - 52) * BEAT


CUT_TO_BLACK = beat(23)       # 10.56: the feed dies
GLASS_LANDS = 11.95
BEAM_STRIKE = beat(47)        # 21.64
# Kicks of the drop (detected in the track, on this timeline). Acts 6–7 cut on them.
DROP_KICKS = [23.95, 24.68, 25.80, 26.25, 27.64, 28.42, 29.49, 29.95, 30.64, 31.33, 32.03, 33.18, 33.36, 33.64,
              34.28, 35.03, 35.81, 36.87, 37.33]
END_IN = 30.64
MARK_IN = 31.33
FLIPS = [33.18, 34.28, 35.81]   # Cloak → Elysium → Hyperliquid → Cloak (the last on the hardest kick)
MUSIC_OUT = 37.33
FADE_OUT = 38.5


# ─── sources ─────────────────────────────────────────────────────────────────
SRC = {}


def load_clips():
    for n in range(1, 8):
        path = os.path.join(HERE, "clips", f"{n}.mp4")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        SRC[n] = np.frombuffer(raw, np.uint8).reshape(-1, 720, 1280, 3)


def ease_in(u):
    return u * u


def ease_out(u):
    return 1 - (1 - u) ** 2


def ease_io(u):
    return u * u * (3 - 2 * u)


class Cut:
    """A piece of a clip on the timeline. src(t) maps timeline time to clip time."""

    def __init__(self, t0, t1, clip, s0, s1, ease=None, zoom=(1.0, 1.0), center=(0.5, 0.5), stutter=None,
                 src_fn=None):
        self.t0, self.t1, self.clip, self.s0, self.s1 = t0, t1, clip, s0, s1
        self.ease, self.zoom, self.center, self.stutter, self.src_fn = ease, zoom, center, stutter, src_fn

    def src(self, t):
        if self.src_fn:
            return self.src_fn(t)
        u = (t - self.t0) / (self.t1 - self.t0)
        if self.stutter and u > self.stutter[0]:
            # the tail of the cut locks into a short frame loop, like a stuck feed
            t_lock = self.t0 + self.stutter[0] * (self.t1 - self.t0)
            k = int((t - t_lock) * FPS) % self.stutter[1]
            return self.src(t_lock - 1e-6) + k / FPS
        f = self.ease(u) if self.ease else u
        return self.s0 + (self.s1 - self.s0) * f

    def zoom_at(self, t):
        u = ease_io(np.clip((t - self.t0) / (self.t1 - self.t0), 0, 1))
        return self.zoom[0] + (self.zoom[1] - self.zoom[0]) * u


def pingpong(start_t, s0, s1, speed):
    span = s1 - s0

    def f(t):
        x = (t - start_t) * speed
        k = x % (2 * span)
        return s0 + (k if k < span else 2 * span - k)
    return f


CUTS = [
    # WATCHED (on the beat grid)
    Cut(beat(1), beat(3), 1, 0.00, 0.93, zoom=(1.00, 1.06)),
    Cut(beat(3), beat(5), 1, 2.20, 3.12, zoom=(1.18, 1.22), center=(0.5, 0.62)),
    Cut(beat(5), beat(6), 1, 3.12, 3.58, zoom=(1.30, 1.30), center=(0.5, 0.62)),
    Cut(beat(6), beat(8), 1, 3.60, 4.52, zoom=(1.00, 1.08)),
    Cut(beat(8), beat(10), 1, 5.20, 6.12, zoom=(1.28, 1.36), center=(0.5, 0.6)),
    Cut(beat(10), beat(12), 1, 7.00, 7.92, zoom=(1.00, 1.10), center=(0.5, 0.45)),
    # TRACED
    Cut(beat(12), beat(16), 2, 0.60, 3.60, zoom=(1.00, 1.05)),
    Cut(beat(16), beat(20), 2, 3.60, 6.40, zoom=(1.05, 1.15)),
    Cut(beat(20), CUT_TO_BLACK, 2, 6.40, 7.60, zoom=(1.15, 1.45), stutter=(0.55, 3)),
    # UNTIL NOW (black and silent until 10.9)
    Cut(10.90, 11.30, 3, 0.60, 1.00, zoom=(1.04, 1.04)),
    Cut(11.30, GLASS_LANDS, 3, 1.00, 2.75, ease=ease_in, zoom=(1.04, 1.04)),
    Cut(GLASS_LANDS, beat(34), 3, 2.75, 8.00, zoom=(1.04, 1.16)),
    # SEALED
    Cut(beat(34), beat(44), 4, 0.30, 7.95, zoom=(1.00, 1.10)),
    # ONE PRICE
    Cut(beat(44), BEAM_STRIKE, 5, 0.00, 1.30, zoom=(1.10, 1.03), center=(0.5, 0.35)),
    Cut(BEAM_STRIKE, DROP, 5, 1.30, 4.62, ease=ease_in, zoom=(1.03, 1.12)),
    Cut(DROP, 26.25, 5, 4.62, 7.95, zoom=(1.18, 1.32), center=(0.5, 0.62)),
    # NO TRACE: cut on the kicks
    Cut(26.25, 27.64, 6, 0.00, 1.70, zoom=(1.00, 1.04)),
    Cut(27.64, 28.42, 6, 2.40, 3.40, zoom=(1.12, 1.16)),
    Cut(28.42, 28.67, 1, 7.10, 7.35, zoom=(1.10, 1.10), center=(0.5, 0.45)),  # callback: the watched figure, negative
    Cut(28.67, 29.95, 6, 4.30, 5.90, zoom=(1.00, 1.06)),
    Cut(29.95, END_IN, 6, 6.40, 7.95, zoom=(1.06, 1.20)),
    # END: the panels flare as a light sweep, then breathe under the graphics
    Cut(END_IN, END_IN + 0.6, 7, 2.60, 5.60, ease=ease_out),
    Cut(END_IN + 0.6, DURATION, 7, 5.60, 8.0, src_fn=pingpong(END_IN + 0.6, 5.60, 7.95, 0.45)),
]


def find_cut(t):
    for c in CUTS:
        if c.t0 <= t < c.t1:
            return c
    return None


def base_frame(t, shake=(0.0, 0.0)):
    c = find_cut(t)
    if c is None:
        return np.broadcast_to(INK * 0.4, (H, W, 3)).copy()
    frames = SRC[c.clip]
    i = int(np.clip(round(c.src(t) * FPS), 0, len(frames) - 1))
    z = c.zoom_at(t) * 1.5  # 720p → 1080p
    cx, cy = c.center[0] * 1280, c.center[1] * 720
    m = np.float32([[z, 0, W / 2 - z * cx + shake[0]], [0, z, H / 2 - z * cy + shake[1]]])
    # keep the frame covered when zoomed around an off-centre point
    m[0, 2] = min(0, max(W - z * 1280, m[0, 2]))
    m[1, 2] = min(0, max(H - z * 720, m[1, 2]))
    img = cv2.warpAffine(frames[i], m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return img.astype(np.float32) / 255


# ─── effects ────────────────────────────────────────────────────────────────
def rgb_split(img, px):
    if abs(px) < 0.5:
        return img
    px = int(round(px))
    out = img.copy()
    out[..., 0] = np.roll(img[..., 0], px, axis=1)
    out[..., 2] = np.roll(img[..., 2], -px, axis=1)
    return out


def glitch(img, amount, seed):
    """Horizontal band displacement + channel tears. amount 0..1."""
    if amount <= 0:
        return img
    rng = np.random.default_rng(seed)
    out = img.copy()
    for _ in range(int(3 + 14 * amount)):
        h = int(rng.integers(4, 10 + int(90 * amount)))
        y = int(rng.integers(0, H - h))
        dx = int(rng.normal(0, 140 * amount))
        band = np.roll(img[y: y + h], dx, axis=1)
        if rng.random() < 0.4:
            band = band.copy()
            band[..., int(rng.integers(0, 3))] *= rng.uniform(0.2, 1.8)
        out[y: y + h] = band
    if rng.random() < 0.35 * amount:  # a block repeats (frozen macroblock)
        bw, bh = int(rng.integers(120, 480)), int(rng.integers(40, 160))
        x, y = int(rng.integers(0, W - bw)), int(rng.integers(0, H - bh))
        out[y: y + bh, x: x + bw] = out[y: y + 1, x: x + bw]
    return out


def invert(img):
    """A photographic negative kept in the brand palette: dark ink where it was bright, paper where it was dark."""
    lum = np.clip(img @ np.array([0.2126, 0.7152, 0.0722], np.float32), 0, 1)[..., None]
    neg = 1.0 - lum
    return INK + (PAPER - INK) * neg ** 1.4 + (TEAL - INK) * (neg * (1 - neg)) * 0.8


def flash(img, amount, color=PAPER):
    return img + (color - img) * np.clip(amount, 0, 1)


def hmotion_blur(img, px):
    k = int(px) | 1
    if k < 3:
        return img
    return cv2.blur(img, (k, 1))


def pulse(t, t0, decay=8.0):
    return math.exp(-(t - t0) * decay) if t >= t0 else 0.0


# Events: (time, kind, strength). Built by place_events() so they can follow the music's kicks.
EVENTS = []
KICKS = []


def place_events():
    ev = EVENTS
    ev.clear()
    # WATCHED: shutter flashes on the punch-ins, negative frames on the jolts
    for t in (beat(3), beat(8), beat(9), beat(9.5)):
        ev.append((t, "flash", 0.85))
    ev += [(beat(5), "invert", 0.12), (beat(5), "glitch", 0.8), (beat(11.5), "invert", 0.08), (beat(11.5), "glitch", 0.9),
           (0.0, "glitch", 1.0), (beat(1), "rgb", 1.0)]
    # TRACED: glitches thicken toward the cut, on every beat
    for i, n in enumerate(range(16, 23)):
        ev.append((beat(n), "glitch", 0.25 + 0.5 * i / 6))
    ev += [(beat(20), "invert", 0.08), (beat(21), "invert", 0.08), (beat(22.5), "invert", 0.2)]
    # UNTIL NOW: the glass lands
    ev += [(GLASS_LANDS, "flash", 0.55), (GLASS_LANDS, "shake", 1.0), (GLASS_LANDS, "rgb", 0.8)]
    # ONE PRICE
    ev += [(BEAM_STRIKE, "flash", 1.0), (BEAM_STRIKE, "shake", 0.5),
           (DROP, "flash", 1.0), (DROP, "shake", 1.2), (DROP, "rgb", 1.0), (DROP, "glitch", 0.6)]
    for k in DROP_KICKS[1:4]:
        ev.append((k, "bump", 0.5))
    # NO TRACE: every cut on a kick, one negative callback
    for t in (26.25, 27.64, 28.67, 29.95):
        ev += [(t, "glitch", 0.5), (t, "rgb", 0.6)]
    ev += [(28.42, "invert", 0.25), (28.42, "glitch", 1.0)]
    # END
    ev += [(END_IN, "glitch", 0.7), (MARK_IN, "flash", 0.25), (MUSIC_OUT, "flash", 0.35)]
    for f in FLIPS:
        ev += [(f, "rgb", 0.5), (f, "bump", 0.4)]


def fx_state(t):
    s = dict(flash=0.0, invert=False, glitch=0.0, rgb=0.0, shake=0.0, bump=0.0)
    for t0, kind, k in EVENTS:
        if kind == "invert":
            if t0 <= t < t0 + k:
                s["invert"] = True
        elif kind == "flash":
            s["flash"] = max(s["flash"], k * pulse(t, t0, 10))
        elif kind == "glitch":
            if t0 <= t < t0 + 0.17:
                s["glitch"] = max(s["glitch"], k)
        elif kind == "rgb":
            s["rgb"] = max(s["rgb"], k * pulse(t, t0, 9))
        elif kind == "shake":
            s["shake"] = max(s["shake"], k * pulse(t, t0, 5))
        elif kind == "bump":
            s["bump"] = max(s["bump"], k * pulse(t, t0, 10))
    return s


# ─── type ────────────────────────────────────────────────────────────────────
_cache = {}


def text_rgba(text, size, font=FONT_BIG, color=PAPER, tracking=0.0, shadow=0.0):
    key = (text, size, font, tuple(color), tracking, shadow)
    if key in _cache:
        return _cache[key]
    f = ImageFont.truetype(font, size)
    pad = int(size * 0.8)
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + tracking * size * max(len(text) - 1, 0)
    im = Image.new("L", (int(total + 2 * pad), int(size * 1.5 + 2 * pad)), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for ch, w in zip(text, widths):
        d.text((x, pad), ch, font=f, fill=255)
        x += w + tracking * size
    a = np.asarray(im, np.float32) / 255
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = color
    rgba[..., 3] = a
    if shadow:
        s = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.3)), np.float32) / 255 * shadow
        out_a = a + s * (1 - a)
        rgba[..., :3] = (color * a[..., None] + INK * 0.3 * (s * (1 - a))[..., None]) / np.maximum(out_a, 1e-4)[..., None]
        rgba[..., 3] = out_a
    ys, xs = np.nonzero(rgba[..., 3] > 0.003)
    rgba = rgba[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    _cache[key] = rgba
    return rgba


def over(img, layer, cx, cy, alpha=1.0, sx=1.0, sy=1.0):
    if alpha <= 0.001 or sx <= 0.001 or sy <= 0.001:
        return img
    if sx != 1.0 or sy != 1.0:
        layer = cv2.resize(layer, (max(1, int(layer.shape[1] * sx)), max(1, int(layer.shape[0] * sy))),
                           interpolation=cv2.INTER_LINEAR)
    h, w = layer.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return img
    lay = layer[ya - y0: yb - y0, xa - x0: xb - x0]
    a = lay[..., 3:4] * alpha
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + lay[..., :3] * a
    return img


def slam(img, t, t_in, t_out, kicker, word, y=0.5, seed=0):
    """Mono kicker + big word. Glitches in for 4 frames, holds, glitches out fast."""
    if not t_in <= t < t_out:
        return img
    age, left = t - t_in, t_out - t
    big = text_rgba(word, 150, tracking=-0.025, shadow=0.6)
    kick = text_rgba(kicker, 24, FONT_MONO, TEAL_L, tracking=0.32, shadow=0.5) if kicker else None
    s = 1.0 + 0.06 * math.exp(-age * 14)
    alpha = 1.0
    jitter = 0
    if age < 0.17 or left < 0.09:
        rng = np.random.default_rng(int(t * FPS) + seed)
        alpha = rng.choice([0.0, 0.6, 1.0])
        jitter = int(rng.normal(0, 18))
    ky = H * y - big.shape[0] * s / 2 - 34
    if kick is not None:
        img = over(img, kick, W / 2, ky, min(1, age * 6) * alpha)
    if age < 0.17:  # chromatic ghost of the word as it arrives
        ghost = big.copy()
        ghost[..., :3] = TEAL_L
        img = over(img, ghost, W / 2 + jitter + 14, H * y, 0.5 * alpha, s, s)
        ghost[..., :3] = AMBER
        img = over(img, ghost, W / 2 + jitter - 14, H * y, 0.4 * alpha, s, s)
    return over(img, big, W / 2 + jitter, H * y, alpha, s, s)


# ─── surveillance HUD (acts 1–2) ────────────────────────────────────────────
_ADDR = np.random.default_rng(11)
LOG = [f"0x{_ADDR.bytes(2).hex()}…{_ADDR.bytes(2).hex()}  →  0x{_ADDR.bytes(2).hex()}…{_ADDR.bytes(2).hex()}   "
       f"{_ADDR.uniform(0.05, 9.9):.2f} HYPE" for _ in range(40)]


def hud(img, t):
    if t >= CUT_TO_BLACK or t < beat(1):
        return img
    mono = lambda s, size=20, c=PAPER * 0.85: text_rgba(s, size, FONT_MONO, c, tracking=0.12)
    f = int(t * FPS)
    tc = f"00:00:{int(t):02d}:{f % FPS:02d}"
    if (f // 12) % 2 == 0:
        dot = np.zeros((18, 18, 4), np.float32)
        cv2.circle(dot, (9, 9), 7, tuple(float(v) for v in AMBER) + (1.0,), -1, cv2.LINE_AA)
        img = over(img, dot, 70, 66)
    img = over(img, mono("REC"), 70 + 52, 66)
    lay = mono(tc)
    img = over(img, lay, W - 70 - lay.shape[1] / 2, 66)
    lay = mono("CAM 04 · SEQUENCER VIEW", 16, PAPER * 0.6)
    img = over(img, lay, W - 70 - lay.shape[1] / 2, 96)
    # target brackets
    c = find_cut(t)
    if c and c.clip == 1:
        bx, by, bw, bh = W / 2, H * 0.56, 300 + 40 * math.sin(t * 3), 520
        L = 46
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = int(bx + sx * bw / 2), int(by + sy * bh / 2)
                cv2.line(img, (x, y), (x - sx * L, y), tuple(float(v) for v in PAPER), 2, cv2.LINE_AA)
                cv2.line(img, (x, y), (x, y - sy * L), tuple(float(v) for v in PAPER), 2, cv2.LINE_AA)
        lay = mono("TARGET ACQUIRED" if t > beat(6) else "SCANNING…", 16, TEAL_L)
        img = over(img, lay, bx - bw / 2 + lay.shape[1] / 2, by - bh / 2 - 22)
    # transaction log while the swarm traces everything
    if c and c.clip == 2:
        n = int((t - beat(12)) * 9)
        for i in range(6):
            line = LOG[(n + i) % len(LOG)]
            lay = mono(line, 16, TEAL_L * (0.45 + 0.1 * i))
            img = over(img, lay, 70 + lay.shape[1] / 2, H - 70 - (5 - i) * 26)
        lay = mono("WALLET LINKED", 16, AMBER)
        if (f // 6) % 2:
            img = over(img, lay, W - 70 - lay.shape[1] / 2, H - 70)
    return img


def signal_lost(img, t):
    if GLASS_LANDS <= t < GLASS_LANDS + 0.55:
        rng = np.random.default_rng(int(t * FPS))
        lay = text_rgba("SIGNAL LOST", 28, FONT_MONO, PAPER, tracking=0.4)
        img = over(img, lay, W / 2 + rng.normal(0, 6), H * 0.18, rng.choice([0.4, 1.0]))
    return img


# ─── end card: the mark built from flutes, then the flips ───────────────────
def mark_layer(height):
    key = ("mark", height)
    if key in _cache:
        return _cache[key]
    d = ("M149.671 0C119.989 12.7135 73.3456 40.2595 58.5046 74.1622C41.5434 118.659 37.3031 192.822 3.38073 266.984"
         "C-2.97971 279.697 -0.859564 288.173 13.9815 294.53C62.7449 317.838 117.869 326.314 160.272 319.957"
         "C209.035 315.719 247.198 298.768 279 275.459L232.357 209.773C213.275 230.962 187.834 243.676 160.272 245.795"
         "C117.869 250.032 86.0665 226.724 86.0665 186.465C86.0665 137.73 115.749 93.2324 149.671 69.9243"
         "C172.993 84.7568 194.194 108.065 206.915 133.492L257.799 103.827C234.477 57.2108 189.954 19.0703 149.671 0Z")
    import re
    toks = re.findall(r"[MCLZ]|-?[\d.]+", d)
    pts, cur, i, cmd = [], None, 0, None
    while i < len(toks):
        if toks[i] in "MCLZ":
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd in "ML":
            cur = np.array([float(toks[i]), float(toks[i + 1])])
            pts.append(cur)
            i += 2
        else:
            p = [cur] + [np.array([float(toks[i + 2 * k]), float(toks[i + 2 * k + 1])]) for k in range(3)]
            for s in np.linspace(0, 1, 40)[1:]:
                pts.append((1 - s) ** 3 * p[0] + 3 * (1 - s) ** 2 * s * p[1] + 3 * (1 - s) * s ** 2 * p[2] + s ** 3 * p[3])
            cur = p[3]
            i += 6
    scale = 4 * height / 322.0
    poly = np.array(pts) * scale + 8
    m = Image.new("L", (int(279 * scale) + 16, int(322 * scale) + 16), 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=255)
    m = m.resize((m.width // 4, m.height // 4), Image.LANCZOS)
    a = np.asarray(m, np.float32) / 255
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = PAPER
    rgba[..., 3] = a
    _cache[key] = rgba
    return rgba


def flute_reveal(layer, u, stripe=14):
    """Reveal a layer stripe by stripe, each sliding in from alternating sides, like it's forming behind reeded glass."""
    if u >= 1:
        return layer
    out = np.zeros_like(layer)
    w = layer.shape[1]
    n = (w + stripe - 1) // stripe
    for i in range(n):
        k = np.clip(u * 1.6 - i / n * 0.6, 0, 1)
        if k <= 0:
            continue
        k = ease_out(k)
        dy = int((1 - k) * 60 * (1 if i % 2 else -1))
        x0, x1 = i * stripe, min((i + 1) * stripe, w)
        col = np.roll(layer[:, x0:x1], dy, axis=0)
        col = col.copy()
        col[..., 3] *= k
        out[:, x0:x1] = col
    return out


def lockup_layer():
    """[mark]  Launch sealed. / Trade unseen."""
    if "lockup" in _cache:
        return _cache["lockup"]
    mark = mark_layer(230)
    l1 = text_rgba("Launch sealed.", 104, tracking=-0.025)
    l2 = text_rgba("Trade unseen.", 104, tracking=-0.025)
    gap = 56
    tw = max(l1.shape[1], l2.shape[1])
    w = mark.shape[1] + gap + tw
    h = max(mark.shape[0], 250)
    out = np.zeros((h, w, 4), np.float32)
    out[(h - mark.shape[0]) // 2:(h - mark.shape[0]) // 2 + mark.shape[0], :mark.shape[1]] = mark
    x = mark.shape[1] + gap
    for lay, cy in ((l1, h / 2 - 62), (l2, h / 2 + 62)):
        y0 = int(cy - lay.shape[0] / 2)
        out[y0:y0 + lay.shape[0], x:x + lay.shape[1]] = np.maximum(out[y0:y0 + lay.shape[0], x:x + lay.shape[1]], lay)
    _cache["lockup"] = out
    return out


def plate(label, word, mark=False):
    key = ("plate", label, word, mark)
    if key in _cache:
        return _cache[key]
    big = text_rgba(word, 168, tracking=-0.03)
    lab = text_rgba(label, 24, FONT_MONO, TEAL_L, tracking=0.38) if label else None
    m = mark_layer(150) if mark else None
    row_h = max(big.shape[0], m.shape[0] if mark else 0)
    parts_w = big.shape[1] + ((m.shape[1] + 40) if mark else 0)
    top = 70 if lab is not None else 0
    w = max(parts_w, lab.shape[1] if lab is not None else 0)
    out = np.zeros((row_h + top + 20, w + 20, 4), np.float32)
    y = 10
    if lab is not None:
        x0 = (out.shape[1] - lab.shape[1]) // 2
        out[y:y + lab.shape[0], x0:x0 + lab.shape[1]] = lab
        y += top
    x = (out.shape[1] - parts_w) // 2
    if mark:
        my = y + (row_h - m.shape[0]) // 2
        out[my:my + m.shape[0], x:x + m.shape[1]] = m
        x += m.shape[1] + 40
    by = y + (row_h - big.shape[0]) // 2
    out[by:by + big.shape[0], x:x + big.shape[1]] = big
    _cache[key] = out
    return out


def flip_warp(layer, angle):
    """Rotate a layer about its horizontal axis (perspective), angle in radians, |angle| < pi/2."""
    h, w = layer.shape[:2]
    c, s = math.cos(angle), math.sin(angle)
    if c < 0.02:
        return None
    f = 3200.0
    pts = []
    for (x, y) in ((0, 0), (w, 0), (w, h), (0, h)):
        X, Y = x - w / 2, y - h / 2
        y3, z3 = Y * c, Y * s
        k = f / (f + z3)
        pts.append((X * k + w, y3 * k + h))
    dst = np.float32(pts)
    src = np.float32([(0, 0), (w, 0), (w, h), (0, h)])
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(layer, M, (2 * w, 2 * h), flags=cv2.INTER_LINEAR)
    shade = 0.55 + 0.45 * c  # the card darkens as it turns away
    out[..., :3] *= shade
    return out


STATES = None


def end_states():
    global STATES
    if STATES is None:
        STATES = [lockup_layer(), plate("LIVE ON", "Elysium"), plate("BUILT FOR", "Hyperliquid"),
                  plate(None, "Cloak", mark=True)]
    return STATES


def end_card(img, t):
    if t < END_IN:
        return img
    # darken the panels behind the type
    dim = np.clip((t - END_IN) / 0.6, 0, 1) * 0.5
    img = img * (1 - dim) + INK * dim
    if t < MARK_IN:
        return img
    st = end_states()
    cx, cy = W / 2, H * 0.47
    dur = 0.32
    idx = sum(1 for f in FLIPS if t >= f + dur / 2)
    active = [f for f in FLIPS if f <= t < f + dur]
    if active:
        f0 = active[0]
        u = (t - f0) / dur
        a = ease_io(u) * math.pi
        i = FLIPS.index(f0)
        layer, ang = (st[i], a) if a < math.pi / 2 else (st[i + 1], a - math.pi)
        warped = flip_warp(layer, ang)
        if warped is not None:
            img = over(img, warped, cx, cy)
        # a light edge rides the flip
        line_y = int(cy + math.cos(a) * layer.shape[0] / 2)
        img[max(line_y - 1, 0):line_y + 2, int(cx - 500):int(cx + 500)] += 0.5 * math.sin(a)
        return img
    layer = st[idx]
    scale = 1.0
    if idx == 0:
        u = (t - MARK_IN) / 0.55
        layer = flute_reveal(layer, u)
    if idx == 3:  # final lockup: keeps moving (slow push, one glint) while the URL lands
        since = t - FLIPS[2]
        scale = 1.0 + 0.035 * since / 3.0
        layer = glint(layer, (since - 0.45) / 0.7)
    img = over(img, layer, cx, cy, sx=scale, sy=scale)
    if idx == 3:
        k = ease_out(np.clip((t - FLIPS[2] - 0.6) / 0.4, 0, 1))
        url = text_rgba("cloak.boblabs.tech", 44, FONT_MONO, PAPER * 0.92, tracking=0.04)
        img = over(img, url, W / 2, H * 0.72 + (1 - k) * 14, k)
        k2 = ease_out(np.clip((t - FLIPS[2] - 0.9) / 0.4, 0, 1))
        lab = text_rgba("LIVE ON ELYSIUM TESTNET", 21, FONT_MONO, TEAL_L, tracking=0.32)
        img = over(img, lab, W / 2, H * 0.72 + 56, k2)
    return img


def glint(layer, u):
    """One diagonal light sweep across a layer's shapes, u 0→1."""
    if not 0 < u < 1:
        return layer
    h, w = layer.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    pos = -0.3 * w + u * 1.6 * w
    band = np.exp(-((xs + 0.35 * ys - pos) / 34) ** 2)[..., None]
    out = layer.copy()
    out[..., :3] = out[..., :3] + (1.0 - out[..., :3]) * band * 0.9 + TEAL_L * band * 0.15
    return out


# ─── titles ─────────────────────────────────────────────────────────────────
TITLES = [
    (beat(6), beat(8), "EVERY LAUNCH IS", "Watched.", 0.5),
    (beat(13), beat(16), "EVERY TRADE IS", "Traced.", 0.5),
    (12.40, 13.95, "", "Until now.", 0.5),
    (beat(35), beat(40), "EVERY BID GOES IN", "Sealed.", 0.78),
    (DROP, 26.25, "EVERYONE PAYS", "One price.", 0.2),
    (27.64, 28.42, "YOUR WALLET LEAVES", "No trace.", 0.5),
]

# ─── grade, grain, vignette ─────────────────────────────────────────────────
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.38 * (((_xx / W - 0.5) * 1.1) ** 2 + ((_yy / H - 0.5) * 1.25) ** 2) ** 1.1)[..., None]
del _yy, _xx
GRAIN = [np.random.default_rng(i).standard_normal((H // 2, W // 2)).astype(np.float32) for i in range(6)]


def grade(img):
    lum = (img @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    img = lum + (img - lum) * 0.9
    img = np.clip((img - 0.018) / 0.982, 0, 1)
    img = img * img * (3 - 2 * img) * 0.35 + img * 0.65  # gentle S-curve
    return INK * 0.7 + img * (1 - INK * 0.7)


def finish(img, f):
    g = cv2.resize(GRAIN[f % len(GRAIN)], (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    img = INK * 0.5 + (img - INK * 0.5) * VIGNETTE
    return img + g * 0.02


# ─── one frame ──────────────────────────────────────────────────────────────
def render(f):
    t = f / FPS
    s = fx_state(t)
    rng = np.random.default_rng(f)
    shake = (rng.normal(0, 22 * s["shake"]), rng.normal(0, 14 * s["shake"])) if s["shake"] > 0.02 else (0, 0)
    if CUT_TO_BLACK <= t < 10.90 or t < beat(1):
        img = np.broadcast_to(INK * 0.35, (H, W, 3)).copy()
        if t < beat(1):  # static burst before the first frame
            img = img + rng.random((H // 8, W // 8, 1)).astype(np.float32).repeat(8, 0).repeat(8, 1) * 0.18
    else:
        img = grade(base_frame(t, shake))
        if s["bump"] > 0.02:  # kick: a quick exposure bump
            img = img * (1 + 0.35 * s["bump"])
    img = hud(img, t)
    for t_in, t_out, kicker, word, y in TITLES:
        img = slam(img, t, t_in, t_out, kicker, word, y, seed=int(t_in * 10))
    img = signal_lost(img, t)
    img = end_card(img, t)
    if s["glitch"] > 0:
        img = glitch(img, s["glitch"], f)
    if s["rgb"] > 0.02:
        img = rgb_split(img, 26 * s["rgb"])
    if s["invert"]:
        img = invert(img)
    if s["flash"] > 0.01:
        img = flash(img, s["flash"])
    if t >= FADE_OUT:
        k = np.clip((t - FADE_OUT) / (DURATION - FADE_OUT), 0, 1)
        img = img * (1 - k) + INK * 0.3 * k
    img = finish(img, f)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
