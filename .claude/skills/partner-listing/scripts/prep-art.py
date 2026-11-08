"""Shrink a partner's banner and PFP so they fit a sale's 96 KB details.

    python3 prep-art.py <banner image> <pfp image> <out dir>

Writes <out dir>/banner.webp (1200x400, cropped to 3:1 from the centre) and <out dir>/pfp.webp (320x320, cropped
square), lowering the quality until both together are under ~85 KB of base64. Needs Pillow.
"""
import base64
import io
import os
import sys

from PIL import Image

BUDGET = 85_000  # base64 bytes for both images; leaves room for text, links and requirements


def crop(im, ratio):
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w / ratio)
    return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def webp(im, q):
    b = io.BytesIO()
    im.save(b, "WEBP", quality=q, method=6)
    return b.getvalue()


banner_src, pfp_src, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
banner = crop(Image.open(banner_src).convert("RGB"), 3).resize((1200, 400), Image.LANCZOS)
pfp = crop(Image.open(pfp_src).convert("RGB"), 1).resize((320, 320), Image.LANCZOS)
pq, bq = 80, 70
while True:
    p, b = webp(pfp, pq), webp(banner, bq)
    total = len(base64.b64encode(p)) + len(base64.b64encode(b))
    if total <= BUDGET or bq <= 25:
        break
    bq -= 5
    if bq < 50 and pq > 60:
        pq -= 5
open(os.path.join(out, "banner.webp"), "wb").write(b)
open(os.path.join(out, "pfp.webp"), "wb").write(p)
print(f"banner.webp q{bq} {len(b)} B · pfp.webp q{pq} {len(p)} B · base64 total {total} B (budget {BUDGET})")
if total > BUDGET:
    sys.exit("still over budget: link the banner (https or ipfs) instead")
