"""
engine.py — Shield Matrix Prediction Engine
Pure Poisson model. No fake data. No simulation theatre.
Takes real xG inputs, returns real probabilities.
"""

import math
import json
from datetime import datetime

# WC average: ~1.35 goals per team per match (historical WC baseline)
WC_AVG = 1.35

# ── TEAM STRENGTH TABLE ─────────────────────────────────────────────────────
# Based on: FIFA rankings, WC2022 performance, WC2026 qualifying stats,
# recent international form (2024-2025).
# attack = avg goals scored per match, defense = avg goals conceded per match
# These update dynamically once WC2026 results come in via rebuild_team_stats()

BASE_STRENGTHS = {
    # Group A
    "Mexico":               {"attack": 1.65, "defense": 0.95},
    "South Korea":          {"attack": 1.45, "defense": 1.10},
    "Czech Republic":       {"attack": 1.25, "defense": 1.20},
    "South Africa":         {"attack": 0.90, "defense": 1.45},
    # Group B
    "Switzerland":          {"attack": 1.55, "defense": 0.85},
    "Canada":               {"attack": 1.35, "defense": 1.00},
    "Bosnia & Herzegovina": {"attack": 1.20, "defense": 1.30},
    "Qatar":                {"attack": 0.80, "defense": 1.55},
    # Group C
    "Brazil":               {"attack": 2.10, "defense": 0.70},
    "Scotland":             {"attack": 1.30, "defense": 1.10},
    "Morocco":              {"attack": 1.25, "defense": 0.90},
    "Haiti":                {"attack": 0.70, "defense": 1.60},
    # Group D
    "United States":        {"attack": 1.55, "defense": 1.00},
    "USA":                  {"attack": 1.55, "defense": 1.00},
    "Australia":            {"attack": 1.25, "defense": 1.20},
    "Türkiye":              {"attack": 1.45, "defense": 1.10},
    "Turkey":               {"attack": 1.45, "defense": 1.10},
    "Paraguay":             {"attack": 1.10, "defense": 1.25},
    # Group E
    "Spain":                {"attack": 2.05, "defense": 0.70},
    "Netherlands":          {"attack": 1.90, "defense": 0.80},
    "Sweden":               {"attack": 1.65, "defense": 0.90},
    "Tunisia":              {"attack": 0.90, "defense": 1.30},
    # Group F
    "Germany":              {"attack": 2.15, "defense": 0.70},
    "Japan":                {"attack": 1.50, "defense": 1.00},
    "Belgium":              {"attack": 1.70, "defense": 0.90},
    "Egypt":                {"attack": 1.10, "defense": 1.10},
    # Group G
    "Portugal":             {"attack": 2.05, "defense": 0.80},
    "Congo DR":             {"attack": 1.00, "defense": 1.30},
    "Uzbekistan":           {"attack": 1.10, "defense": 1.20},
    "Colombia":             {"attack": 1.65, "defense": 1.00},
    # Group H
    "Argentina":            {"attack": 2.20, "defense": 0.70},
    "Algeria":              {"attack": 1.00, "defense": 1.20},
    "Austria":              {"attack": 1.55, "defense": 1.00},
    "Jordan":               {"attack": 0.80, "defense": 1.45},
    # Group I
    "France":               {"attack": 2.10, "defense": 0.70},
    "Senegal":              {"attack": 1.40, "defense": 1.00},
    "Norway":               {"attack": 1.85, "defense": 0.90},
    "Iraq":                 {"attack": 0.90, "defense": 1.40},
    # Group J
    "England":              {"attack": 1.95, "defense": 0.80},
    "Croatia":              {"attack": 1.40, "defense": 1.00},
    "Ghana":                {"attack": 1.10, "defense": 1.20},
    "Panama":               {"attack": 0.80, "defense": 1.45},
    # Group K
    "New Zealand":          {"attack": 1.05, "defense": 1.30},
    "Saudi Arabia":         {"attack": 1.15, "defense": 1.20},
    "Uruguay":              {"attack": 1.60, "defense": 0.90},
    "Iran":                 {"attack": 1.00, "defense": 1.30},
    # Group L
    "Ivory Coast":          {"attack": 1.45, "defense": 1.10},
    "Ecuador":              {"attack": 1.25, "defense": 1.20},
    "Cape Verde":           {"attack": 0.95, "defense": 1.30},
    "Serbia":               {"attack": 1.35, "defense": 1.10},
}


def get_strength(team: str, live_stats: dict = None) -> dict:
    """
    Get team strength. If we have live WC2026 stats, blend them with base ratings.
    This means the engine gets smarter as the tournament progresses.
    """
    base = None
    # Try exact match first
    if team in BASE_STRENGTHS:
        base = BASE_STRENGTHS[team]
    else:
        # Case-insensitive fallback
        for k, v in BASE_STRENGTHS.items():
            if k.lower() == team.lower():
                base = v
                break

    if not base:
        # Unknown team — use tournament average as fallback
        base = {"attack": 1.10, "defense": 1.25}

    # If we have live WC2026 results for this team, blend them in (50/50)
    if live_stats and team in live_stats:
        ls = live_stats[team]
        if ls.get("played", 0) >= 1:
            live_atk = ls.get("avg_gf", base["attack"])
            live_def = ls.get("avg_ga", base["defense"])
            # Weight: more games = more trust in live data
            games = min(ls["played"], 3)
            w = games / 3.0  # 0.33 after 1 game, 0.67 after 2, 1.0 after 3
            return {
                "attack":  round(base["attack"]  * (1 - w) + live_atk * w, 3),
                "defense": round(base["defense"] * (1 - w) + live_def * w, 3),
            }

    return base


def poisson(lam: float, k: int) -> float:
    """P(X=k) — Poisson distribution."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def predict(home: str, away: str, live_stats: dict = None) -> dict:
    """
    Full match prediction using Poisson model.
    Returns: win/draw/loss %, xG, over/under 2.5, BTTS, top scorelines, best bet.
    """
    h = get_strength(home, live_stats)
    a = get_strength(away, live_stats)

    # Expected goals — Dixon-Coles style
    # Home gets +10% advantage (neutral venue WC = 5%, slight home crowd effect)
    home_xg = (h["attack"] / WC_AVG) * (a["defense"] / WC_AVG) * WC_AVG * 1.08
    away_xg = (a["attack"] / WC_AVG) * (h["defense"] / WC_AVG) * WC_AVG

    home_xg = round(max(0.3, home_xg), 3)
    away_xg = round(max(0.3, away_xg), 3)

    # Build 7x7 score matrix (0–6 goals each side)
    MAX = 7
    home_win = draw = away_win = 0.0
    over25 = btts = 0.0
    matrix = {}

    for h_goals in range(MAX):
        for a_goals in range(MAX):
            p = poisson(home_xg, h_goals) * poisson(away_xg, a_goals)
            matrix[f"{h_goals}-{a_goals}"] = round(p * 100, 2)

            if h_goals > a_goals:   home_win += p
            elif h_goals == a_goals: draw    += p
            else:                    away_win += p

            if h_goals + a_goals > 2:       over25 += p
            if h_goals > 0 and a_goals > 0: btts   += p

    # Normalise (matrix covers ~98% of probability space)
    total = home_win + draw + away_win
    hw_pct  = round(home_win / total * 100, 1)
    d_pct   = round(draw     / total * 100, 1)
    aw_pct  = round(100 - hw_pct - d_pct, 1)

    o25_pct  = round(over25 * 100, 1)
    u25_pct  = round(100 - o25_pct, 1)
    btts_pct = round(btts * 100, 1)

    # Top 5 scorelines
    top5 = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:5]
    top5 = [{"score": s, "prob": p} for s, p in top5]

    # Best bet
    candidates = [
        (f"{home} Win", hw_pct),
        ("Draw",        d_pct),
        (f"{away} Win", aw_pct),
        ("Over 2.5",    o25_pct),
        ("Under 2.5",   u25_pct),
        ("BTTS Yes",    btts_pct),
        ("BTTS No",     round(100 - btts_pct, 1)),
    ]
    best_label, best_pct = max(candidates, key=lambda x: x[1])
    confidence = "HIGH" if best_pct >= 55 else "MEDIUM" if best_pct >= 42 else "LOW"

    return {
        "home_team":  home,
        "away_team":  away,
        "xg": {"home": home_xg, "away": away_xg},
        "probabilities": {
            "home_win": hw_pct,
            "draw":     d_pct,
            "away_win": aw_pct,
        },
        "markets": {
            "over_2_5":  o25_pct,
            "under_2_5": u25_pct,
            "btts_yes":  btts_pct,
            "btts_no":   round(100 - btts_pct, 1),
        },
        "top_scorelines": top5,
        "best_bet": {
            "pick":       best_label,
            "probability": best_pct,
            "confidence": confidence,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }
