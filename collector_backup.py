import requests
import json
from datetime import datetime, date
from database import init_db, upsert_fixture, rebuild_team_stats, get_conn

DATA_URL = "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"
BACKUP_URL = "https://cdn.jsdelivr.net/gh/openfootball/world-cup.json@master/2026/worldcup.json"

def fetch_raw():
    for url in [DATA_URL, BACKUP_URL]:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[COLLECTOR] Warning: {url} failed - {e}")
    raise RuntimeError("Both data sources unreachable.")

def make_match_id(match):
    d = match["date"].replace("-", "")
    h = match["team1"].replace(" ", "").replace("&", "")[:6].upper()
    a = match["team2"].replace(" ", "").replace("&", "")[:6].upper()
    return f"{d}-{h}-{a}"

def parse_and_store(raw):
    matches = raw.get("matches", [])
    finished = 0
    upcoming = 0
    for m in matches:
        has_result = "score" in m and m["score"].get("ft") is not None
        if has_result:
            status = "FINISHED"
            home_score = m["score"]["ft"][0]
            away_score = m["score"]["ft"][1]
            ht_home = m["score"].get("ht", [None, None])[0]
            ht_away = m["score"].get("ht", [None, None])[1]
            goals_json = json.dumps({"home": m.get("goals1", []), "away": m.get("goals2", [])})
            finished += 1
        else:
            status = "UPCOMING"
            home_score = away_score = ht_home = ht_away = None
            goals_json = None
            upcoming += 1
        fixture = {
            "match_id": make_match_id(m),
            "date": m["date"],
            "time_utc": m.get("time", ""),
            "home_team": m["team1"],
            "away_team": m["team2"],
            "group_name": m.get("group", ""),
            "venue": m.get("ground", ""),
            "round": m.get("round", ""),
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
            "ht_home": ht_home,
            "ht_away": ht_away,
            "goals_json": goals_json,
            "updated_at": datetime.utcnow().isoformat(),
        }
        upsert_fixture(fixture)
    rebuild_team_stats()
    summary = {"total": len(matches), "finished": finished, "upcoming": upcoming, "synced_at": datetime.utcnow().isoformat()}
    print(f"[COLLECTOR] Sync complete - {finished} results, {upcoming} upcoming.")
    return summary

def run_sync():
    print(f"[COLLECTOR] Starting sync at {datetime.utcnow().isoformat()}")
    raw = fetch_raw()
    return parse_and_store(raw)

def get_live_team_stats():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM team_stats").fetchall()
    conn.close()
    return {r["team_name"]: dict(r) for r in rows}

if __name__ == "__main__":
    init_db()
    result = run_sync()
    print(json.dumps(result, indent=2))
