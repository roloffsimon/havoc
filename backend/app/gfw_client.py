"""
Global Fishing Watch — Events API v3 client.

The Events API is the project's primary data source. AIS-transponder
signals, classified by a machine-learning model into "fishing" vs.
"transit", arrive as discrete events with a start time, an end time,
a position, and a vessel identity. The event *is* the signature of
industrial fishing as seen from orbit; its duration approximates the
apparent fishing hours consumed at that position.

GFW publishes events with a ~72 hour delay, so the scheduler queries
the day that ended 3 days ago.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
DEFAULT_LIMIT = 10_000


def _token() -> str:
    tok = os.environ.get("GFW_TOKEN", "").strip()
    if not tok:
        raise RuntimeError(
            "GFW_TOKEN is not set. Get one at https://globalfishingwatch.org/our-apis/"
        )
    return tok


def last_available_window() -> tuple[str, str]:
    """One full day, ending ~3 days ago, matches GFW's publication lag."""
    end = (datetime.now(timezone.utc) - timedelta(days=3)).date()
    start = end - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def parse_entries(raw_entries: Iterable[dict]) -> list[dict]:
    """
    Normalise raw GFW entries into event dicts.

    The Events API has no explicit `totalFishingHours` field, so we
    compute duration from (end - start). Since an event is, by
    construction, a detected fishing period, its duration is a valid
    approximation of apparent fishing hours for our purposes.
    """
    events: list[dict] = []
    for entry in raw_entries:
        pos = entry.get("position") or {}
        lat, lon = pos.get("lat"), pos.get("lon")
        if lat is None or lon is None:
            continue

        # Prefer explicit fields if a future API version adds them.
        fishing = entry.get("fishing") or {}
        hours = None
        if isinstance(fishing, dict):
            hours = fishing.get("totalFishingHours") or fishing.get("apparentFishingHours")
        if hours is None:
            hours = entry.get("fishing_hours")
        if hours is None:
            s, e = entry.get("start", ""), entry.get("end", "")
            if s and e:
                try:
                    ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    te = datetime.fromisoformat(e.replace("Z", "+00:00"))
                    hours = (te - ts).total_seconds() / 3600.0
                except (ValueError, TypeError):
                    pass
        if hours is None or hours <= 0:
            hours = 1.0  # Every event catches at least one stanza.

        vessel = entry.get("vessel") or {}
        if isinstance(vessel, dict):
            vname = vessel.get("name") or "UNKNOWN"
            flag = vessel.get("flag", "??")
            vid = vessel.get("id", "")
        else:
            vname = entry.get("vessel_name") or "UNKNOWN"
            flag = entry.get("flag", "??")
            vid = entry.get("vessel_id", "")

        events.append({
            "vessel_name": vname,
            "vessel_id": vid,
            "flag": flag,
            "lat": lat,
            "lon": lon,
            "fishing_hours": round(float(hours), 2),
            "start": entry.get("start", ""),
            "end": entry.get("end", ""),
        })
    return events


def fetch_events(start_date: str, end_date: str, page_size: int = DEFAULT_LIMIT) -> list[dict]:
    """Pull one window of events from the Events API v3, paginating until done."""
    headers = {"Authorization": f"Bearer {_token()}"}
    all_entries: list[dict] = []
    offset = 0
    total: int | None = None
    while True:
        params = {
            "datasets[0]": "public-global-fishing-events:latest",
            "start-date": start_date,
            "end-date": end_date,
            "limit": page_size,
            "offset": offset,
        }
        log.info("GFW fetch: %s → %s (offset=%d, limit=%d)", start_date, end_date, offset, page_size)
        r = requests.get(f"{BASE_URL}/events", headers=headers, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()
        entries = data.get("entries", [])
        if total is None:
            total = data.get("total", len(entries))
        all_entries.extend(entries)
        if len(entries) < page_size or len(all_entries) >= total:
            break
        offset += page_size
    log.info("GFW fetch complete: %d entries (total reported %s)", len(all_entries), total)
    return parse_entries(all_entries)


def load_events_from_file(path: str) -> list[dict]:
    """Fallback: load a previously saved GFW dump."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        raw = data.get("entries", data.get("events", []))
    elif isinstance(data, list):
        raw = data
    else:
        raise ValueError(f"Unexpected JSON structure in {path}: {type(data)}")
    return parse_entries(raw)
