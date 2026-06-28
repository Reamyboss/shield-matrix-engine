from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, os
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, get_fixtures_today, get_fixtures_upcoming, get_fixtures_finished, get_standings, get_team_stat, get_conn
from collector import run_sync, get_live_team_stats
from engine import predict, get_strength
from live_engine import live_predict, fetch_live_scores

# FIX 7: Single version constant — used everywhere so they never drift apart
VERSION = "3.1"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
# FIX 8: No hardcoded default — warn loudly if unset so it's never silently open in production
if not ADMIN_PASSWORD:
    print("[WARNING] ADMIN_PASSWORD env var not set — admin endpoints are unprotected!")


# FIX 4 & 5: Replace deprecated @app.on_event("startup") with lifespan context manager
# This also gives us a clean place to shut the scheduler down on exit
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    init_db()
    try:
        _create_all_tables()
        print("[STARTUP] All tables ready.")
    except Exception as e:
        print(f"[STARTUP] Table error: {e}")
        
        # Run initial sync in background so it never blocks startup
    scheduler.add_job(run_sync, "date")  # runs once immediately in background
    scheduler.add_job(run_sync, "interval", hours=3)

    yield  # app is running

    # ── SHUTDOWN ──
    # FIX 5: Cleanly stop scheduler so no zombie threads on Railway restart
    scheduler.shutdown(wait=False)
    print("[SHUTDOWN] Scheduler stopped.")


app = FastAPI(
    title=f"Shield Matrix Engine v{VERSION}",
    version=VERSION,
    description="WC2026 AI Prediction Engine - Professional Dashboard",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── AUTH ─────────────────────────────────────────────────────────
def verify_admin(x_admin_key: str = Header(None)):
    if not ADMIN_PASSWORD or x_admin_key != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ── PAGES ────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_root():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    return {"engine": "Shield Matrix Engine", "version": VERSION, "status": "running"}

@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    return {"error": "Dashboard not found"}

@app.get("/admin", include_in_schema=False)
def serve_admin():
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    return {"error": "Admin not found"}


# ── STARTUP HELPERS ──────────────────────────────────────────────
def _create_all_tables():
    # FIX 1: Context manager — connection always closes even if CREATE TABLE throws
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, text TEXT, rating INTEGER, date TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot TEXT, code TEXT, active INTEGER DEFAULT 1,
            created_at TEXT)""")
        conn.commit()


# ── HELPERS ──────────────────────────────────────────────────────
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
            # FIX 6: Specific exception types — bare except hides system errors
            try:
                out["goals"] = json.loads(f["goals_json"])
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        out["prediction"] = get_prediction(f["home_team"], f["away_team"])
    return out


# ── CORE API ─────────────────────────────────────────────────────
@app.get("/health")
def health():
    # FIX 7: Version pulled from single VERSION constant
    return {"status": "ok", "version": VERSION, "time": datetime.utcnow().isoformat()}

@app.get("/sync")
def manual_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_sync)
    return {"message": "Sync started in background."}

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
    return get_prediction(home.replace("-", " "), away.replace("-", " "))

@app.get("/standings")
def standings():
    return {"standings": get_standings()}

@app.get("/team/{team_name}")
def team_profile(team_name: str):
    team = team_name.replace("-", " ")
    stats = get_team_stat(team)
    finished = [f for f in get_fixtures_finished() if f["home_team"] == team or f["away_team"] == team]
    upcoming = [f for f in get_fixtures_upcoming(str(date.today()), 100) if f["home_team"] == team or f["away_team"] == team][:3]
    form = []
    for f in finished[-5:]:
        is_home = f["home_team"] == team
        gf = f["home_score"] if is_home else f["away_score"]
        ga = f["away_score"] if is_home else f["home_score"]
        form.append({
            "date": f["date"],
            "opponent": f["away_team"] if is_home else f["home_team"],
            "score": f"{gf}-{ga}",
            "result": "W" if gf > ga else ("D" if gf == ga else "L"),
        })
    next_matches = [
        {
            "date": f["date"],
            "opponent": f["away_team"] if f["home_team"] == team else f["home_team"],
            "prediction": get_prediction(f["home_team"], f["away_team"]),
        }
        for f in upcoming
    ]
    return {"team": team, "stats": stats, "form": form, "next_matches": next_matches}


# ── LIVE ─────────────────────────────────────────────────────────
@app.get("/live")
def live_matches():
    matches = fetch_live_scores()
    result = []
    live_stats = get_live_team_stats()
    for m in matches:
        h = get_strength(m["home"], live_stats)
        a = get_strength(m["away"], live_stats)
        hxg = (h["attack"] / 1.288) * (a["defense"] / 1.288) * 1.288 * 1.08
        axg = (a["attack"] / 1.288) * (h["defense"] / 1.288) * 1.288
        pred = live_predict(m["home"], m["away"], m["home_score"], m["away_score"], m["minute"], hxg, axg)
        result.append({**m, "prediction": pred})
    return {"live_count": len(result), "matches": result, "fetched_at": datetime.utcnow().isoformat()}

@app.get("/live/predict")
def live_predict_manual(home: str, away: str, home_score: int = 0, away_score: int = 0, minute: int = 0):
    home = home.replace("-", " ")
    away = away.replace("-", " ")
    live_stats = get_live_team_stats()
    h = get_strength(home, live_stats)
    a = get_strength(away, live_stats)
    hxg = (h["attack"] / 1.288) * (a["defense"] / 1.288) * 1.288 * 1.08
    axg = (a["attack"] / 1.288) * (h["defense"] / 1.288) * 1.288
    return live_predict(home, away, home_score, away_score, minute, hxg, axg)


# ── REVIEWS ──────────────────────────────────────────────────────
class ReviewIn(BaseModel):
    name: str = "Anonymous"
    text: str
    rating: int

@app.post("/reviews")
def post_review(review: ReviewIn):
    if not 1 <= review.rating <= 5:
        raise HTTPException(400, "Rating must be 1-5")
    if not review.text.strip():
        raise HTTPException(400, "Review text required")
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reviews (name,text,rating,date) VALUES (?,?,?,?)",
            (review.name[:50], review.text[:500], review.rating, datetime.utcnow().strftime("%b %d, %Y"))
        )
        conn.commit()
    return {"message": "Review submitted!"}

@app.get("/reviews")
def get_reviews():
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,name,text,rating,date FROM reviews ORDER BY id DESC"
        ).fetchall()
    return {"reviews": [dict(r) for r in rows], "total": len(rows)}

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int, auth: bool = Depends(verify_admin)):
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        conn.commit()
    return {"message": "Deleted."}


# ── ADS ──────────────────────────────────────────────────────────
class AdIn(BaseModel):
    slot: str
    code: str

@app.post("/ads", dependencies=[Depends(verify_admin)])
def create_ad(ad: AdIn):
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ads (slot,code,active,created_at) VALUES (?,?,1,?)",
            (ad.slot[:50], ad.code[:5000], datetime.utcnow().isoformat())
        )
        conn.commit()
    return {"message": "Ad saved."}

@app.get("/ads", dependencies=[Depends(verify_admin)])
def get_ads():
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM ads ORDER BY id DESC").fetchall()
    return {"ads": [dict(r) for r in rows]}

@app.get("/ads/active")
def get_active_ads():
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM ads WHERE active=1").fetchall()
    return {"ads": [dict(r) for r in rows]}

@app.post("/ads/{ad_id}/toggle", dependencies=[Depends(verify_admin)])
def toggle_ad(ad_id: int):
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        conn.execute(
            "UPDATE ads SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?",
            (ad_id,)
        )
        conn.commit()
    return {"message": "Toggled."}

@app.delete("/ads/{ad_id}", dependencies=[Depends(verify_admin)])
def delete_ad(ad_id: int):
    # FIX 2: Context manager — connection always closes
    with get_conn() as conn:
        conn.execute("DELETE FROM ads WHERE id=?", (ad_id,))
        conn.commit()
    return {"message": "Deleted."}


# ── ADMIN STATS ──────────────────────────────────────────────────
@app.get("/admin/stats", dependencies=[Depends(verify_admin)])
def admin_stats():
    # FIX 3: Context manager — connection always closes across all 7 queries
    with get_conn() as conn:
        total_fixtures = conn.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
        finished       = conn.execute("SELECT COUNT(*) FROM fixtures WHERE status='FINISHED'").fetchone()[0]
        upcoming       = conn.execute("SELECT COUNT(*) FROM fixtures WHERE status='UPCOMING'").fetchone()[0]
        total_reviews  = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        avg_rating     = conn.execute("SELECT AVG(rating) FROM reviews").fetchone()[0]
        total_ads      = conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
        active_ads     = conn.execute("SELECT COUNT(*) FROM ads WHERE active=1").fetchone()[0]
    return {
        "fixtures": {"total": total_fixtures, "finished": finished, "upcoming": upcoming},
        "reviews": {"total": total_reviews, "avg_rating": round(avg_rating or 0, 2)},
        "ads": {"total": total_ads, "active": active_ads},
        "server_time": datetime.utcnow().isoformat(),
    }
