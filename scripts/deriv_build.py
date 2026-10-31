#!/usr/bin/env python3
"""Build the derivs/<song id> documents from the Claude task's picks and print one ArtifactData batch.

usage: deriv_build.py RUN_DIR PICKS_JSON VERSIONS_JSON T_MS
  PICKS_JSON    : {song id: {"cover": [i, ...], "ip": [[i, "IP name"], ...], "note": "짧은 한국어 메모"}}
                  (i = candidate numbers printed by deriv_pending.py; [] when nothing fits)
  VERSIONS_JSON : {song id: version} of the existing derivs documents (omit songs that have none)
Each list keeps the hand-added entries first, then the picks, at most 5 per kind. Writes RUN_DIR/out/<id>.json and
prints a JSON array of "set" writes (file_path form, if_version where the document exists).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, entries

run, picks_p, ver_p, t_ms = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
picks = json.load(open(picks_p, encoding="utf-8"))
vers = json.load(open(ver_p, encoding="utf-8")) if os.path.exists(ver_p) else {}
cands = json.load(open(os.path.join(run, "cands.json"), encoding="utf-8"))
derivs = docs(os.path.join(run, "derivs"))
os.makedirs(os.path.join(run, "out"), exist_ok=True)
writes = []
for sid, p in picks.items():
    if sid not in cands:
        continue
    d = derivs.get(sid, {})
    doc = {"hide": [h for h in (d.get("hide") or []) if isinstance(h, str)][:200], "searchedAt": t_ms, "at": t_ms,
           "searchNote": str(p.get("note") or "")[:120]}
    for kind in ("cover", "ip"):
        lst = [e for e in entries(d, kind) if e.get("manual")]
        have = {e["vid"] for e in lst}
        for item in p.get(kind) or []:
            i, ipname = (item[0], item[1]) if isinstance(item, list) else (item, "")
            if not isinstance(i, int) or not (0 <= i < len(cands[sid][kind])):
                continue
            c = cands[sid][kind][i]
            if c["vid"] in have:
                continue
            have.add(c["vid"])
            e = {"vid": c["vid"], "title": c.get("title", "")[:200], "channel": c.get("channel", "")[:80], "v": int(c.get("views") or 0)}
            if kind == "ip":
                e["ip"] = str(ipname or c.get("kw") or "")[:40]
            lst.append(e)
        doc[kind] = lst[:5]
    path = os.path.abspath(os.path.join(run, "out", sid + ".json"))
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    w = {"op": "set", "collection": "derivs", "doc_id": sid, "file_path": path}
    if sid in vers:
        w["if_version"] = int(vers[sid])
    writes.append(w)
print(json.dumps(writes, ensure_ascii=False))
