import math, sqlite3, asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db
from collector import run_all_collectors

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(run_all_collectors())
    yield

app = FastAPI(title="Shield Matrix", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def poisson_prob(lam, k):
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)

def run_poisson(home_avg, away_avg):
    home_win = draw = away_win = 0.0
    for hg in range(8):
        for ag in range(8):
            p = poisson_prob(home_avg, hg) * poisson_prob(away_avg, ag)
            if hg > ag: home_win += p
            elif hg == ag: draw += p
            else: away_win += p
    total = home_win + draw + away_win
    return {"home_win": round((home_win/total)*100,1), "draw": round((draw/total)*100,1), "away_win": round((away_win/total)*100,1)}

@app.get("/")
async def root():
    db = get_db()
    teams = db.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    matches = db.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    players = db.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    db.close()
    return {"status": "Shield Matrix is live", "version": "3.0", "teams": teams, "matches": matches, "players": players}

@app.get("/matches")
async def get_matches(sport: str = None, league: str = None, limit: int = Query(default=50, le=200)):
    db = get_db()
    query = "SELECT * FROM matches WHERE 1=1"
    params = []
    if sport: query += " AND sport=?"; params.append(sport)
    if league: query += " AND league=?"; params.append(league)
    query += " ORDER BY match_date DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(query, params).fetchall()
    db.close()
    return {"matches": [dict(r) for r in rows], "total": len(rows)}

@app.get("/teams")
async def get_teams(sport: str = None):
    db = get_db()
    query = "SELECT * FROM teams WHERE 1=1"
    params = []
    if sport: query += " AND sport=?"; params.append(sport)
    rows = db.execute(query, params).fetchall()
    db.close()
    return {"teams": [dict(r) for r in rows], "total": len(rows)}

@app.get("/predict")
async def predict(home: str, away: str):
    db = get_db()
    def team_avg(name):
        r1 = db.execute("SELECT AVG(home_score) as avg FROM matches WHERE home_team LIKE ? AND home_score IS NOT NULL", (f"%{name}%",)).fetchone()
        r2 = db.execute("SELECT AVG(away_score) as avg FROM matches WHERE away_team LIKE ? AND away_score IS NOT NULL", (f"%{name}%",)).fetchone()
        combined = ((r1["avg"] or 0) + (r2["avg"] or 0)) / 2
        return combined if combined > 0 else 1.3
    home_avg = team_avg(home)
    away_avg = team_avg(away)
    db.close()
    pred = run_poisson(home_avg, away_avg)
    confidence = round(max(pred["home_win"], pred["draw"], pred["away_win"]), 1)
    gap = abs(pred["home_win"] - pred["away_win"])
    risk = "LOW" if gap > 30 else "MEDIUM" if gap > 15 else "HIGH"
    if pred["home_win"] > 50: tip = f"{home} to Win"
    elif pred["away_win"] > 50: tip = f"{away} to Win"
    elif pred["draw"] > 30: tip = "Draw likely"
    else: tip = "Too close to call"
    return {"match": f"{home} vs {away}", "home_win": f"{pred['home_win']}%", "draw": f"{pred['draw']}%", "away_win": f"{pred['away_win']}%", "risk": risk, "confidence": f"{confidence}%", "tip": tip, "model": "Poisson v3.0 — Shield Matrix"}

@app.get("/standings")
async def get_standings(league: str):
    db = get_db()
    rows = db.execute("SELECT * FROM standings WHERE league LIKE ? ORDER BY position ASC", (f"%{league}%",)).fetchall()
    db.close()
    return {"standings": [dict(r) for r in rows], "league": league}

@app.post("/admin/collect")
async def trigger_collection():
    asyncio.create_task(run_all_collectors())
    return {"status": "Collection started"}