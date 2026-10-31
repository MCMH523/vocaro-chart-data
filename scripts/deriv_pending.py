#!/usr/bin/env python3
"""Show the 2차창작 search results of the requested songs so the Claude task can judge them.

usage: deriv_pending.py REPO_DIR RUN_DIR IDS
  IDS : comma-separated song ids (from deriv_request.py)
Saves RUN_DIR/cands.json = {song id: [candidates]} and prints, per song: the song, the entries a viewer added by hand
("keep", always kept) and one numbered list of candidates (from the cover searches and the IP searches together):
title, channel, views on the search page, length, the IP keyword it was searched with ("searched_with"), "match"
(the title contains the song's name), "hangul" (the title has Korean letters) and "now" (one of the song's current automatic entries, kind "cover" or "ip").
Titles that contain the song's name come first, then titles with Korean letters, then by views.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, norm, entries

repo, run, ids = sys.argv[1], sys.argv[2], [i for i in sys.argv[3].split(",") if i]
derivs, songs = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
cp = os.path.join(repo, "data", "deriv_candidates.json")
cand = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
lp = os.path.join(repo, "data", "latest.json")
info = (json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}).get("info", {})
chart_ids = set(songs)   # the chart's own songs are never someone else's cover or fan work
vp = os.path.join(repo, "data", "deriv_views.json")
dv = (json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else {}).get("views", {})
saved, out = {}, []
for sid in ids:
    s, d, c = songs.get(sid, {}), derivs.get(sid, {}), cand.get(sid)
    if not c:
        out.append({"id": sid, "error": "no search results in data/deriv_candidates.json"})
        continue
    hide = set(d.get("hide") or [])
    keep = {k: [e for e in entries(d, k) if e.get("manual")] for k in ("cover", "ip")}
    taken = {e["vid"] for k in keep for e in keep[k]} | hide | chart_ids
    own = norm((info.get(sid) or {}).get("channel"))   # uploads by the song's own channel are official, not fan works
    names = [n for n in (norm(s.get("ko")), norm(s.get("title"))) if len(n) >= 2]
    seen, lst = set(), []
    for kind in ("cover", "ip"):
        for e in entries(d, kind):
            if not e.get("manual") and e["vid"] not in taken and e["vid"] not in seen:
                seen.add(e["vid"])
                lst.append({"vid": e["vid"], "title": e.get("title", ""), "channel": e.get("channel", ""),
                            "views": dv.get(e["vid"], e.get("v") or 0), "length": "", "now": kind, "kw": e.get("ip", "")})
    for kind in ("cover", "ip"):
        for x in c.get(kind, []):
            if x["vid"] in taken or x["vid"] in seen or (own and norm(x.get("channel")) == own):
                continue
            seen.add(x["vid"])
            lst.append(dict(x))
    for x in lst:
        x["match"] = any(n in norm(x["title"]) for n in names)
        x["hangul"] = any("\uac00" <= ch <= "\ud7a3" for ch in x["title"])
    lst.sort(key=lambda x: (not x["match"], not x["hangul"], -(x.get("views") or 0)))
    lst = lst[:50]
    saved[sid] = lst
    out.append({"id": sid, "title": s.get("title"), "ko": s.get("ko"), "artist": s.get("artist"), "vocal": s.get("vocal"),
                "keep": {k: [{"title": e.get("title"), "ip": e.get("ip")} for e in keep[k]] for k in keep},
                "candidates": [dict(i=n, title=x["title"], channel=x["channel"], views=x.get("views"), length=x.get("length"),
                                    searched_with=x.get("kw") or None, match=x["match"], hangul=x["hangul"], now=x.get("now") or None) for n, x in enumerate(lst)]})
json.dump(saved, open(os.path.join(run, "cands.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
