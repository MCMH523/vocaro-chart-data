#!/usr/bin/env python3
"""Collect YouTube search results that may be a song's instrumental or Korean-language version.

Runs in GitHub Actions (the runner can open youtube.com; no API quota is used). For every id in songs.json that
has no entry in data/alt_candidates.json yet (or every id with --all), it searches YouTube for
"<title> off vocal", "<title> instrumental" and "<title> 한국어", and keeps the first results of each search
(video id, title, channel, views, length). It only gathers candidates: the hourly Claude task decides which
one, if any, really is the Inst / Korean version, and stores that in the page's database.
usage: alt_candidates.py [--all] [--max N]
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "alt_candidates.json")
songs = json.load(open(os.path.join(ROOT, "songs.json"), encoding="utf-8"))
latest = json.load(open(os.path.join(ROOT, "data", "latest.json"), encoding="utf-8"))
info = latest.get("info") or {}
have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
TITLES = os.path.join(ROOT, "data", "song_titles.json")  # clean original titles, when known (id -> title)
titles = json.load(open(TITLES, encoding="utf-8")) if os.path.exists(TITLES) else {}
ids = [i for i in dict.fromkeys(songs.get("ids", []) + songs.get("pending", [])) if re.fullmatch(r"[\w-]{11}", i or "")]
args = sys.argv[1:]
redo = "--all" in args
limit = int(args[args.index("--max") + 1]) if "--max" in args else 60

def norm(x):
    return re.sub(r"[\s'\"‘’“”・*_.]", "", (x or "").lower())

def core(title, channel=""):
    """The song name from a YouTube title: drop bracketed tags, feat./singer credits and the producer part."""
    t = re.sub(r"[【\[（(][^】\]）)]*[】\]）)]", " ", title)
    t = re.sub(r"[‘’'\"「」『』]", " ", t)
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+|\s*/\s*|\s*／\s*|\s*//\s*", t) if p.strip()]
    ch = norm(channel)
    keep = [p for p in parts if not (ch and (norm(p) == ch or norm(p) in ch or ch in norm(p)))] or parts
    t = keep[0] if keep else title
    t = re.split(r"\s+(?:feat\.?|ft\.|w/)\s*", t, flags=re.I)[0]
    t = re.sub(r"\b(MV|M/V|Music Video|Official|Original Song|full)\b", " ", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -–—|｜:：") or title

def search(q):
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "hl": "ko", "gl": "KR"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                                               "Accept-Language": "ko-KR,ko;q=0.9,ja;q=0.8,en;q=0.7"})
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});</script>", html, re.S)
    if not m:
        return []
    data, out = json.loads(m.group(1)), []
    def walk(o):
        if isinstance(o, dict):
            v = o.get("videoRenderer")
            if isinstance(v, dict) and v.get("videoId"):
                txt = lambda k: "".join(r.get("text", "") for r in (v.get(k) or {}).get("runs", [])) or (v.get(k) or {}).get("simpleText", "")
                out.append({"vid": v["videoId"], "title": txt("title")[:200], "channel": txt("ownerText")[:80],
                            "views": txt("viewCountText")[:40], "length": txt("lengthText")[:12]})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(data)
    return out[:8]

todo = [i for i in ids if redo or i not in have][:limit]
for vid in todo:
    t = titles.get(vid) or core((info.get(vid) or {}).get("title", ""), (info.get(vid) or {}).get("channel", ""))
    if not t:
        continue
    entry = {"q": t, "t": int(time.time()), "inst": [], "ko": []}
    for kind, q in (("inst", t + " off vocal"), ("inst", t + " instrumental"), ("ko", t + " 한국어")):
        try:
            seen = {c["vid"] for c in entry[kind]}
            entry[kind] += [c for c in search(q) if c["vid"] not in seen and c["vid"] != vid]
        except Exception as e:
            print("search failed:", vid, q, e, file=sys.stderr)
        time.sleep(1.2)
    have[vid] = entry
    print(vid, t, len(entry["inst"]), len(entry["ko"]))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("candidates for %d songs (%d new)" % (len(have), len(todo)))
