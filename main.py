from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json, os
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, get_fixtures_today, get_fixtures_upcoming, get_fixtures_finished, get_standings, get_team_stat, get_conn
from collector import run_sync, get_live_team_stats
from engine import predict, get_strength
from live_engine import live_predict, fetch_live_scores

app = FastAPI(title="Shield Matrix Engine", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if os.path.exists("dashboard.html"):
    @app.get("/dashboard", include_in_schema=False)
    def serve_dashboard():
        return FileResponse("dashboard.html")

@app.on_event("startup")
def startup():
    init_db()
    try:
        conn = get_conn()
        conn.execute("DELETE FROM predictions")
        conn.commit()
        conn.close()
        print("[STARTUP] Cache cleared.")
    except Exception as e:
        print(f"[STARTUP] {e}")
    try:
        run_sync()
        print("[STARTUP] Sync complete.")
    except Exception as e:
        print(f"[STARTUP] Sync failed: {e}")
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_sync, "interval", hours=3)
    scheduler.start()

def get_prediction(home, away):
    live = get_live_team_stats()
    return predict(home, away, live)

def format_match(f):
    out = {
        "match_id": f["match_id"],
        "date": f["date"],
        "time": f.get("time_utc", ""),
        "home": f["home_team"],
        "away": f["away_team"],
        "group": f.get("group_name", ""),
        "venue": f.get("venue", ""),
        "status": f["status"],
    }
    if f["status"] == "FINISHED":
        out["result"] = {"home": f["home_score"], "away": f["away_score"]}
        if f.get("ht_home") is not None:
            out["result"]["ht"] = [f["ht_home"], f["ht_away"]]
        if f.get("goals_json"):
            try: out["goals"] = json.loads(f["goals_json"])
            except: pass
    else:
        out["prediction"] = get_prediction(f["home_team"], f["away_team"])
    return out

@app.get("/")
def root():
    return {"engine": "Shield Matrix Engine", "version": "3.0", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/sync")
def manual_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_sync)
    return {"message": "Sync started."}

@app.get("/matches/today")
def matches_today():
    today = str(date.today())
    fixtures = get_fixtures_today(today)
    return {"date": today, "count": len(fixtures), "matches": [format_match(f) for f in fixtures]}

@app.get("/matches/upcoming")
def matches_upcoming(limit: int = 20):
    fixtures = get_fixtures_upcoming(str(date.today()), limit=limit)
    return {"count": len(fixtures), "matches": [format_match(f) for f in fixtures]}

@app.get("/matches/results")
def matches_results():
    fixtures = get_fixtures_finished()
    return {"total_played": len(fixtures), "results": [format_match(f) for f in fixtures]}

@app.get("/predict/{home}/{away}")
def predict_match(home: str, away: str):
    return get_prediction(home.replace("-"," "), away.replace("-"," "))

@app.get("/standings")
def standings():
    return {"standings": get_standings()}

@app.get("/team/{team_name}")
def team_profile(team_name: str):
    team = team_name.replace("-", " ")
    stats = get_team_stat(team)
    finished = [f for f in get_fixtures_finished() if f["home_team"]==team or f["away_team"]==team]
    upcoming = [f for f in get_fixtures_upcoming(str(date.today()), 100) if f["home_team"]==team or f["away_team"]==team][:3]
    form = []
    for f in finished[-5:]:
        is_home = f["home_team"] == team
        gf = f["home_score"] if is_home else f["away_score"]
        ga = f["away_score"] if is_home else f["home_score"]
        form.append({"date": f["date"], "opponent": f["away_team"] if is_home else f["home_team"], "score": f"{gf}-{ga}", "result": "W" if gf>ga else ("D" if gf==ga else "L")})
    next_matches = [{"date": f["date"], "opponent": f["away_team"] if f["home_team"]==team else f["home_team"], "prediction": get_prediction(f["home_team"], f["away_team"])} for f in upcoming]
    return {"team": team, "stats": stats, "form": form, "next_matches": next_matches}

@app.get("/live")
def live_matches():
    matches = fetch_live_scores()
    result = []
    live_stats = get_live_team_stats()
    for m in matches:
        h = get_strength(m["home"], live_stats)
        a = get_strength(m["away"], live_stats)
        hxg = (h["attack"]/1.35)*(a["defense"]/1.35)*1.35*1.08
        axg = (a["attack"]/1.35)*(h["defense"]/1.35)*1.35
        pred = live_predict(m["home"], m["away"], m["home_score"], m["away_score"], m["minute"], hxg, axg)
        result.append({**m, "prediction": pred})
    return {"live_count": len(result), "matches": result, "fetched_at": datetime.utcnow().isoformat()}

@app.get("/live/predict")
def live_predict_manual(home: str, away: str, home_score: int=0, away_score: int=0, minute: int=0):
    home = home.replace("-"," ")
    away = away.replace("-"," ")
    live_stats = get_live_team_stats()
    h = get_strength(home, live_stats)
    a = get_strength(away, live_stats)
    hxg = (h["attack"]/1.35)*(a["defense"]/1.35)*1.35*1.08
    axg = (a["attack"]/1.35)*(h["defense"]/1.35)*1.35
    return live_predict(home, away, home_score, away_score, minute, hxg, axg)
