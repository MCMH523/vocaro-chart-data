#!/usr/bin/env python3
"""IP sweep: add the Claude task's picks to each song's 2차창작 list and mark the songs done for this IP.

usage: deriv_ipbuild.py RUN_DIR PICKS_JSON VERSIONS_JSON T_MS IP_NAME IDS
  PICKS_JSON    : {song id: [i, ...]} (numbers from deriv_ippending.py; songs without picks may be left out)
  VERSIONS_JSON : {song id: version} of the existing derivs documents among IDS
  IDS           : every song id of this batch (all of them are marked done: ipSwept[IP_NAME] = T_MS)
The song's IP list keeps hand-added entries first, then every other entry and the new picks by views (no limit).
Writes RUN_DIR/ipout/<id>.json and prints a JSON array of "set" writes (file_path form, if_version where it exists).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deriv_lib import docs, entries

run, picks_p, ver_p, t_ms, ipname, ids = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], [i for i in sys.argv[6].split(",") if i]
picks = json.load(open(picks_p, encoding="utf-8")) if os.path.exists(picks_p) else {}
vers = json.load(open(ver_p, encoding="utf-8")) if os.path.exists(ver_p) else {}
cands = json.load(open(os.path.join(run, "ipcands.json"), encoding="utf-8"))
derivs = docs(os.path.join(run, "derivs"))
os.makedirs(os.path.join(run, "ipout"), exist_ok=True)
writes, added = [], 0
for sid in ids:
    d = derivs.get(sid)
    doc = dict(d) if d else {"cover": [], "ip": [], "hide": []}
    hide = set(doc.get("hide") or [])
    covers = {e["vid"] for e in entries(doc, "cover")}
    cur = entries(doc, "ip")
    have = {e["vid"] for e in cur}
    new = []
    for i in picks.get(sid) or []:
        lst = cands.get(sid) or []
        if not isinstance(i, int) or not (0 <= i < len(lst)):
            continue
        c = lst[i]
        if c["vid"] in have or c["vid"] in hide or c["vid"] in covers:
            continue
        have.add(c["vid"])
        new.append({"vid": c["vid"], "title": c.get("title", "")[:200], "channel": c.get("channel", "")[:80],
                    "v": int(c.get("views") or 0), "ip": ipname[:40], "sweep": ipname[:40]})
    manual = [e for e in cur if e.get("manual")]
    rest = sorted([e for e in cur if not e.get("manual")] + new, key=lambda e: -(e.get("v") or 0))
    doc["ip"] = (manual + rest)[:60]
    added += len([e for e in new if e in doc["ip"]])
    sw = dict(doc.get("ipSwept") or {})
    sw[ipname] = t_ms
    doc["ipSwept"] = sw
    doc["at"] = t_ms
    path = os.path.abspath(os.path.join(run, "ipout", sid + ".json"))
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    w = {"op": "set", "collection": "derivs", "doc_id": sid, "file_path": path}
    if d is not None:
        if sid not in vers:
            sys.exit("missing version for existing derivs document " + sid)
        w["if_version"] = int(vers[sid])
    writes.append(w)
print(json.dumps(writes, ensure_ascii=False))
print("links added: %d" % added, file=sys.stderr)
