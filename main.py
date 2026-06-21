"""
main.py — Shield Matrix Engine v2
FastAPI backend. Deploy on Railway.
All routes tested, no fake data.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler

from database import (
    init_db,
    get_fixtures_today,
    get_fixtures_upcoming,
    get_fixtures_finished,
    get_fixture_by_id,
    get_prediction,
    upsert_prediction,
    get_standings,
    get_team_stat,
)
from collector import run_sync, get_live_team_stats
from engine import predict

# ── APP SETUP ───────────────────────────────────────────────────────────────

app = FastAPI(title="Shield Matrix Engine", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve dashboard.html as static file
if os.path.exists("dashboard.html"):
    @app.get("/dashboard", include_in_schema=False)
    def serve_dashboard():
        return FileResponse("dashboard.html")

# ── STARTUP ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    # Sync data on boot
    try:
        run_sync()
        print("[STARTUP] Initial data sync complete.")
    except Exception as e:
        print(f"[STARTUP] Warning: sync failed — {e}")

    # Schedule auto-refresh every 3 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_sync, "interval", hours=3, id="sync_job")
    scheduler.start()
    print("[STARTUP] Scheduler running — syncing every 3 hours.")


# ── HELPERS ──────────────────────────────────────────────────────────────────

def build_prediction_for(fixture: dict) -> dict:
    """Get cached prediction or generate a new one."""
    mid = fixture["match_id"]
    cached = get_prediction(mid)
    if cached:
        return json.loads(cached["top_scorelines"]) if isinstance(cached.get("top_scorelines"), str) else cached

    # Generate fresh
    live = get_live_team_stats()
    pred = predict(fixture["home_team"], fixture["away_team"], live)

    # Cache to DB
    upsert_prediction({
        "match_id":      mid,
        "home_team":     fixture["home_team"],
        "away_team":     fixture["away_team"],
        "match_date":    fixture["date"],
        "home_win_pct":  pred["probabilities"]["home_win"],
        "draw_pct":      pred["probabilities"]["draw"],
        "away_win_pct":  pred["probabilities"]["away_win"],
        "home_xg":       pred["xg"]["home"],
        "away_xg":       pred["xg"]["away"],
        "over25_pct":    pred["markets"]["over_2_5"],
        "under25_pct":   pred["markets"]["under_2_5"],
        "btts_yes_pct":  pred["markets"]["btts_yes"],
        "btts_no_pct":   pred["markets"]["btts_no"],
        "top_scorelines": json.dumps(pred["top_scorelines"]),
        "best_bet":      pred["best_bet"]["pick"],
        "best_bet_pct":  pred["best_bet"]["probability"],
        "confidence":    pred["best_bet"]["confidence"],
        "created_at":    datetime.utcnow().isoformat(),
    })
    return pred


def format_fixture(f: dict, include_prediction: bool = False) -> dict:
    out = {
        "match_id":  f["match_id"],
        "date":      f["date"],
        "time":      f.get("time_utc", ""),
        "home":      f["home_team"],
        "away":      f["away_team"],
        "group":     f.get("group_name", ""),
        "venue":     f.get("venue", ""),
        "status":    f["status"],
    }
    if f["status"] == "FINISHED":
        out["result"] = {
            "home": f["home_score"],
            "away": f["away_score"],
        }
        if f.get("ht_home") is not None:
            out["result"]["ht"] = [f["ht_home"], f["ht_away"]]
        if f.get("goals_json"):
            try:
                out["goals"] = json.loads(f["goals_json"])
            except Exception:
                pass
    elif include_prediction:
        out["prediction"] = build_prediction_for(f)
    return out


# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "engine": "Shield Matrix Engine",
        "version": "2.0",
        "status": "running",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/sync")
def manual_sync(background_tasks: BackgroundTasks):
    """Manually trigger a data sync."""
    background_tasks.add_task(run_sync)
    return {"message": "Sync started in background."}


@app.get("/matches/today")
def matches_today():
    today = str(date.today())
    fixtures = get_fixtures_today(today)
    result = []
    for f in fixtures:
        out = format_fixture(f, include_prediction=(f["status"] == "UPCOMING"))
        result.append(out)
    return {
        "date": today,
        "count": len(result),
        "matches": result,
    }


@app.get("/matches/upcoming")
def matches_upcoming(limit: int = 20):
    today = str(date.today())
    fixtures = get_fixtures_upcoming(today, limit=limit)
    result = [format_fixture(f, include_prediction=True) for f in fixtures]
    return {"count": len(result), "matches": result}


@app.get("/matches/results")
def matches_results():
    fixtures = get_fixtures_finished()
    result = [format_fixture(f) for f in fixtures]
    return {"total_played": len(result), "results": result}


@app.get("/match/{match_id}")
def match_detail(match_id: str):
    f = get_fixture_by_id(match_id)
    if not f:
        raise HTTPException(404, "Match not found")
    out = format_fixture(f, include_prediction=(f["status"] == "UPCOMING"))
    return out


@app.get("/predict/{home}/{away}")
def predict_match(home: str, away: str):
    home = home.replace("-", " ").replace("_", " ")
    away = away.replace("-", " ").replace("_", " ")
    live = get_live_team_stats()
    return predict(home, away, live)


@app.get("/standings")
def standings():
    data = get_standings()
    return {"standings": data}


@app.get("/team/{team_name}")
def team_profile(team_name: str):
    team = team_name.replace("-", " ").replace("_", " ")
    stats = get_team_stat(team)

    # Get their fixtures
    finished = get_fixtures_finished()
    upcoming_all = get_fixtures_upcoming(str(date.today()), limit=100)

    played = [
        f for f in finished
        if f["home_team"] == team or f["away_team"] == team
    ]
    upcoming = [
        f for f in upcoming_all
        if f["home_team"] == team or f["away_team"] == team
    ][:3]

    form = []
    for f in played[-5:]:
        gh, ga = f["home_score"], f["away_score"]
        is_home = f["home_team"] == team
        gf = gh if is_home else ga
        gc = ga if is_home else gh
        result = "W" if gf > gc else ("D" if gf == gc else "L")
        opp = f["away_team"] if is_home else f["home_team"]
        form.append({
            "date":     f["date"],
            "opponent": opp,
            "score":    f"{gf}–{gc}",
            "result":   result,
        })

    live = get_live_team_stats()
    next_matches = []
    for f in upcoming:
        pred = predict(f["home_team"], f["away_team"], live)
        opp = f["away_team"] if f["home_team"] == team else f["home_team"]
        next_matches.append({
            "date":       f["date"],
            "opponent":   opp,
            "home_away":  "Home" if f["home_team"] == team else "Away",
            "prediction": pred,
        })

    return {
        "team":         team,
        "stats":        stats,
        "form":         form,
        "next_matches": next_matches,
    }


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ── LIVE IN-PLAY ROUTES ──────────────────────────────────────────────────────

from live_engine import live_predict, fetch_live_scores
from engine import get_strength

@app.get("/live")
def live_matches():
    """Auto-fetch all live WC2026 matches with in-play predictions."""
    matches = fetch_live_scores()
    result = []
    live_stats = get_live_team_stats()
    for m in matches:
        h = get_strength(m["home"], live_stats)
        a = get_strength(m["away"], live_stats)
        home_xg = (h["attack"] / 1.35) * (a["defense"] / 1.35) * 1.35 * 1.08
        away_xg = (a["attack"] / 1.35) * (h["defense"] / 1.35) * 1.35
        pred = live_predict(
            m["home"], m["away"],
            m["home_score"], m["away_score"],
            m["minute"], home_xg, away_xg
        )
        result.append({**m, "prediction": pred})
    return {"live_count": len(result), "matches": result, "fetched_at": datetime.utcnow().isoformat()}


@app.get("/live/predict")
def live_predict_manual(
    home: str, away: str,
    home_score: int = 0, away_score: int = 0, minute: int = 0
):
    """Manual in-play prediction — user provides current score and minute."""
    home = home.replace("-", " ").replace("_", " ")
    away = away.replace("-", " ").replace("_", " ")
    live_stats = get_live_team_stats()
    h = get_strength(home, live_stats)
    a = get_strength(away, live_stats)
    home_xg = (h["attack"] / 1.35) * (a["defense"] / 1.35) * 1.35 * 1.08
    away_xg = (a["attack"] / 1.35) * (h["defense"] / 1.35) * 1.35
    return live_predict(home, away, home_score, away_score, minute, home_xg, away_xg)

