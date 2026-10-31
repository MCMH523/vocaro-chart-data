#!/usr/bin/env python3
"""Search YouTube for each requested song's Korean covers and Korean-IP fan works (2차창작).

Runs in GitHub Actions when deriv/req.json is pushed (the runner can open youtube.com; no API quota is used).
deriv/req.json = {"t": epoch seconds, "songs": [{"id", "title", "ko", "artist"}]}, written by the page's
"2차창작 검색" Claude task for the songs a viewer asked about. For every song it runs:
  - covers: "<ko> 한국어 커버" and "<title> 한국어" sorted by view count, "<title> 한국어 커버" by relevance;
  - fan works: "<ko> <ip>" and "<title> <ip>" for each Korean IP keyword below, by relevance;
and keeps every video result (id, title, channel, view count, length, query). It only gathers candidates; the
Claude task decides which ones really are a Korean cover / a Korean-IP fan work of that very song.
Results go to data/deriv_candidates.json as {song id: {"req": t, "at": epoch, "cover": [...], "ip": [...]}}.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ = os.path.join(ROOT, "deriv", "req.json")
OUT = os.path.join(ROOT, "data", "deriv_candidates.json")
# Korean IPs whose fan works are common on YouTube (search keyword, name shown on the page).
IPS = [("블루아카이브", "블루 아카이브"), ("트릭컬", "트릭컬"), ("니케", "승리의 여신: 니케"), ("메이플", "메이플스토리"),
       ("쿠키런", "쿠키런"), ("림버스", "림버스 컴퍼니")]
SORT_VIEWS = "CAMSAhAB"   # search filter: videos only, sorted by view count

def search(q, views=False):
    p = {"search_query": q, "hl": "ko", "gl": "KR"}
    if views:
        p["sp"] = SORT_VIEWS
    req = urllib.request.Request("https://www.youtube.com/results?" + urllib.parse.urlencode(p),
                                 headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                                          "Accept-Language": "ko-KR,ko;q=0.9,ja;q=0.8,en;q=0.7"})
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});</script>", html, re.S)
    if not m:
        return []
    out = []
    def walk(o):
        if isinstance(o, dict):
            v = o.get("videoRenderer")
            if isinstance(v, dict) and v.get("videoId"):
                txt = lambda k: "".join(r.get("text", "") for r in (v.get(k) or {}).get("runs", [])) or (v.get(k) or {}).get("simpleText", "")
                vt = txt("viewCountText")
                digits = re.sub(r"[^\d]", "", vt)
                out.append({"vid": v["videoId"], "title": txt("title")[:200], "channel": txt("ownerText")[:80],
                            "views": int(digits) if digits else 0, "length": txt("lengthText")[:12], "q": q})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(json.loads(m.group(1)))
    return out[:12]

req = json.load(open(REQ, encoding="utf-8"))
have = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
for s in req.get("songs", [])[:12]:
    sid = s.get("id", "")
    if not re.fullmatch(r"[\w-]{11}", sid):
        continue
    title, ko = (s.get("title") or "").strip(), (s.get("ko") or "").strip()
    names = [n for n in dict.fromkeys([ko, title]) if n]
    if not names:
        continue
    jobs = [("cover", names[0] + " 한국어 커버", True), ("cover", names[-1] + " 한국어", True), ("cover", names[-1] + " 한국어 커버", False)]
    for kw, ipname in IPS:
        for n in names:
            jobs.append(("ip:" + ipname, n + " " + kw, False))
    entry = {"req": req.get("t"), "at": int(time.time()), "cover": [], "ip": [], "errors": 0}
    seen = {sid}
    for kind, q, by_views in jobs:
        try:
            for c in search(q, by_views):
                if c["vid"] in seen:
                    continue
                seen.add(c["vid"])
                if kind.startswith("ip:"):
                    c["kw"] = kind[3:]
                    entry["ip"].append(c)
                else:
                    entry["cover"].append(c)
        except Exception as e:
            entry["errors"] += 1
            print("search failed:", sid, q, e, file=sys.stderr)
        time.sleep(1.3)
    have[sid] = entry
    print(sid, names, len(entry["cover"]), len(entry["ip"]), "errors", entry["errors"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(have, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
