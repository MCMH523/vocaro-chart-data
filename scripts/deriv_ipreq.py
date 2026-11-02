#!/usr/bin/env python3
"""IP sweep: pick the next songs to search for one Korean IP across the whole chart, and write deriv/req.json.

usage: deriv_ipreq.py REPO_DIR RUN_DIR [MAX]
  RUN_DIR/dipreq, RUN_DIR/derivs, RUN_DIR/songs : collections saved by ArtifactData list out_dir
A sweep request dipreq/<key> = {"ip": name, "kws": [search keywords], "at": ms, "paused"?, "ids"?} covers every live
song, or only the live songs in "ids" when the viewer chose songs (at most 20); a paused one is skipped. A song is done
for it once derivs/<song>.ipSwept[name] is not older than "at". Takes the sweep with chosen songs first (they finish
in one run), else the oldest sweep that still has songs to do,
writes REPO_DIR/deriv/req.json for at most MAX (default 20) of them and prints
{"ip": name, "kws": [...], "ids": [...], "left_after": n (songs left in every open sweep after this batch, so the task
keeps chaining), "left_this": n, "total": n, "chosen": bool, "open_sweeps": n} ({"ids": []} when none).
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, vid_ok

repo, run = sys.argv[1:3]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
reqs, derivs, songs = docs(os.path.join(run, "dipreq")), docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
live = sorted(k for k, s in songs.items() if vid_ok(k) and s.get("status") not in ("pending", "error", "removed"))
live_set = set(live)
sweeps = []
for key, r in reqs.items():
    name, at = str(r.get("ip") or "").strip(), r.get("at") or 0
    if not name or r.get("paused"):
        continue
    chosen = r.get("ids") if isinstance(r.get("ids"), list) else None
    scope = [k for k in dict.fromkeys(chosen) if k in live_set][:20] if chosen is not None else live
    todo = [k for k in scope if ((derivs.get(k) or {}).get("ipSwept") or {}).get(name, 0) < at]
    if todo:
        kws = [str(k).strip() for k in (r.get("kws") or []) if str(k).strip()][:3] or [name]
        sweeps.append((0 if chosen is not None else 1, at, name, kws, todo, len(scope)))
sweeps.sort(key=lambda x: (x[0], x[1]))
if not sweeps:
    print(json.dumps({"ids": [], "open_sweeps": 0}))
    sys.exit(0)
_, at, name, kws, todo, total = sweeps[0]
pick = todo[:limit]
os.makedirs(os.path.join(repo, "deriv"), exist_ok=True)
json.dump({"t": int(time.time()), "ip": {"name": name, "kws": kws},
           "songs": [{"id": k, "title": songs[k].get("title") or "", "ko": songs[k].get("ko") or "", "artist": songs[k].get("artist") or ""} for k in pick]},
          open(os.path.join(repo, "deriv", "req.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(json.dumps({"ip": name, "kws": kws, "ids": pick, "left_after": len(todo) - len(pick) + sum(len(x[4]) for x in sweeps[1:]), "left_this": len(todo) - len(pick), "total": total, "chosen": sweeps[0][0] == 0, "open_sweeps": len(sweeps)}, ensure_ascii=False))
