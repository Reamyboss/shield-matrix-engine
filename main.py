from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
import os
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler

from database import (
    init_db, get_fixtures_today, get_fixtures_upcoming,
    get_fixtures_finished, get_fixture_by_id, get_prediction,
    upsert_prediction, get_standings, get_team_stat,
)
from collector import run_sync, get_live_team_stats
from engine import predict

app = FastAPI(title="Shield Matrix Engine", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("dashboard.html"):
    @app.get("/dashboard", include_in_schema=False)
    def serve_dashboard():
        return FileResponse("dashboard.html")

@app.on_event("startup")
def startup():
    init_db()
    try:
        run_sync()
        print("[STARTUP] Initial data sync complete.")
    except Exception as e:
        print(f"[STARTUP] Warning: sync failed - {e}")
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_sync, "interval", hours=3, id="sync_job")
    scheduler.start()
    print("[STARTUP] Scheduler running - syncing every 3 hours.")

def build_prediction_for(fixture):
    mid = fixture["match_id"]
    cached = get_prediction(mid)
    if cached:
        top = cached["top_scorelines"]
        if isinstance(top, str):
            try:
                top = json.loads(top)
            except:
                top = []
        return {
            "home_team": fixture["home_team"],
            "away_team": fixture["away_team"],
            "xg": {"home": cached["home_xg"], "away": cached["away_xg"]},
            "probabilities": {
                "home_win": cached["home_win_pct"],
                "draw": cached["draw_pct"],
                "away_win": cached["away_win_pct"]
            },
            "markets": {
                "over_2_5": cached["over25_pct"],
                "under_2_5": cached["under25_pct"],
                "btts_yes": cached["btts_yes_pct"],
                "btts_no": cached["btts_no_pct"]
            },
            "top_scorelines": top,
            "best_bet": {
                "pick": cached["best_bet"],
                "probability": cached["best_bet_pct"],
                "confidence": cached["confidence"]
            }
        }
    live = get_live_team_stats()
    pred = predict(fixture["home_team"], fixture["away_team"], live)
    upsert_prediction({
        "match_id": mid,
        "home_team": fixture["home_team"],
        "away_team": fixture["away_team"],
        "match_date": fixture["date"],
        "home_win_pct": pred["probabilities"]["home_win"],
        "draw_pct": pred["probabilities"]["draw"],
        "away_win_pct": pred["probabilities"]["away_win"],
        "home_xg": pred["xg"]["home"],
        "away_xg": pred["xg"]["away"],
        "over25_pct": pred["markets"]["over_2_5"],
        "under25_pct": pred["markets"]["under_2_5"],
        "btts_yes_pct": pred["markets"]["btts_yes"],
        "btts_no_pct": pred["markets"]["btts_no"],
        "top_scorelines": json.dumps(pred["top_scorelines"]),
        "best_bet": pred["best_bet"]["pick"],
        "best_bet_pct": pred["best_bet"]["probability"],
        "confidence": pred["best_bet"]["confidence"],
        "created_at": datetime.utcnow().isoformat(),
    })
    return pred

def format_fixture(f, include_prediction=False):
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
            try:
                out["goals"] = json.loads(f["goals_json"])
            except:
                pass
    elif include_prediction:
        out["prediction"] = build_prediction_for(f)
    return out

@app.get("/")
def root():
    return {"engine": "Shield Matrix Engine", "version": "2.0", "status": "running"}

@app.get("/sync")
def manual_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_sync)
    return {"message": "Sync started."}

@app.get("/matches/today")
def matches_today():
    today = str(date.today())
    fixtures = get_fixtures_today(today)
    return {"date": today, "count": len(fixtures), "matches": [format_fixture(f, include_prediction=(f["status"] == "UPCOMING")) for f in fixtures]}

@app.get("/matches/upcoming")
def matches_upcoming(limit: int = 20):
    today = str(date.today())
    fixtures = get_fixtures_upcoming(today, limit=limit)
    return {"count": len(fixtures), "matches": [format_fixture(f, include_prediction=True) for f in fixtures]}

@app.get("/matches/results")
def matches_results():
    fixtures = get_fixtures_finished()
    return {"total_played": len(fixtures), "results": [format_fixture(f) for f in fixtures]}

@app.get("/predict/{home}/{away}")
def predict_match(home: str, away: str):
    home = home.replace("-", " ").replace("_", " ")
    away = away.replace("-", " ").replace("_", " ")
    live = get_live_team_stats()
    return predict(home, away, live)

@app.get("/standings")
def standings():
    return {"standings": get_standings()}

@app.get("/team/{team_name}")
def team_profile(team_name: str):
    team = team_name.replace("-", " ").replace("_", " ")
    stats = get_team_stat(team)
    finished = get_fixtures_finished()
    upcoming_all = get_fixtures_upcoming(str(date.today()), limit=100)
    played = [f for f in finished if f["home_team"] == team or f["away_team"] == team]
    upcoming = [f for f in upcoming_all if f["home_team"] == team or f["away_team"] == team][:3]
    form = []
    for f in played[-5:]:
        gh, ga = f["home_score"], f["away_score"]
        is_home = f["home_team"] == team
        gf = gh if is_home else ga
        gc = ga if is_home else gh
        result = "W" if gf > gc else ("D" if gf == gc else "L")
        opp = f["away_team"] if is_home else f["home_team"]
        form.append({"date": f["date"], "opponent": opp, "score": f"{gf}-{gc}", "result": result})
    live = get_live_team_stats()
    next_matches = []
    for f in upcoming:
        pred = predict(f["home_team"], f["away_team"], live)
        opp = f["away_team"] if f["home_team"] == team else f["home_team"]
        next_matches.append({"date": f["date"], "opponent": opp, "prediction": pred})
    return {"team": team, "stats": stats, "form": form, "next_matches": next_matches}

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
