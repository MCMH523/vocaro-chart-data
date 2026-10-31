"""Shared helpers for the 2차창작 scripts run by the page's Claude tasks."""
import json, os, re

def docs(d):
    """A collection saved by ArtifactData list/query out_dir: {doc id: data}, files searched recursively."""
    out = {}
    if not d or d == "-" or not os.path.isdir(d):
        return out
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".json"):
                try:
                    x = json.load(open(os.path.join(root, f), encoding="utf-8"))
                except Exception:
                    continue
                out[f[:-5]] = x.get("data", x) if isinstance(x, dict) and isinstance(x.get("data"), dict) and "id" in x else x
    return out

def norm(x):
    return re.sub(r"[\s'\"‘’“”・·*_.,!！?？~～\-–—:：()（）\[\]【】「」『』/／|｜]", "", (x or "").lower())

def vid_ok(v):
    return isinstance(v, str) and re.fullmatch(r"[\w-]{11}", v) is not None

def entries(doc, kind):
    return [e for e in (doc.get(kind) or []) if isinstance(e, dict) and vid_ok(e.get("vid"))]
