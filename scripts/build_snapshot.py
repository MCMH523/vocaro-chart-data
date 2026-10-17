#!/usr/bin/env python3
"""Turn data/latest.json into one snapshot document for the chart page (used by the hourly Claude task).

usage: build_snapshot.py LATEST_JSON PREV_SNAPSHOT_JSON ACTIVE_IDS_JSON OUT_JSON [EXTRA_JSON]
  PREV_SNAPSHOT_JSON: the newest snapshot document as saved by ArtifactData (or "-" if none)
  ACTIVE_IDS_JSON:    a JSON array of the ids that should be recorded
  EXTRA_JSON:         optional {id: count} fetched another way for ids latest.json lacks
Prints a JSON report; writes OUT_JSON only when there is something to record.
"""
import json, sys, time
from datetime import datetime, timezone

latest_p, prev_p, ids_p, out_p = sys.argv[1:5]
extra = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
latest = json.load(open(latest_p, encoding="utf-8"))
prev = {}
prev_t = 0
if prev_p != "-":
    d = json.load(open(prev_p, encoding="utf-8"))
    d = d.get("data", d)
    prev, prev_t = d.get("views", {}) or {}, d.get("t", 0) or 0
ids = json.load(open(ids_p, encoding="utf-8"))

now_ms = int(time.time() * 1000)
t = int(latest.get("t", 0))
age_min = round((now_ms - t) / 60000, 1)
hour_start = now_ms // 3600000 * 3600000
stale_file = t <= prev_t or t < hour_start         # no reading from this hour yet (the chart cuts on the hour)
src = {} if stale_file else dict(latest.get("views", {}))
src_t = t if not stale_file else now_ms
for k, v in extra.items():
    src.setdefault(k, int(v))
if extra and stale_file:
    src_t = now_ms

views, rejected, missing, increased = {}, [], [], 0
for i in ids:
    n = src.get(i)
    if n is None:
        missing.append(i)
        continue
    p = prev.get(i)
    if p is not None and not (p <= n <= p * 1.5 + 3_000_000):
        rejected.append({"id": i, "prev": p, "new": n})
        continue
    if p is not None and n > p:
        increased += 1
    views[i] = int(n)

dt = datetime.fromtimestamp(src_t / 1000, tz=timezone.utc)
uh = dt.hour
report = {"stamp": dt.strftime("%Y%m%dT%H%M"), "t": src_t, "fileAgeMin": age_min, "staleFile": stale_file, "fileAt": t,
          "recorded": len(views), "increased": increased, "missing": missing, "rejected": rejected,
          "nothingIncreased": bool(prev) and increased == 0}
if views and not report["nothingIncreased"]:
    doc = {"t": src_t, "source": "youtube-api" + ("" if stale_file else "-gha"), "keep": uh in (3, 9, 15, 21),
           "noon": uh == 3, "views": views}
    json.dump(doc, open(out_p, "w", encoding="utf-8"), separators=(",", ":"))
    report["written"] = out_p
print(json.dumps(report, ensure_ascii=False))
