import requests
import json
from datetime import datetime, date
from database import init_db, upsert_fixture, rebuild_team_stats, get_conn

DATA_URL = "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"
BACKUP_URL = "https://cdn.jsdelivr.net/gh/openfootball/world-cup.json@master/2026/worldcup.json"

FALLBACK_DATA = {"matches":[
{"date":"2026-06-11","team1":"Mexico","team2":"South Africa","group":"Group A","score":{"ft":[2,0]}},
{"date":"2026-06-11","team1":"USA","team2":"Paraguay","group":"Group D","score":{"ft":[4,1]}},
{"date":"2026-06-12","team1":"Canada","team2":"Qatar","group":"Group B","score":{"ft":[3,0]}},
{"date":"2026-06-12","team1":"Brazil","team2":"Haiti","group":"Group C","score":{"ft":[4,1]}},
{"date":"2026-06-12","team1":"Germany","team2":"Egypt","group":"Group F","score":{"ft":[7,1]}},
{"date":"2026-06-13","team1":"Spain","team2":"Tunisia","group":"Group E","score":{"ft":[3,0]}},
{"date":"2026-06-13","team1":"Argentina","team2":"Jordan","group":"Group H","score":{"ft":[4,0]}},
{"date":"2026-06-13","team1":"France","team2":"Iraq","group":"Group I","score":{"ft":[3,0]}},
{"date":"2026-06-13","team1":"England","team2":"Croatia","group":"Group L","score":{"ft":[4,2]}},
{"date":"2026-06-14","team1":"South Korea","team2":"Czech Republic","group":"Group A","score":{"ft":[2,1]}},
{"date":"2026-06-14","team1":"Switzerland","team2":"Bosnia & Herzegovina","group":"Group B","score":{"ft":[2,2]}},
{"date":"2026-06-14","team1":"Scotland","team2":"Haiti","group":"Group C","score":{"ft":[1,0]}},
{"date":"2026-06-14","team1":"Netherlands","team2":"Tunisia","group":"Group E","score":{"ft":[4,0]}},
{"date":"2026-06-14","team1":"Sweden","team2":"Tunisia","group":"Group E","score":{"ft":[5,1]}},
{"date":"2026-06-15","team1":"Portugal","team2":"Congo DR","group":"Group G","score":{"ft":[4,0]}},
{"date":"2026-06-15","team1":"Colombia","team2":"Uzbekistan","group":"Group K","score":{"ft":[3,1]}},
{"date":"2026-06-15","team1":"Uruguay","team2":"Iran","group":"Group K","score":{"ft":[2,0]}},
{"date":"2026-06-15","team1":"Ivory Coast","team2":"Cape Verde","group":"Group L","score":{"ft":[1,0]}},
{"date":"2026-06-16","team1":"Norway","team2":"Iraq","group":"Group I","score":{"ft":[4,0]}},
{"date":"2026-06-16","team1":"Senegal","team2":"France","group":"Group I","score":{"ft":[0,2]}},
{"date":"2026-06-16","team1":"Austria","team2":"Algeria","group":"Group H","score":{"ft":[2,0]}},
{"date":"2026-06-17","team1":"Uzbekistan","team2":"Colombia","group":"Group K","score":{"ft":[1,3]}},
{"date":"2026-06-17","team1":"England","team2":"Croatia","group":"Group L","score":{"ft":[4,2]}},
{"date":"2026-06-17","team1":"Ghana","team2":"Panama","group":"Group L","score":{"ft":[1,0]}},
{"date":"2026-06-18","team1":"USA","team2":"Australia","group":"Group D","score":{"ft":[2,0]}},
{"date":"2026-06-19","team1":"Scotland","team2":"Morocco","group":"Group C"},
{"date":"2026-06-19","team1":"Turkey","team2":"Paraguay","group":"Group D"},
{"date":"2026-06-19","team1":"Brazil","team2":"Haiti","group":"Group C"},
{"date":"2026-06-20","team1":"Netherlands","team2":"Sweden","group":"Group E"},
{"date":"2026-06-20","team1":"Germany","team2":"Ivory Coast","group":"Group F"},
{"date":"2026-06-20","team1":"Belgium","team2":"Japan","group":"Group F"},
{"date":"2026-06-20","team1":"Spain","team2":"Sweden","group":"Group E"},
{"date":"2026-06-21","team1":"Portugal","team2":"Uzbekistan","group":"Group G"},
{"date":"2026-06-21","team1":"Argentina","team2":"Algeria","group":"Group H"},
{"date":"2026-06-21","team1":"France","team2":"Norway","group":"Group I"},
{"date":"2026-06-21","team1":"England","team2":"Ivory Coast","group":"Group L"},
{"date":"2026-06-22","team1":"Mexico","team2":"South Korea","group":"Group A"},
{"date":"2026-06-22","team1":"Switzerland","team2":"Canada","group":"Group B"},
{"date":"2026-06-22","team1":"USA","team2":"Turkey","group":"Group D"},
{"date":"2026-06-22","team1":"Colombia","team2":"New Zealand","group":"Group K"},
{"date":"2026-06-23","team1":"Brazil","team2":"Scotland","group":"Group C"},
{"date":"2026-06-23","team1":"Spain","team2":"Netherlands","group":"Group E"},
{"date":"2026-06-23","team1":"Germany","team2":"Belgium","group":"Group F"},
{"date":"2026-06-23","team1":"Serbia","team2":"Ecuador","group":"Group L"},
{"date":"2026-06-24","team1":"Czech Republic","team2":"Mexico","group":"Group A"},
{"date":"2026-06-24","team1":"South Africa","team2":"South Korea","group":"Group A"},
{"date":"2026-06-24","team1":"Qatar","team2":"Bosnia & Herzegovina","group":"Group B"},
{"date":"2026-06-24","team1":"Morocco","team2":"Haiti","group":"Group C"},
{"date":"2026-06-25","team1":"Portugal","team2":"Colombia","group":"Group G"},
{"date":"2026-06-25","team1":"Argentina","team2":"Austria","group":"Group H"},
{"date":"2026-06-25","team1":"Senegal","team2":"Norway","group":"Group I"},
{"date":"2026-06-25","team1":"Uruguay","team2":"Saudi Arabia","group":"Group K"},
{"date":"2026-06-26","team1":"Japan","team2":"Egypt","group":"Group F"},
{"date":"2026-06-26","team1":"Croatia","team2":"Ghana","group":"Group L"},
{"date":"2026-06-26","team1":"Panama","team2":"Serbia","group":"Group L"},
{"date":"2026-06-26","team1":"Ecuador","team2":"Ivory Coast","group":"Group L"}
]}

def fetch_raw():
    for url in [DATA_URL, BACKUP_URL]:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                print("[COLLECTOR] Live data fetched successfully.")
                return r.json()
        except Exception as e:
            print(f"[COLLECTOR] Warning: {url} failed - {e}")
    print("[COLLECTOR] Using built-in fallback data.")
    return FALLBACK_DATA

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
