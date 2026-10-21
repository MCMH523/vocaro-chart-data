#!/usr/bin/env python3
"""Compare data/radar.json with the page's radar/latest document and write the new document if it changed.

usage: radar_doc.py REPO_DIR OLD_DOC_JSON_OR_- NEW_OUT_JSON
Prints "changed" (and writes NEW_OUT_JSON) or "same" / "none" (no radar file yet).
"""
import json, os, sys
repo, old_path, out_path = sys.argv[1:4]
p = os.path.join(repo, "data", "radar.json")
if not os.path.exists(p):
    print("none"); sys.exit(0)
new = json.load(open(p, encoding="utf-8"))
items = [{k: it.get(k) for k in ("vid", "title", "channel", "published", "views", "seconds", "fromSongs")} for it in new.get("items", [])][:40]
old = None
if old_path != "-" and os.path.exists(old_path):
    try:
        old = json.load(open(old_path, encoding="utf-8"))
    except Exception:
        old = None
def key(lst):
    return [i.get("vid") for i in (lst or [])]
if old and key(old.get("items")) == key(items):
    print("same"); sys.exit(0)
json.dump({"items": items, "scannedAt": new.get("t"), "channels": new.get("channels")}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
print("changed")
