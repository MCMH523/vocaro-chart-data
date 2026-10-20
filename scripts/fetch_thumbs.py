#!/usr/bin/env python3
"""Make a 120x120 cover thumbnail for every song in songs.json that does not have one yet.

Runs in GitHub Actions after fetch_views.py (the runner can reach i.ytimg.com; the chart page and the Claude
workspace cannot). Each thumbnail is the centre square of the video's mqdefault.jpg (hqdefault.jpg as a
fallback), saved as data/thumbs/<id>.jpg. The hourly Claude task copies new ones into the page's database
with thumb_writes.py. Needs Pillow.
"""
import io, json, os, re, sys, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "thumbs")
os.makedirs(OUT, exist_ok=True)
songs = json.load(open(os.path.join(ROOT, "songs.json"), encoding="utf-8"))
ids = [i for i in songs.get("ids", []) + songs.get("pending", []) if isinstance(i, str) and re.fullmatch(r"[\w-]{11}", i)]
todo = [i for i in dict.fromkeys(ids) if not os.path.exists(os.path.join(OUT, i + ".jpg"))]

def grab(vid, name):
    req = urllib.request.Request("https://i.ytimg.com/vi/%s/%s" % (vid, name), headers={"User-Agent": "vocaro-chart"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")

made, bad = [], []
for vid in todo[:200]:
    try:
        try:
            im = grab(vid, "mqdefault.jpg")          # 320x180, 16:9 without bars
        except Exception:
            im = grab(vid, "hqdefault.jpg")          # 480x360 with letterbox bars: crop the 16:9 band first
            band = round(im.width * 9 / 16); top = (im.height - band) // 2
            im = im.crop((0, top, im.width, top + band))
        side = min(im.size); left = (im.width - side) // 2; top = (im.height - side) // 2
        im = im.crop((left, top, left + side, top + side)).resize((120, 120), Image.LANCZOS)
        if max(b - a for a, b in im.getextrema()) < 8:
            raise ValueError("blank image")
        im.save(os.path.join(OUT, vid + ".jpg"), "JPEG", quality=78, optimize=True)
        made.append(vid)
    except Exception as e:
        bad.append("%s %s" % (vid, e))
print("thumbs made %d, failed %d" % (len(made), len(bad)))
for b in bad:
    print("  " + b, file=sys.stderr)
