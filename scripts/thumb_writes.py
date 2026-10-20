#!/usr/bin/env python3
"""Prepare ArtifactData batch writes for cover thumbnails the page's database does not have yet.

usage: thumb_writes.py REPO_DIR HAVE_DIR WANT_IDS_JSON OUT_DIR
  HAVE_DIR       directory of the "thumbs" collection as saved by ArtifactData list out_dir (<id>.json per thumbnail)
  WANT_IDS_JSON  JSON array of song ids that should have a thumbnail (active and newly activated songs)
  OUT_DIR        where the documents are written, one <id>.json = {"src": "data:image/jpeg;base64,..."}
Prints a JSON array of at most 40 "set" writes (file_path form, new documents), ready for one ArtifactData batch.
"""
import base64, io, json, os, re, sys
from PIL import Image

repo, have_dir, want_file, out = sys.argv[1:5]
have = set()
for root, _, files in os.walk(have_dir) if os.path.isdir(have_dir) else []:
    have.update(f[:-5] for f in files if f.endswith(".json"))
want = [i for i in json.load(open(want_file)) if isinstance(i, str) and re.fullmatch(r"[\w-]{11}", i)]
os.makedirs(out, exist_ok=True)
writes = []
for vid in want:
    if vid in have or len(writes) >= 40:
        continue
    p = os.path.join(repo, "data", "thumbs", vid + ".jpg")
    if not os.path.exists(p):
        continue
    raw = open(p, "rb").read()
    im = Image.open(io.BytesIO(raw)); im.load()
    if im.format != "JPEG" or im.size != (120, 120):
        continue
    doc = os.path.abspath(os.path.join(out, vid + ".json"))
    json.dump({"src": "data:image/jpeg;base64," + base64.b64encode(raw).decode()}, open(doc, "w"))
    writes.append({"op": "set", "collection": "thumbs", "doc_id": vid, "file_path": doc})
print(json.dumps(writes))
