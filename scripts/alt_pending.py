#!/usr/bin/env python3
"""List active songs that have no Inst / Korean version decision in the page's database yet, with the YouTube
search candidates gathered by alt_candidates.py, so the hourly Claude task can pick one (or none) for each.

usage: alt_pending.py REPO_DIR HAVE_DIR IDS_JSON SONGS_DIR [MAX]
  HAVE_DIR  : the "alts" collection saved by ArtifactData list (files <id>.json, searched recursively)
  IDS_JSON  : JSON array of active ids
  SONGS_DIR : the "songs" collection saved by ArtifactData list
Prints a JSON array (at most MAX, default 5) of {id, title, ko, artist, vocal, length_sec, inst: [...], ko_candidates: [...]}.
Songs whose candidates are not gathered yet are left for a later run.
"""
import json, os, sys

repo, have_dir, ids_path, songs_dir = sys.argv[1:5]
limit = int(sys.argv[5]) if len(sys.argv) > 5 else 5

def docs(d):
    out = {}
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".json"):
                try:
                    out[f[:-5]] = json.load(open(os.path.join(root, f), encoding="utf-8"))
                except Exception:
                    pass
    return out

have = docs(have_dir) if os.path.isdir(have_dir) else {}
songs = docs(songs_dir)
ids = json.load(open(ids_path, encoding="utf-8"))
cand_path = os.path.join(repo, "data", "alt_candidates.json")
cand = json.load(open(cand_path, encoding="utf-8")) if os.path.exists(cand_path) else {}
latest = json.load(open(os.path.join(repo, "data", "latest.json"), encoding="utf-8"))
dur = latest.get("duration") or {}
out = []
for i in ids:
    if i in have or i not in cand:
        continue
    s = songs.get(i, {})
    s = s.get("data", s) if isinstance(s, dict) else {}
    c = cand[i]
    out.append({"id": i, "title": s.get("title"), "ko": s.get("ko"), "artist": s.get("artist"), "vocal": s.get("vocal"),
                "length_sec": dur.get(i), "inst": c.get("inst", [])[:10], "ko_candidates": c.get("ko", [])[:10]})
    if len(out) >= limit:
        break
print(json.dumps(out, ensure_ascii=False))
