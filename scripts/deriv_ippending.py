#!/usr/bin/env python3
"""IP sweep: show each song's search results for the IP so the Claude task can judge them.

usage: deriv_ippending.py REPO_DIR RUN_DIR IDS IP_NAME
Only results whose title contains the song's name are shown (at most 15 per song): title, channel, views on the search
page, length and "kw_in_title" (the title or channel contains one of the IP's search keywords or its name).
Saves RUN_DIR/ipcands.json = {song id: [candidates]} and prints, per song, its current IP fan works and the numbered
candidates (an empty list when nothing came up).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, norm, entries

repo, run, ids, ipname = sys.argv[1], sys.argv[2], [i for i in sys.argv[3].split(",") if i], sys.argv[4]
derivs, songs = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
cand = json.load(open(os.path.join(repo, "data", "deriv_ipcands.json"), encoding="utf-8"))
lp = os.path.join(repo, "data", "latest.json")
info = (json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}).get("info", {})
saved, out = {}, []
for sid in ids:
    s, d, c = songs.get(sid, {}), derivs.get(sid, {}), cand.get(sid) or {}
    if c.get("ip") != ipname:
        out.append({"id": sid, "error": "no sweep results for this IP"})
        continue
    taken = set(d.get("hide") or []) | set(songs) | {e["vid"] for k in ("cover", "ip") for e in entries(d, k)}
    own = norm((info.get(sid) or {}).get("channel"))
    names = [n for n in (norm(s.get("ko")), norm(s.get("title"))) if len(n) >= 2]
    keys = [norm(k) for k in set([ipname] + [x.get("kw", "") for x in c.get("c", [])]) if len(norm(k)) >= 2]
    lst = []
    for x in c.get("c", []):
        if x["vid"] in taken or (own and norm(x.get("channel")) == own):
            continue
        if not any(n in norm(x["title"]) for n in names):
            continue
        x = dict(x)
        x["kw_in_title"] = any(k in norm(x["title"] + " " + x.get("channel", "")) for k in keys)
        lst.append(x)
        taken.add(x["vid"])
    lst.sort(key=lambda x: (not x["kw_in_title"], -(x.get("views") or 0)))
    lst = lst[:15]
    saved[sid] = lst
    out.append({"id": sid, "ko": s.get("ko"), "title": s.get("title"), "artist": s.get("artist"),
                "now_ip": [{"title": e.get("title"), "ip": e.get("ip")} for e in entries(d, "ip")],
                "candidates": [dict(i=n, title=x["title"], channel=x["channel"], views=x.get("views"), length=x.get("length"),
                                    kw_in_title=x["kw_in_title"]) for n, x in enumerate(lst)]})
json.dump(saved, open(os.path.join(run, "ipcands.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
