#!/usr/bin/env python3
"""Show the 2차창작 search results of the requested songs so the Claude task can judge them.

usage: deriv_pending.py REPO_DIR RUN_DIR IDS
  IDS : comma-separated song ids (from deriv_request.py)
Saves RUN_DIR/cands.json = {song id: {"cover": [...], "ip": [...]}} (the numbered candidates) and prints, per song:
the song, the entries a viewer added by hand ("keep", always kept), and the numbered candidates of each kind,
most viewed first. Current automatic entries are listed among the candidates (marked "now") so they can be kept.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, norm, entries

repo, run, ids = sys.argv[1], sys.argv[2], [i for i in sys.argv[3].split(",") if i]
derivs, songs = docs(os.path.join(run, "derivs")), docs(os.path.join(run, "songs"))
cp = os.path.join(repo, "data", "deriv_candidates.json")
cand = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
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
    taken = {e["vid"] for k in keep for e in keep[k]} | hide | {sid}
    names = [n for n in (norm(s.get("ko")), norm(s.get("title"))) if len(n) >= 2]
    lists = {}
    for kind in ("cover", "ip"):
        seen, lst = set(), []
        for e in entries(d, kind):
            if not e.get("manual") and e["vid"] not in taken:
                lst.append({"vid": e["vid"], "title": e.get("title", ""), "channel": e.get("channel", ""),
                            "views": dv.get(e["vid"], e.get("v") or 0), "length": "", "now": True, "kw": e.get("ip", "")})
                seen.add(e["vid"])
        for x in c.get(kind, []):
            if x["vid"] in taken or x["vid"] in seen:
                continue
            seen.add(x["vid"])
            lst.append(dict(x))
        for x in lst:
            x["match"] = any(n in norm(x["title"]) for n in names)
        lst.sort(key=lambda x: (not x["match"], -(x.get("views") or 0)))
        lists[kind] = lst[:25 if kind == "cover" else 30]
    saved[sid] = lists
    out.append({"id": sid, "title": s.get("title"), "ko": s.get("ko"), "artist": s.get("artist"), "vocal": s.get("vocal"),
                "keep": {k: [{"title": e.get("title"), "ip": e.get("ip")} for e in keep[k]] for k in keep},
                "cover": [dict(i=n, title=x["title"], channel=x["channel"], views=x.get("views"), length=x.get("length"),
                               match=x["match"], now=x.get("now", False)) for n, x in enumerate(lists["cover"])],
                "ip": [dict(i=n, title=x["title"], channel=x["channel"], views=x.get("views"), length=x.get("length"),
                            match=x["match"], searched_with=x.get("kw"), now=x.get("now", False)) for n, x in enumerate(lists["ip"])]})
json.dump(saved, open(os.path.join(run, "cands.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
