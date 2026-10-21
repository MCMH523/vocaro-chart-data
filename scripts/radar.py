#!/usr/bin/env python3
"""신곡 레이더: find new uploads on the YouTube channels of songs already in the chart.

Runs in GitHub Actions. Reads every channel id from data/latest.json (info[id].channelId), reads each channel's
public RSS feed (no API quota), keeps videos published in the last 45 days that are not in songs.json, then asks
the YouTube Data API (videos.list, 1 unit per 50 ids) for their length and views so shorts (under 70 s), long
streams (over 15 min) and obvious non-songs (teasers, crossfades, live streams, announcements) can be dropped.
Writes data/radar.json = {"t": ms, "items": [{vid, title, channel, channelId, published, views, seconds, fromSongs}]}.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("YT_API_KEY", "").strip()
songs = json.load(open(os.path.join(ROOT, "songs.json"), encoding="utf-8"))
latest = json.load(open(os.path.join(ROOT, "data", "latest.json"), encoding="utf-8"))
known = set(songs.get("ids", []) + songs.get("pending", []) + songs.get("removed", []))
info = latest.get("info") or {}
chans = {}
for vid, v in info.items():
    c = (v or {}).get("channelId")
    if c and re.fullmatch(r"UC[\w-]{22}", c):
        chans.setdefault(c, {"name": v.get("channel", ""), "songs": []})["songs"].append(vid)
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}
SKIP = re.compile(r"(告知|ティザー|teaser|trailer|クロスフェード|xfd|crossfade|生放送|配信|live|ライブ|切り抜き|#shorts|short ver|ショート|予告|お知らせ|anniversary|メイキング|making|試聴|preview|全曲)", re.I)
cut = datetime.now(timezone.utc) - timedelta(days=45)
found = {}
for cid, c in chans.items():
    url = "https://www.youtube.com/feeds/videos.xml?" + urllib.parse.urlencode({"channel_id": cid})
    try:
        xml = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read()
        root = ET.fromstring(xml)
    except Exception as e:
        print("feed failed:", cid, e, file=sys.stderr)
        continue
    for en in root.findall("a:entry", NS):
        vid = (en.findtext("yt:videoId", "", NS) or "").strip()
        title = (en.findtext("a:title", "", NS) or "").strip()
        pub = (en.findtext("a:published", "", NS) or "").strip()
        link = en.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        if not re.fullmatch(r"[\w-]{11}", vid) or vid in known or "/shorts/" in href or SKIP.search(title):
            continue
        try:
            when = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except Exception:
            continue
        if when < cut:
            continue
        found[vid] = {"vid": vid, "title": title[:200], "channel": c["name"][:100], "channelId": cid, "published": pub[:25], "fromSongs": c["songs"][:3]}
    time.sleep(0.3)

ids = list(found)
if KEY and ids:
    def secs(iso):
        m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
        return None if not m else sum(int(x or 0) * k for x, k in zip(m.groups(), (86400, 3600, 60, 1)))
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"part": "statistics,contentDetails,snippet", "id": ",".join(ids[i:i + 50]), "key": KEY})
        try:
            data = json.load(urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30))
        except Exception as e:
            print("videos.list failed:", e, file=sys.stderr)
            continue
        for it in data.get("items", []):
            f = found.get(it["id"])
            if not f:
                continue
            f["seconds"] = secs(it.get("contentDetails", {}).get("duration"))
            f["views"] = int(it.get("statistics", {}).get("viewCount", 0) or 0)
            if it.get("snippet", {}).get("liveBroadcastContent") not in (None, "none"):
                f["seconds"] = -1
keep = [f for f in found.values() if f.get("seconds") is None or 70 <= f["seconds"] <= 900]
keep.sort(key=lambda f: f["published"], reverse=True)
out = {"t": int(time.time() * 1000), "channels": len(chans), "items": keep[:40]}
json.dump(out, open(os.path.join(ROOT, "data", "radar.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("radar: %d channels, %d new videos kept of %d" % (len(chans), len(out["items"]), len(found)))
