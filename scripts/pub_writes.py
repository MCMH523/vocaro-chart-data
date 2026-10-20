#!/usr/bin/env python3
"""Print ArtifactData batch writes that record upload times for newly activated songs.

usage: pub_writes.py LATEST_JSON ID1,ID2,...
Each write creates pub/<id> = {"published": ISO time, "duration": seconds (when known)}. Ids without an upload time in
LATEST_JSON are skipped.
"""
import json, re, sys
latest = json.load(open(sys.argv[1], encoding="utf-8"))
pub = latest.get("published") or {}
dur = latest.get("duration") or {}
ids = [i for i in sys.argv[2].split(",") if re.fullmatch(r"[\w-]{11}", i)]
def doc(i):
    d = {"published": pub[i]}
    if isinstance(dur.get(i), int) and 0 < dur[i] < 86400:
        d["duration"] = dur[i]
    return d
writes = [{"op": "set", "collection": "pub", "doc_id": i, "data": doc(i)}
          for i in ids if isinstance(pub.get(i), str) and re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+Z", pub[i])]
print(json.dumps(writes, ensure_ascii=False))
