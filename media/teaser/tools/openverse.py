"""Search Openverse for CC0 / CC-BY audio and download picks with their attribution.

  python3 tools/openverse.py search "glass impact" [--music] [-n 15]
  python3 tools/openverse.py get <id> <name>     → sfx/<name>.mp3 and an entry in sfx/credits.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(HERE, "sfx")
OK_LICENSES = {"cc0", "by", "pdm"}  # free for a commercial promo; "by" needs credit
SOURCES = "jamendo,wikimedia_audio"  # freesound's CDN is not reachable from this environment


UA = "CloakTeaserBuilder/1.0 (https://github.com/NECOKIZZ/Cloak; sound design for a project teaser)"


def fetch(url, tries=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            time.sleep(min(int(e.headers.get("Retry-After") or 0) or 30 * (i + 1), 900) + 5)
        except OSError:
            if i == tries - 1:
                raise


def search(q, music=False, n=15):
    params = {"q": q, "license": ",".join(sorted(OK_LICENSES)), "page_size": n, "source": SOURCES}
    if music:
        params["category"] = "music"
    d = json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))
    for r in d["results"]:
        dur = (r.get("duration") or 0) / 1000
        tags = ",".join(t["name"] for t in (r.get("tags") or [])[:8])
        print(f"{r['id']}  {dur:6.1f}s  {r['license']:<4} {r['source']:<9} {r['title'][:55]!r}  [{tags[:70]}]")


def get(id_, name):
    r = json.loads(fetch(API + id_ + "/"))
    if r["license"] not in OK_LICENSES:
        sys.exit(f"license {r['license']} not allowed")
    os.makedirs(SFX, exist_ok=True)
    ext = os.path.splitext(urllib.parse.urlparse(r["url"]).path)[1] or ".mp3"
    path = os.path.join(SFX, name + ext)
    data = fetch(r["url"])
    with open(path, "wb") as f:
        f.write(data)
    credits_path = os.path.join(SFX, "credits.json")
    credits = json.load(open(credits_path)) if os.path.exists(credits_path) else {}
    credits[name] = {k: r.get(k) for k in ("id", "title", "creator", "creator_url", "license", "license_version",
                                          "license_url", "foreign_landing_url", "source", "attribution")}
    json.dump(credits, open(credits_path, "w"), indent=2)
    print(path)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "search":
        args = sys.argv[2:]
        music = "--music" in args
        n = int(args[args.index("-n") + 1]) if "-n" in args else 15
        q = [a for i, a in enumerate(args) if not a.startswith("-") and (i == 0 or args[i - 1] != "-n")][0]
        search(q, music, n)
    elif cmd == "get":
        get(sys.argv[2], sys.argv[3])
