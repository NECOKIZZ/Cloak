"""End-of-thread card for long X threads: python3 end_of_thread.py → end-of-thread.png (1600×900)."""
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900
INK = np.array([11, 16, 19], np.float32) / 255
TEAL = np.array([45, 115, 136], np.float32) / 255
TEAL_L = (108, 182, 203)
PAPER = (248, 247, 244)
AMBER = np.array([227, 169, 90], np.float32) / 255
FONT_BIG = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
FONT_BODY = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
FONT_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf"
MARK = os.path.join(HERE, "..", "..", "apps", "web", "public", "brand", "cloak-mark.svg")


def mark_polygon(height):
    """The Cloak mark from the brand SVG, flattened to a polygon `height` px tall."""
    d = re.search(r'd="([^"]+)"', open(MARK).read()).group(1)
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
            for s in np.linspace(0, 1, 48)[1:]:
                pts.append((1 - s) ** 3 * p[0] + 3 * (1 - s) ** 2 * s * p[1] + 3 * (1 - s) * s ** 2 * p[2] + s ** 3 * p[3])
            cur = p[3]
            i += 6
    return np.array(pts) * (height / 322.0)


def fluted(img, width=46, spread=2.6):
    """Reeded glass: each vertical flute shows a mirrored, wider slice of what's behind it."""
    x = np.arange(img.shape[1], dtype=np.float32)
    u = (x % width) / width - 0.5
    centre = x - (x % width) + width / 2
    src = np.clip(centre - u * width * spread, 0, img.shape[1] - 1).astype(np.int32)
    shade = 0.82 + 0.22 * np.cos(u * np.pi) + 0.16 * np.exp(-((u - 0.42) / 0.035) ** 2)
    return img[:, src] * shade[None, :, None]


def background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.exp(-(((xx - W * 0.86) / (W * 0.30)) ** 2 + ((yy - H * 0.45) / (H * 0.75)) ** 2))[..., None]
    img = INK + (TEAL - INK) * glow * 0.95
    ghost = np.zeros((H, W), np.float32)  # the banner's ghost mark, behind the glass
    cv2.fillPoly(ghost, [(mark_polygon(860) + [W * 0.64, H * 0.03]).astype(np.int32)], 1.0, cv2.LINE_AA)
    img = img + cv2.GaussianBlur(ghost, (0, 0), 14)[..., None] * np.array(TEAL_L, np.float32) / 255 * 0.55
    img = cv2.GaussianBlur(img, (0, 0), 6)
    img = fluted(img)
    fade = np.clip((xx / W - 0.30) / 0.35, 0, 1)[..., None]  # glass gives way to ink on the left, where the type sits
    img = INK + (img - INK) * (0.18 + 0.82 * fade)
    vignette = 1 - 0.35 * (((xx / W - 0.5) * 1.1) ** 2 + ((yy / H - 0.5) * 1.3) ** 2)
    img = INK + (img - INK) * vignette[..., None]
    grain = np.random.default_rng(1).standard_normal((H, W, 1)).astype(np.float32) * 0.012
    return np.clip(img + grain, 0, 1)


def orb_line(img, x0, y, n=9, r=9, gap=30):
    """The amber 'one price' line from the teaser: n orbs in a row, glowing."""
    glow = np.zeros((H, W), np.float32)
    core = np.zeros((H, W), np.float32)
    for k in range(n):
        c = (int(x0 + k * gap), int(y))
        cv2.circle(core, c, r, 1.0, -1, cv2.LINE_AA)
        cv2.circle(glow, c, r + 4, 1.0, -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 14) * 1.6
    hot = AMBER + (1 - AMBER) * 0.55
    img = img + glow[..., None] * AMBER * 0.6
    return img * (1 - core[..., None]) + hot * core[..., None]


def tracked(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + tracking


def main():
    img = background()
    left = 128
    img = orb_line(img, left + 10, 568)
    im = Image.fromarray((img * 255 + 0.5).astype(np.uint8))
    d = ImageDraw.Draw(im)
    tracked(d, (left, 236), "END OF THREAD", ImageFont.truetype(FONT_MONO, 26), TEAL_L, 7)
    d.text((left - 6, 286), "Thread sealed.", font=ImageFont.truetype(FONT_BIG, 150), fill=PAPER)
    d.text((left, 474), "Thanks for reading. Launch sealed. Trade unseen.",
           font=ImageFont.truetype(FONT_BODY, 34), fill=tuple(int(c * 0.72) for c in PAPER))
    # sign-off: the mark and the URL
    poly = mark_polygon(52) + [left, 718]
    d.polygon([tuple(p) for p in poly], fill=PAPER)
    d.text((left + 72, 728), "cloak.boblabs.tech", font=ImageFont.truetype(FONT_MONO, 30), fill=PAPER)
    tracked(d, (left + 72, 770), "LIVE ON ELYSIUM TESTNET", ImageFont.truetype(FONT_MONO, 17), TEAL_L, 4)
    out = os.path.join(HERE, "end-of-thread.png")
    im.save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()
