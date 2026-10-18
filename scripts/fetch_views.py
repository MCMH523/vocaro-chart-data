#!/usr/bin/env python3
"""Fetch current YouTube view counts for every id in songs.json and write data/latest.json.

Runs hourly in GitHub Actions. Needs the YT_API_KEY secret. Uses only the standard library.
videos.list costs 1 quota unit per call (whatever parts are asked for) and takes up to 50 ids, so 1,000 songs
cost 20 units an hour. The snippet part adds each video's upload time, used for the year filter and anniversaries.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("YT_API_KEY", "").strip()
if not KEY:
    sys.exit("YT_API_KEY secret is missing")

with open(os.path.join(ROOT, "songs.json"), encoding="utf-8") as f:
    ids = [i for i in json.load(f).get("ids", []) if isinstance(i, str) and len(i) == 11]
ids = list(dict.fromkeys(ids))  # unique, keep order

def call(batch, attempt):
    q = urllib.parse.urlencode({"part": "statistics,snippet", "id": ",".join(batch), "key": KEY,
                                "quotaUser": "gha%d%d" % (int(time.time()), attempt)})
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?" + q,
                                 headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

views, published, failed = {}, {}, []
for i in range(0, len(ids), 50):
    batch = ids[i:i + 50]
    for attempt in range(3):
        try:
            data = call(batch, attempt)
            for it in data.get("items", []):
                n = it.get("statistics", {}).get("viewCount")
                if n is not None:
                    views[it["id"]] = int(n)
                p = it.get("snippet", {}).get("publishedAt")
                if isinstance(p, str) and len(p) <= 32:
                    published[it["id"]] = p
            break
        except Exception as e:  # network or API error: retry, then give up on this batch
            err = str(e)
            time.sleep(3 * (attempt + 1))
    else:
        failed.extend(batch)
        print("batch failed:", err, file=sys.stderr)

if not views:
    sys.exit("no view counts fetched")

now = datetime.now(timezone.utc)
out = {
    "t": int(now.timestamp() * 1000),
    "fetchedAt": now.isoformat(timespec="seconds"),
    "count": len(views),
    "views": views,
    "published": published,
    "missing": [i for i in ids if i not in views and i not in failed],  # private or deleted videos
    "failed": failed,                                                   # batches the API did not answer
}
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "latest.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("fetched %d/%d" % (len(views), len(ids)))
