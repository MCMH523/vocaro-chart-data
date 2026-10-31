#!/usr/bin/env python3
"""Daily 2차창작 run, part 2: the 2차창작 chart.

usage: deriv_chart.py REPO_DIR RUN_DIR PREV OUT DAY
  RUN_DIR/derivs, RUN_DIR/songs : collections saved by ArtifactData list out_dir
  PREV : the previous dchart document saved by ArtifactData query out_dir (a file or a directory), or "-"
  OUT  : where to write the new dchart document; DAY = YYYYMMDD (Korea time)
A song's score is the average view count of its links (Korean covers + Korean-IP fan works, up to 10) as read by
the deriv-views workflow; links YouTube no longer returns are left out. Songs without a readable link are not ranked.
Prints a short JSON report.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, entries, vid_ok

repo, run, prev_p, out_p, day = sys.argv[1:6]
derivs, songs = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
dv = json.load(open(os.path.join(repo, "data", "deriv_views.json"), encoding="utf-8"))
views, info = dv.get("views") or {}, dv.get("info") or {}
prev = None
if prev_p != "-":
    if os.path.isdir(prev_p):
        ds = [x for x in docs(prev_p).values() if isinstance(x, dict) and x.get("day") != day]
        prev = max(ds, key=lambda x: x.get("t") or 0) if ds else None
    elif os.path.exists(prev_p):
        prev = json.load(open(prev_p, encoding="utf-8"))
        prev = prev.get("data", prev) if "rows" not in prev else prev
prank = {r["id"]: r for r in (prev or {}).get("rows", []) if prev and prev.get("day") != day}
rows, used, gone, meta = [], {}, [], {}
for sid, d in derivs.items():
    s = songs.get(sid)
    if not vid_ok(sid) or not s or s.get("status") in ("pending", "error", "removed"):
        continue
    nc = ni = 0
    tot = []
    for kind in ("cover", "ip"):
        for e in entries(d, kind)[:5]:
            v = views.get(e["vid"])
            if v is None:
                gone.append(e["vid"])
                continue
            used[e["vid"]] = v
            tot.append(v)
            if kind == "cover":
                nc += 1
            else:
                ni += 1
            if not e.get("title") and e["vid"] in info:
                meta[e["vid"]] = [info[e["vid"]].get("title", ""), info[e["vid"]].get("channel", "")]
    if tot:
        rows.append({"id": sid, "avg": round(sum(tot) / len(tot)), "n": len(tot), "nc": nc, "ni": ni})
rows.sort(key=lambda r: (-r["avg"], r["id"]))
for i, r in enumerate(rows):
    r["rank"] = i + 1
    p = prank.get(r["id"])
    if p:
        r["prev"] = p.get("rank")
        r["pavg"] = p.get("avg")
doc = {"day": day, "t": dv.get("t"), "rows": rows, "views": used, "meta": meta, "gone": sorted(set(gone))[:300],
       "prevDay": (prev or {}).get("day") if prev and prev.get("day") != day else None}
json.dump(doc, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps({"songs": len(rows), "links": len(used), "gone": len(set(gone)), "top": rows[:3], "bytes": os.path.getsize(out_p)}, ensure_ascii=False))
