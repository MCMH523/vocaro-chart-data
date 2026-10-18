#!/usr/bin/env python3
"""Print ArtifactData batch writes that record upload times for newly activated songs.

usage: pub_writes.py LATEST_JSON ID1,ID2,...
Each write creates pub/<id> = {"published": ISO time}. Ids without an upload time in LATEST_JSON are skipped.
"""
import json, re, sys
latest = json.load(open(sys.argv[1], encoding="utf-8"))
pub = latest.get("published") or {}
ids = [i for i in sys.argv[2].split(",") if re.fullmatch(r"[\w-]{11}", i)]
writes = [{"op": "set", "collection": "pub", "doc_id": i, "data": {"published": pub[i]}}
          for i in ids if isinstance(pub.get(i), str) and re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+Z", pub[i])]
print(json.dumps(writes, ensure_ascii=False))
