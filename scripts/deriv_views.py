#!/usr/bin/env python3
"""Fetch view counts, titles and channels of the 2차창작 links (Korean covers and Korean-IP fan works).

Runs in GitHub Actions when deriv/ids.json is pushed by the page's daily noon Claude task.
deriv/ids.json = {"t": epoch seconds, "ids": [video ids]}. Uses videos.list (50 ids per call, 1 quota unit each)
with the YT_API_KEY secret and writes data/deriv_views.json:
{"req": t, "t": ms, "views": {id: n}, "info": {id: {"title", "channel"}}, "missing": [...], "failed": [...]}.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("YT_API_KEY", "").strip()
if not KEY:
    sys.exit("YT_API_KEY secret is missing")
req = json.load(open(os.path.join(ROOT, "deriv", "ids.json"), encoding="utf-8"))
ids = list(dict.fromkeys(i for i in req.get("ids", []) if isinstance(i, str) and re.fullmatch(r"[\w-]{11}", i)))

views, info, failed = {}, {}, []
for i in range(0, len(ids), 50):
    batch = ids[i:i + 50]
    for attempt in range(3):
        try:
            q = urllib.parse.urlencode({"part": "statistics,snippet", "id": ",".join(batch), "key": KEY,
                                        "fields": "items(id,statistics(viewCount),snippet(title,channelTitle))",
                                        "quotaUser": "deriv%d%d" % (int(time.time()), attempt)})
            with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30) as r:
                data = json.load(r)
            for it in data.get("items", []):
                n = it.get("statistics", {}).get("viewCount")
                if n is not None:
                    views[it["id"]] = int(n)
                sn = it.get("snippet", {})
                info[it["id"]] = {"title": str(sn.get("title", ""))[:200], "channel": str(sn.get("channelTitle", ""))[:80]}
            break
        except Exception as e:
            err = str(e)
            time.sleep(3 * (attempt + 1))
    else:
        failed.extend(batch)
        print("batch failed:", err, file=sys.stderr)

out = {"req": req.get("t"), "t": int(datetime.now(timezone.utc).timestamp() * 1000), "count": len(views),
       "views": views, "info": info, "missing": [i for i in ids if i not in views and i not in failed], "failed": failed}
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "data", "deriv_views.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("fetched %d/%d" % (len(views), len(ids)))
