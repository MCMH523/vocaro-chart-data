# vocaro-chart-data

Hourly YouTube view counts for the songs on the "보카로 차트" page.

- `songs.json` — the video ids to track (kept in sync by the chart's hourly Claude task).
- `.github/workflows/views.yml` — runs every hour, calls the YouTube Data API (`videos.list`, 50 ids per call,
  1 quota unit each) with the `YT_API_KEY` repository secret, and commits `data/latest.json`.
- `scripts/build_snapshot.py` — used by the Claude task to turn `data/latest.json` into the page's snapshot,
  with the same sanity checks as before (a count may not fall, or jump by more than 50% + 3M in an hour).
