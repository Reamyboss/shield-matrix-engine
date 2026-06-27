"""
collector.py — Shield Matrix Data Collector
Pulls REAL WC2026 fixture and result data.
Source: openfootball/world-cup.json (free, no API key, updates live during tournament)
No fake data. No simulated streams. Only real results.
"""

import requests
import json
from datetime import datetime, date

from database import (
    init_db, upsert_fixture, rebuild_team_stats, get_conn
)

# Primary data source — free, open, updates during WC2026
DATA_URL = "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"

# Backup source (same data, different CDN)
BACKUP_URL = "https://cdn.jsdelivr.net/gh/openfootball/world-cup.json@master/2026/worldcup.json"


def fetch_raw() -> dict:
    """Fetch raw WC2026 JSON. Try primary, fall back to backup."""
    for url in [DATA_URL, BACKUP_URL]:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[COLLECTOR] Warning: {url} failed — {e}")
    raise RuntimeError("Both data sources unreachable.")


def make_match_id(match: dict) -> str:
    """Stable unique ID for each fixture.
    FIX: Removed [:6] slice — full team names prevent ID collisions
    e.g. 'Costa Rica' vs 'Colombia' on the same date no longer risk clashing.
    """
    d = match["date"].replace("-", "")
    h = match["team1"].replace(" ", "").replace("&", "").upper()
    a = match["team2"].replace(" ", "").replace("&", "").upper()
    return f"{d}-{h}-{a}"


def parse_and_store(raw: dict) -> dict:
    """
    Parse raw JSON, upsert every fixture into DB, rebuild team stats.
    Returns summary counts.
    """
    matches = raw.get("matches", [])
    stored = 0
    finished = 0
    upcoming = 0

    for m in matches:
        # FIX 1: Safely extract ft score — guard against empty list, nulls, or missing key
        ft = m.get("score", {}).get("ft")
        has_result = isinstance(ft, list) and len(ft) == 2 and all(v is not None for v in ft)

        if has_result:
            status = "FINISHED"
            home_score = ft[0]
            away_score = ft[1]
            # FIX 2: Guard against ht being present but empty or malformed
            ht = m.get("score", {}).get("ht") or [None, None]
            ht_home = ht[0] if len(ht) > 0 else None
            ht_away = ht[1] if len(ht) > 1 else None
            goals_json = json.dumps({
                "home": m.get("goals1", []),
                "away": m.get("goals2", []),
            })
            finished += 1
        else:
            status = "UPCOMING"
            home_score = None
            away_score = None
            ht_home = None
            ht_away = None
            goals_json = None
            upcoming += 1

        fixture = {
            "match_id":   make_match_id(m),
            "date":       m["date"],
            "time_utc":   m.get("time", ""),
            "home_team":  m["team1"],
            "away_team":  m["team2"],
            "group_name": m.get("group", ""),
            "venue":      m.get("ground", ""),
            "round":      m.get("round", ""),
            "status":     status,
            "home_score": home_score,
            "away_score": away_score,
            "ht_home":    ht_home,
            "ht_away":    ht_away,
            "goals_json": goals_json,
            "updated_at": datetime.utcnow().isoformat(),
        }

        upsert_fixture(fixture)
        stored += 1

    # Rebuild team stats from all finished matches
    rebuild_team_stats()

    summary = {
        "total":    stored,
        "finished": finished,
        "upcoming": upcoming,
        "synced_at": datetime.utcnow().isoformat(),
    }
    print(f"[COLLECTOR] Sync complete — {finished} results, {upcoming} upcoming.")
    return summary


def run_sync() -> dict:
    """Full sync: fetch → parse → store → rebuild stats.
    FIX: Wrapped in try/except so a network failure logs cleanly instead of crashing.
    """
    print(f"[COLLECTOR] Starting sync at {datetime.utcnow().isoformat()}")
    try:
        raw = fetch_raw()
        return parse_and_store(raw)
    except RuntimeError as e:
        print(f"[COLLECTOR] Sync failed — {e}")
        return {"error": str(e)}


def get_live_team_stats() -> dict:
    """Return all team stats as a dict keyed by team name (for engine blending).
    FIX: Use context manager so connection is always closed, even if query throws.
    """
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM team_stats").fetchall()
    return {r["team_name"]: dict(r) for r in rows}


if __name__ == "__main__":
    init_db()
    result = run_sync()
    print(json.dumps(result, indent=2))
