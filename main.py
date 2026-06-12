import math
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db
from collector import run_all_collectors
from scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await run_all_collectors()
    start_scheduler()
    yield


app = FastAPI(
    title="Shield Matrix Engine",
    description="Pre-match sports prediction engine — Poisson v3. World Cup 2026 ready.",
    version="3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# TEAM STRENGTH — football goals per game (attack rating)
# Source: 8+ years of international + club match data
# ─────────────────────────────────────────────────────────────
TEAM_STRENGTH = {
    # Elite international
    "Brazil":          {"att": 2.3, "def": 0.8},
    "Argentina":       {"att": 2.2, "def": 0.9},
    "France":          {"att": 2.1, "def": 0.7},
    "Spain":           {"att": 2.0, "def": 0.8},
    "Germany":         {"att": 2.0, "def": 1.0},
    "England":         {"att": 1.9, "def": 0.9},
    "Portugal":        {"att": 2.1, "def": 1.0},
    "Netherlands":     {"att": 1.9, "def": 1.0},
    "Belgium":         {"att": 1.8, "def": 1.0},
    "Croatia":         {"att": 1.6, "def": 0.9},
    "Uruguay":         {"att": 1.7, "def": 1.0},
    "Colombia":        {"att": 1.7, "def": 1.1},
    "Mexico":          {"att": 1.6, "def": 1.1},
    "USA":             {"att": 1.5, "def": 1.1},
    "Canada":          {"att": 1.4, "def": 1.1},
    "Italy":           {"att": 1.7, "def": 0.9},
    "Switzerland":     {"att": 1.5, "def": 1.0},
    "Denmark":         {"att": 1.6, "def": 0.9},
    "Japan":           {"att": 1.5, "def": 1.0},
    "South Korea":     {"att": 1.4, "def": 1.1},
    "Morocco":         {"att": 1.4, "def": 0.9},
    "Senegal":         {"att": 1.5, "def": 1.0},
    "Australia":       {"att": 1.4, "def": 1.2},
    "Ecuador":         {"att": 1.5, "def": 1.2},
    "Serbia":          {"att": 1.6, "def": 1.1},
    "Poland":          {"att": 1.4, "def": 1.2},
    "Ukraine":         {"att": 1.5, "def": 1.2},
    "Turkey":          {"att": 1.5, "def": 1.2},
    "Austria":         {"att": 1.5, "def": 1.1},
    "Norway":          {"att": 1.6, "def": 1.1},
    "Sweden":          {"att": 1.5, "def": 1.1},
    "Iran":            {"att": 1.3, "def": 1.1},
    "Saudi Arabia":    {"att": 1.3, "def": 1.2},
    "Ghana":           {"att": 1.3, "def": 1.2},
    "Ivory Coast":     {"att": 1.5, "def": 1.1},
    "Cameroon":        {"att": 1.3, "def": 1.3},
    "Egypt":           {"att": 1.3, "def": 1.0},
    "Algeria":         {"att": 1.3, "def": 1.1},
    "Mali":            {"att": 1.2, "def": 1.2},
    "DR Congo":        {"att": 1.2, "def": 1.2},
    "Tunisia":         {"att": 1.2, "def": 1.1},
    "South Africa":    {"att": 1.2, "def": 1.2},
    "Nigeria":         {"att": 1.5, "def": 1.2},
    "Paraguay":        {"att": 1.3, "def": 1.2},
    "Chile":           {"att": 1.5, "def": 1.1},
    "Peru":            {"att": 1.3, "def": 1.2},
    "Venezuela":       {"att": 1.2, "def": 1.3},
    "Scotland":        {"att": 1.4, "def": 1.2},
    "Wales":           {"att": 1.3, "def": 1.2},
    "Czech Republic":  {"att": 1.4, "def": 1.1},
    "Czechia":         {"att": 1.4, "def": 1.1},
    "Slovakia":        {"att": 1.3, "def": 1.2},
    "Albania":         {"att": 1.2, "def": 1.2},
    "Hungary":         {"att": 1.3, "def": 1.2},
    "Slovenia":        {"att": 1.2, "def": 1.1},
    "Romania":         {"att": 1.3, "def": 1.2},
    "Greece":          {"att": 1.2, "def": 1.1},
    "Qatar":           {"att": 1.1, "def": 1.4},
    "Uzbekistan":      {"att": 1.2, "def": 1.2},
    "Iraq":            {"att": 1.2, "def": 1.3},
    "Jordan":          {"att": 1.1, "def": 1.3},
    "Panama":          {"att": 1.1, "def": 1.3},
    "Costa Rica":      {"att": 1.2, "def": 1.2},
    "Honduras":        {"att": 1.1, "def": 1.4},
    "Jamaica":         {"att": 1.1, "def": 1.4},
    "Guatemala":       {"att": 1.0, "def": 1.4},
    "Cuba":            {"att": 0.9, "def": 1.5},
    "Haiti":           {"att": 1.0, "def": 1.4},
    "New Zealand":     {"att": 1.1, "def": 1.3},
    "Cape Verde":      {"att": 1.1, "def": 1.2},
    "Benin":           {"att": 1.0, "def": 1.2},
    "Curacao":         {"att": 1.0, "def": 1.4},
    "Bosnia and Herzegovina": {"att": 1.3, "def": 1.2},
    # Club football
    "Arsenal":              {"att": 2.2, "def": 1.0},
    "Chelsea":              {"att": 1.9, "def": 1.1},
    "Liverpool":            {"att": 2.3, "def": 1.0},
    "Manchester City":      {"att": 2.5, "def": 0.9},
    "Manchester United":    {"att": 1.7, "def": 1.2},
    "Tottenham Hotspur":    {"att": 1.8, "def": 1.3},
    "Newcastle United":     {"att": 1.7, "def": 1.1},
    "Aston Villa":          {"att": 1.8, "def": 1.1},
    "West Ham United":      {"att": 1.5, "def": 1.3},
    "Brighton":             {"att": 1.6, "def": 1.1},
    "Real Madrid":          {"att": 2.4, "def": 0.9},
    "Barcelona":            {"att": 2.3, "def": 1.0},
    "Atletico Madrid":      {"att": 1.8, "def": 0.9},
    "Bayern Munich":        {"att": 2.6, "def": 0.9},
    "Borussia Dortmund":    {"att": 2.0, "def": 1.2},
    "Bayer Leverkusen":     {"att": 2.1, "def": 0.9},
    "Inter Milan":          {"att": 2.0, "def": 0.9},
    "AC Milan":             {"att": 1.8, "def": 1.0},
    "Juventus":             {"att": 1.7, "def": 1.0},
    "Paris Saint-Germain":  {"att": 2.4, "def": 1.0},
}


# ─────────────────────────────────────────────────────────────
# WORLD CUP 2026 — Official Groups
# ─────────────────────────────────────────────────────────────
WC2026_GROUPS = {
    "A": {"teams": ["Mexico",      "South Africa", "South Korea",           "Czechia"],               "host": "Mexico"},
    "B": {"teams": ["Canada",      "Switzerland",  "Qatar",                 "Bosnia and Herzegovina"], "host": "Canada"},
    "C": {"teams": ["Brazil",      "Morocco",      "Haiti",                 "Scotland"],              "host": None},
    "D": {"teams": ["USA",         "Paraguay",     "Australia",             "Turkey"],                "host": "USA"},
    "E": {"teams": ["Germany",     "Curacao",      "Ivory Coast",           "Ecuador"],               "host": None},
    "F": {"teams": ["Netherlands", "Japan",        "Sweden",                "Tunisia"],               "host": None},
    "G": {"teams": ["Belgium",     "Egypt",        "Iran",                  "New Zealand"],           "host": None},
    "H": {"teams": ["Spain",       "Cape Verde",   "Saudi Arabia",          "Uruguay"],               "host": None},
    "I": {"teams": ["France",      "Senegal",      "Norway",                "Iraq"],                  "host": None, "label": "Group of Death"},
    "J": {"teams": ["Argentina",   "Algeria",      "Austria",               "Jordan"],                "host": None},
    "K": {"teams": ["Portugal",    "DR Congo",     "Uzbekistan",            "Colombia"],              "host": None},
    "L": {"teams": ["England",     "Croatia",      "Ghana",                 "Panama"],                "host": None},
}

TEAM_TO_GROUP = {
    team: letter
    for letter, info in WC2026_GROUPS.items()
    for team in info["teams"]
}


# ─────────────────────────────────────────────────────────────
# POISSON MODEL — Football only, clean inputs
# ─────────────────────────────────────────────────────────────
def poisson_prob(lam: float, k: int) -> float:
    lam = max(0.1, lam)
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def run_poisson(home_avg: float, away_avg: float, max_goals: int = 8) -> dict:
    home_win = draw = away_win = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson_prob(home_avg, i) * poisson_prob(away_avg, j)
            if i > j:    home_win += p
            elif i == j: draw     += p
            else:        away_win += p
    total = home_win + draw + away_win
    return {
        "home_win": round((home_win / total) * 100, 1),
        "draw":     round((draw     / total) * 100, 1),
        "away_win": round((away_win / total) * 100, 1),
    }


def get_team_avg(db, team: str, is_home: bool, league: str) -> float:
    """
    Returns average goals scored per game for a team.
    - Football sport filter: prevents basketball/NFL scores polluting the model
    - Score cap <= 12: catches any freak outliers
    - Excludes 0-0 draws (placeholder fixtures)
    - Always returns attack average (goals scored), never defence
    - Falls back to TEAM_STRENGTH seed if DB history is thin
    """
    col   = "home_score" if is_home else "away_score"
    t_col = "home_team"  if is_home else "away_team"

    # League-specific football history
    rows = db.execute(
        f"SELECT {col} FROM matches "
        f"WHERE {t_col}=? AND league=? AND sport='football' "
        f"AND status='FT' AND {col} IS NOT NULL "
        f"AND {col} <= 12 "
        f"AND NOT (home_score=0 AND away_score=0) "
        f"ORDER BY match_date DESC LIMIT 20",
        (team, league)
    ).fetchall()

    # Broaden to all football if thin
    if len(rows) < 3:
        rows = db.execute(
            f"SELECT {col} FROM matches "
            f"WHERE {t_col}=? AND sport='football' "
            f"AND status='FT' AND {col} IS NOT NULL "
            f"AND {col} <= 12 "
            f"AND NOT (home_score=0 AND away_score=0) "
            f"ORDER BY match_date DESC LIMIT 20",
            (team,)
        ).fetchall()

    if len(rows) >= 3:
        avg = sum(r[0] for r in rows) / len(rows)
        if 0.3 <= avg <= 5.0:   # sane football range
            return round(avg, 2)

    # Seed fallback — always attack rating
    strength = TEAM_STRENGTH.get(team)
    if strength:
        return strength["att"]

    return 1.3  # universal fallback


def build_prediction(home: str, away: str, league: str, db) -> dict:
    home_avg = get_team_avg(db, home, True,  league)
    away_avg = get_team_avg(db, away, False, league)

    # Apply home advantage (+10% home, -10% away)
    home_lam = round(max(0.5, min(home_avg * 1.10, 4.5)), 2)
    away_lam = round(max(0.5, min(away_avg * 0.90, 4.5)), 2)

    pred = run_poisson(home_lam, away_lam)
    hw, dw, aw = pred["home_win"], pred["draw"], pred["away_win"]

    best = max(hw, dw, aw)
    if hw == best:   tip, tip_code = f"{home} to Win", "1"
    elif aw == best: tip, tip_code = f"{away} to Win", "2"
    else:            tip, tip_code = "Draw", "X"

    gap = abs(hw - aw)
    risk = "LOW" if gap > 25 else "MEDIUM" if gap > 12 else "HIGH"

    total_lam   = home_lam + away_lam
    over25_pct  = round(min(92, max(15, (total_lam / 3.2) * 100)), 1)
    under25_pct = round(100 - over25_pct, 1)
    btts_pct    = round(min(88, max(12,
        (1 - math.exp(-home_lam)) * (1 - math.exp(-away_lam)) * 100
    )), 1)

    return {
        "home_win":       hw,
        "draw":           dw,
        "away_win":       aw,
        "tip":            tip,
        "tip_code":       tip_code,
        "risk":           risk,
        "confidence":     f"{best}%",
        "home_avg_goals": home_lam,
        "away_avg_goals": away_lam,
        "over_2_5":       f"{over25_pct}%",
        "under_2_5":      f"{under25_pct}%",
        "btts":           f"{btts_pct}%",
        "model":          "Poisson v3.0",
    }


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name":        "Shield Matrix Engine",
        "version":     "3.0",
        "description": "Pre-match sports prediction API — Poisson v3",
        "world_cup":   "FIFA World Cup 2026 — active",
        "docs":        "/docs",
    }


@app.get("/api/health")
def health():
    db      = get_db()
    total   = db.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    teams   = db.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    wc26    = db.execute("SELECT COUNT(*) FROM matches WHERE league='World Cup 2026'").fetchone()[0]
    football_ft = db.execute(
        "SELECT COUNT(*) FROM matches WHERE sport='football' AND status='FT' "
        "AND NOT (home_score=0 AND away_score=0)"
    ).fetchone()[0]
    db.close()
    return {
        "status":               "healthy",
        "total_matches":        total,
        "total_teams":          teams,
        "wc2026_fixtures":      wc26,
        "football_ft_matches":  football_ft,
        "model":                "Poisson v3.0",
    }


@app.get("/api/leagues")
def get_leagues():
    db   = get_db()
    rows = db.execute(
        "SELECT DISTINCT league, sport, COUNT(*) as cnt "
        "FROM matches GROUP BY league, sport ORDER BY cnt DESC"
    ).fetchall()
    db.close()
    return {"leagues": [{"league": r[0], "sport": r[1], "matches": r[2]} for r in rows]}


@app.get("/api/matches")
def get_matches(
    league: str = Query(None),
    status: str = Query(None),
    sport:  str = Query(None),
    limit:  int = Query(50),
):
    db     = get_db()
    q      = "SELECT * FROM matches WHERE 1=1"
    params = []
    if league: q += " AND league=?"; params.append(league)
    if status: q += " AND status=?"; params.append(status)
    if sport:  q += " AND sport=?";  params.append(sport)
    q += " ORDER BY match_date DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(q, params).fetchall()
    db.close()
    return {"matches": [dict(r) for r in rows], "count": len(rows)}


@app.get("/api/predict")
def predict(
    home:   str = Query(...),
    away:   str = Query(...),
    league: str = Query("Premier League"),
):
    db   = get_db()
    pred = build_prediction(home, away, league, db)
    db.close()
    return {"match": f"{home} vs {away}", "home_team": home, "away_team": away, "league": league, **pred}


@app.get("/api/teams")
def get_teams(sport: str = Query(None), league: str = Query(None)):
    db     = get_db()
    q      = "SELECT * FROM teams WHERE 1=1"
    params = []
    if sport:  q += " AND sport=?";  params.append(sport)
    if league: q += " AND league=?"; params.append(league)
    q += " ORDER BY name"
    rows = db.execute(q, params).fetchall()
    db.close()
    return {"teams": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/standings")
def get_standings(league: str = Query(...)):
    db   = get_db()
    rows = db.execute(
        "SELECT home_team, home_score, away_score FROM matches "
        "WHERE league=? AND status='FT' AND home_score IS NOT NULL "
        "AND NOT (home_score=0 AND away_score=0) "
        "UNION ALL "
        "SELECT away_team, away_score, home_score FROM matches "
        "WHERE league=? AND status='FT' AND away_score IS NOT NULL "
        "AND NOT (home_score=0 AND away_score=0)",
        (league, league)
    ).fetchall()
    db.close()
    table = {}
    for team, gf, ga in rows:
        if team not in table:
            table[team] = {"team": team, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
        t = table[team]
        t["P"] += 1; t["GF"] += gf; t["GA"] += ga; t["GD"] = t["GF"] - t["GA"]
        if gf > ga:    t["W"] += 1; t["Pts"] += 3
        elif gf == ga: t["D"] += 1; t["Pts"] += 1
        else:          t["L"] += 1
    return {
        "league":    league,
        "standings": sorted(table.values(), key=lambda x: (-x["Pts"], -x["GD"], -x["GF"])),
        "teams":     len(table),
    }


@app.get("/api/bet-of-day")
def bet_of_day():
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM matches WHERE status='Upcoming' "
        "ORDER BY CASE WHEN league='World Cup 2026' THEN 0 ELSE 1 END, match_date ASC LIMIT 15"
    ).fetchall()
    picks = []
    for r in rows:
        m    = dict(r)
        pred = build_prediction(m["home_team"], m["away_team"], m["league"], db)
        best = max(pred["home_win"], pred["draw"], pred["away_win"])
        picks.append({
            "match":      f"{m['home_team']} vs {m['away_team']}",
            "home_team":  m["home_team"],
            "away_team":  m["away_team"],
            "league":     m["league"],
            "date":       m["match_date"],
            "tip":        pred["tip"],
            "tip_code":   pred["tip_code"],
            "confidence": f"{best}%",
            "home_win":   f"{pred['home_win']}%",
            "draw":       f"{pred['draw']}%",
            "away_win":   f"{pred['away_win']}%",
            "over_2_5":   pred["over_2_5"],
            "under_2_5":  pred["under_2_5"],
            "btts":       pred["btts"],
            "risk":       pred["risk"],
        })
    db.close()
    picks.sort(key=lambda x: float(x["confidence"].replace("%", "")), reverse=True)
    return {"picks": picks[:5], "total": len(picks), "model": "Poisson v3.0",
            "note": "All predictions are pre-match. Generated before kickoff."}


@app.get("/api/worldcup2026")
def get_worldcup2026(group: str = Query(None)):
    db      = get_db()
    rows    = db.execute(
        "SELECT * FROM matches WHERE league='World Cup 2026' ORDER BY match_date ASC"
    ).fetchall()
    matches = []
    for r in rows:
        m          = dict(r)
        m["group"] = TEAM_TO_GROUP.get(m.get("home_team", ""), "?")
        if group and m["group"] != group.upper():
            continue
        pred = build_prediction(m["home_team"], m["away_team"], "World Cup 2026", db)
        m.update({
            "home_win_pct":   f"{pred['home_win']}%",
            "draw_pct":       f"{pred['draw']}%",
            "away_win_pct":   f"{pred['away_win']}%",
            "tip":            pred["tip"],
            "tip_code":       pred["tip_code"],
            "risk":           pred["risk"],
            "confidence":     pred["confidence"],
            "over_2_5":       pred["over_2_5"],
            "btts":           pred["btts"],
            "home_avg_goals": pred["home_avg_goals"],
            "away_avg_goals": pred["away_avg_goals"],
        })
        matches.append(m)
    db.close()
    return {
        "tournament":     "FIFA World Cup 2026",
        "host_nations":   ["USA", "Canada", "Mexico"],
        "dates":          "June 11 — July 19, 2026",
        "format":         "48 teams · 12 groups · Round of 32",
        "group_of_death": "Group I — France, Senegal, Norway, Iraq",
        "groups":         WC2026_GROUPS,
        "fixtures":       matches,
        "total_fixtures": len(matches),
    }


@app.get("/api/worldcup2026/groups")
def get_wc_groups():
    return {
        "groups":         WC2026_GROUPS,
        "total_teams":    48,
        "tournament":     "FIFA World Cup 2026",
        "group_of_death": "Group I — France, Senegal, Norway, Iraq",
    }


@app.get("/api/worldcup2026/predict")
def predict_wc_match(home: str = Query(...), away: str = Query(...)):
    db   = get_db()
    pred = build_prediction(home, away, "World Cup 2026", db)
    db.close()
    return {
        "match":      f"{home} vs {away}",
        "home_team":  home,
        "away_team":  away,
        "home_group": f"Group {TEAM_TO_GROUP.get(home, '?')}",
        "away_group": f"Group {TEAM_TO_GROUP.get(away, '?')}",
        "tournament": "FIFA World Cup 2026",
        **pred,
    }
