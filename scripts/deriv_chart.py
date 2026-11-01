#!/usr/bin/env python3
"""Daily 2차창작 run, part 2: the three 2차창작 charts, by views gained since the previous daily reading.

usage: deriv_chart.py REPO_DIR RUN_DIR PREV OUT DAY
  RUN_DIR/derivs, RUN_DIR/songs, RUN_DIR/alts : collections saved by ArtifactData list out_dir (RUN_DIR/seed: new docs)
  PREV : the previous dchart documents saved by ArtifactData query out_dir (a directory), a file, or "-"
  OUT  : where to write the new dchart document; DAY = YYYYMMDD (Korea time)
Every link's gain is (today's views - the previous reading's views), scaled to 24 hours when the readings are not a
day apart (a link's own reading time is in the previous document's "vt" when it was added later), never below 0; a link without a previous reading (added since) has no gain yet. Charts, one row per song:
  inst  : the song's Inst link (alts/<id>.inst)
  cover : the song's Korean cover with the largest gain
  ip    : the sum of the song's three largest Korean-IP fan work gains
The document keeps every reading (views) as tomorrow's baseline, the gains, and the previous ranks. Prints a report.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, entries, vid_ok

repo, run, prev_p, out_p, day = sys.argv[1:6]
derivs, songs, alts = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs")), docs(os.path.join(run, "alts"))
for k, v in docs(os.path.join(run, "seed")).items():   # documents deriv_ids.py created in this run
    derivs.setdefault(k, v)
dv = json.load(open(os.path.join(repo, "data", "deriv_views.json"), encoding="utf-8"))
views, info, t = dv.get("views") or {}, dv.get("info") or {}, dv.get("t")
cands = []
if prev_p != "-":
    if os.path.isdir(prev_p):
        cands = list(docs(prev_p).values())
    elif os.path.exists(prev_p):
        x = json.load(open(prev_p, encoding="utf-8"))
        cands = [x.get("data", x) if "views" not in x else x]
cands = [x for x in cands if isinstance(x, dict) and x.get("day") != day and x.get("views") and x.get("t")]
prev = max(cands, key=lambda x: x["t"]) if cands else None
base, tprev = (prev or {}).get("views") or {}, (prev or {}).get("t")
vt = (prev or {}).get("vt") or {}   # reading times of links added to a reading later (default: the reading's t)
gains = {}
for vid, n in views.items():
    tp = vt.get(vid, tprev)
    if vid in base and t and tp and t > tp:
        gains[vid] = max(0, round((n - base[vid]) * 24 * 3600000 / (t - tp)))
pranks = {k: {r["id"]: r["rank"] for r in rows} for k, rows in ((prev or {}).get("charts") or {}).items()}
charts, gone, meta = {"inst": [], "cover": [], "ip": []}, set(), {}
for sid in sorted(songs):
    s = songs[sid]
    if not vid_ok(sid) or s.get("status") in ("pending", "error", "removed"):
        continue
    inst = (alts.get(sid) or {}).get("inst")
    if isinstance(inst, dict) and vid_ok(inst.get("vid")):
        v = inst["vid"]
        if v not in views:
            gone.add(v)
        elif v in gains:
            charts["inst"].append({"id": sid, "vid": v, "g": gains[v], "v": views[v]})
    d = derivs.get(sid) or {}
    for kind in ("cover", "ip"):
        got = []
        for e in entries(d, kind):
            if e["vid"] not in views:
                gone.add(e["vid"])
                continue
            if not e.get("title") and e["vid"] in info:
                meta[e["vid"]] = [info[e["vid"]].get("title", ""), info[e["vid"]].get("channel", "")]
            if e["vid"] in gains:
                got.append(e["vid"])
        got.sort(key=lambda v: -gains[v])
        if not got:
            continue
        if kind == "cover":
            charts["cover"].append({"id": sid, "vid": got[0], "g": gains[got[0]], "v": views[got[0]], "n": len(got)})
        else:
            top = got[:3]
            charts["ip"].append({"id": sid, "vids": top, "g": sum(gains[v] for v in top), "n": len(got)})
for kind, rows in charts.items():
    rows.sort(key=lambda r: (-r["g"], r["id"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        p = pranks.get(kind, {}).get(r["id"])
        if p:
            r["prev"] = p
doc = {"day": day, "t": t, "prevDay": (prev or {}).get("day"), "prevT": tprev, "views": views, "gains": gains,
       "charts": charts, "meta": meta, "gone": sorted(gone)[:300]}
json.dump(doc, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps({"links_read": len(views), "with_gain": len(gains), "baseline": (prev or {}).get("day"),
                  "rows": {k: len(v) for k, v in charts.items()}, "gone": len(gone),
                  "top": {k: v[:1] for k, v in charts.items()}, "bytes": os.path.getsize(out_p)}, ensure_ascii=False))
