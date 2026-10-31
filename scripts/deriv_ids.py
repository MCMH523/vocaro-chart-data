#!/usr/bin/env python3
"""Daily 2차창작 run, part 1: list every link to read, and seed documents for songs that only have a Korean
version link from the hourly task (alts/<id>.ko) and no derivs document yet.

usage: deriv_ids.py REPO_DIR RUN_DIR T_MS
  RUN_DIR/derivs, RUN_DIR/alts, RUN_DIR/songs : collections saved by ArtifactData list out_dir
Writes REPO_DIR/deriv/ids.json ({"t": epoch seconds, "ids": [...]}) and RUN_DIR/seed/<id>.json, and prints
{"ids": n, "songs": n, "seed": [[ArtifactData "set" writes for the new documents (no if_version)], ...]}: one inner
array per batch of at most 50 writes (usually none or one).
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, entries, vid_ok

repo, run, t_ms = sys.argv[1], sys.argv[2], int(sys.argv[3])
derivs, alts, songs = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "alts")), docs(os.path.join(run, "songs"))
live = {k for k, s in songs.items() if vid_ok(k) and s.get("status") not in ("pending", "error", "removed")}
os.makedirs(os.path.join(run, "seed"), exist_ok=True)
seed, ids, n = [], [], 0
for sid in sorted(live):
    d = derivs.get(sid)
    if d is None:
        ko = (alts.get(sid) or {}).get("ko")
        if isinstance(ko, dict) and vid_ok(ko.get("vid")) and ko["vid"] != sid:
            e = {"vid": ko["vid"], "title": str(ko.get("title") or "")[:200], "channel": str(ko.get("channel") or "")[:80]}
            if ko.get("kind") == "cover":
                e["kind"] = "cover"
            d = {"cover": [e], "ip": [], "hide": [], "at": t_ms, "seeded": True}
            path = os.path.abspath(os.path.join(run, "seed", sid + ".json"))
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            seed.append({"op": "set", "collection": "derivs", "doc_id": sid, "file_path": path})
    if not d:
        continue
    vs = [e["vid"] for k in ("cover", "ip") for e in entries(d, k)][:10]
    if vs:
        n += 1
    ids += vs
ids = list(dict.fromkeys(ids))
os.makedirs(os.path.join(repo, "deriv"), exist_ok=True)
json.dump({"t": int(time.time()), "ids": ids}, open(os.path.join(repo, "deriv", "ids.json"), "w"), indent=0)
print(json.dumps({"ids": len(ids), "songs": n, "seed": [seed[i:i + 50] for i in range(0, len(seed), 50)]}, ensure_ascii=False))
