"""Browse and download Mixkit sound effects (free for commercial use, no attribution required:
https://mixkit.co/license/#sfxFree).

  python3 tools/mixkit.py list whoosh impact glitch      → id, title, length for each category page
  python3 tools/mixkit.py get <id> <name>                → sfx/<name>.mp3, recorded in sfx/credits.json
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(HERE, "sfx")
UA = "Mozilla/5.0 (CloakTeaserBuilder/1.0; +https://github.com/NECOKIZZ/Cloak)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def items(category, page=1):
    url = f"https://mixkit.co/free-sound-effects/{category}/" + (f"?page={page}" if page > 1 else "")
    try:
        s = fetch(url).decode("utf-8", "replace")
    except OSError:
        return []
    parts = re.split(r'data-audio-player-preview-url-value="https://assets\.mixkit\.co/active_storage/sfx/(\d+)/\d+-preview\.mp3"', s)
    out = []
    for k in range(1, len(parts), 2):
        blk = parts[k + 1]
        title = re.search(r"<h2[^>]*>\s*(.*?)\s*</h2>", blk, re.S)
        dur = re.search(r"\b(\d+:\d\d)\b", re.sub("<[^>]+>", " ", blk))
        out.append((parts[k], title.group(1).strip() if title else "?", dur.group(1) if dur else "?"))
    return out


def get(id_, name):
    os.makedirs(SFX, exist_ok=True)
    path = os.path.join(SFX, name + ".mp3")
    data = fetch(f"https://assets.mixkit.co/active_storage/sfx/{id_}/{id_}-preview.mp3")
    with open(path, "wb") as f:
        f.write(data)
    credits_path = os.path.join(SFX, "credits.json")
    credits = json.load(open(credits_path)) if os.path.exists(credits_path) else {}
    credits[name] = {"id": id_, "source": "mixkit", "license": "Mixkit Sound Effects Free License",
                     "license_url": "https://mixkit.co/license/#sfxFree",
                     "url": f"https://assets.mixkit.co/active_storage/sfx/{id_}/{id_}-preview.mp3"}
    json.dump(credits, open(credits_path, "w"), indent=2)
    print(path)


if __name__ == "__main__":
    if sys.argv[1] == "list":
        for cat in sys.argv[2:]:
            seen = set()
            print(f"### {cat}")
            for page in (1, 2):
                for id_, title, dur in items(cat, page):
                    if id_ not in seen:
                        seen.add(id_)
                        print(f"  {id_:>6}  {dur:>5}  {title}")
    elif sys.argv[1] == "get":
        get(sys.argv[2], sys.argv[3])
