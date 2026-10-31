#!/usr/bin/env python3
"""Pick the songs a viewer asked to search (2차창작) and write deriv/req.json for the deriv-search workflow.

usage: deriv_request.py REPO_DIR RUN_DIR [MAX]
  RUN_DIR/dreq, RUN_DIR/derivs, RUN_DIR/songs : collections saved by ArtifactData list out_dir
A request dreq/<song id> = {"at": ms} is open while derivs/<song id>.searchedAt is older than it.
Writes REPO_DIR/deriv/req.json for the oldest MAX (default 8) open requests of live songs and prints
{"ids": [...], "open": total open requests, "t": epoch seconds}.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, vid_ok

repo, run = sys.argv[1:3]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 8
reqs, derivs, songs = docs(os.path.join(run, "dreq")), docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
open_ = []
for sid, r in reqs.items():
    s = songs.get(sid)
    if not vid_ok(sid) or not s or s.get("status") in ("pending", "error", "removed"):
        continue
    at = r.get("at") or 0
    if at > ((derivs.get(sid) or {}).get("searchedAt") or 0):
        open_.append((at, sid))
open_.sort()
pick = [sid for _, sid in open_[:limit]]
t = int(time.time())
os.makedirs(os.path.join(repo, "deriv"), exist_ok=True)
json.dump({"t": t, "songs": [{"id": sid, "title": songs[sid].get("title") or "", "ko": songs[sid].get("ko") or "",
                              "artist": songs[sid].get("artist") or ""} for sid in pick]},
          open(os.path.join(repo, "deriv", "req.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(json.dumps({"ids": pick, "open": len(open_), "t": t}))
