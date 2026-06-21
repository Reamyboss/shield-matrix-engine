"""
live_engine.py — Shield Matrix Live In-Play Engine
Adjusts predictions based on current score + minutes played.
No changes to existing engine.py — this is additive only.
"""

import math
import requests
from datetime import datetime

# TheSportsDB free tier — no API key needed for live scores
LIVE_URL = "https://www.thesportsdb.com/api/v1/json/3/eventslive.php?sport=Soccer"


def fetch_live_scores() -> list:
    """
    Auto-fetch live WC2026 matches from TheSportsDB.
    Returns list of live matches with current score and minute.
    """
    try:
        r = requests.get(LIVE_URL, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json()
            events = data.get("events", []) or []
            live = []
            for e in events:
                # Filter for World Cup only
                league = (e.get("strLeague") or "").lower()
                if "world cup" not in league and "fifa" not in league:
                    continue
                live.append({
                    "home":    e.get("strHomeTeam", ""),
                    "away":    e.get("strAwayTeam", ""),
                    "home_score": int(e.get("intHomeScore") or 0),
                    "away_score": int(e.get("intAwayScore") or 0),
                    "minute":  int(e.get("strProgress") or e.get("intProgress") or 0),
                    "status":  e.get("strStatus", "LIVE"),
                    "event_id": e.get("idEvent", ""),
                })
            return live
    except Exception as e:
        print(f"[LIVE] Auto-fetch failed: {e}")
    return []


def poisson(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def live_predict(
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    minute: int,
    home_xg_pre: float,
    away_xg_pre: float,
) -> dict:
    """
    Recalculate match probabilities mid-game.

    Logic:
    1. Calculate remaining xG based on time left
    2. Add goals already scored as certainties
    3. Recompute win/draw/loss from current state
    4. Adjust for scoreline momentum (team winning = slightly better attack)
    """

    # Time remaining (WC = 90 mins standard, extra time handled separately)
    total_time = 90
    if minute >= 90:
        minute = 90

    time_remaining = max(0, total_time - minute)
    time_fraction = time_remaining / total_time  # 0.0 to 1.0

    # Remaining xG = pre-match xG scaled to time left
    # + momentum factor: team that's winning attacks slightly less (defending lead)
    goal_diff = home_score - away_score

    home_momentum = 1.0
    away_momentum = 1.0

    if goal_diff > 0:
        # Home winning — home defends, away pushes harder
        home_momentum = 0.85
        away_momentum = 1.20
    elif goal_diff < 0:
        # Away winning — away defends, home pushes harder
        home_momentum = 1.20
        away_momentum = 0.85
    elif minute > 70:
        # Draw late — both push, slightly more open
        home_momentum = 1.10
        away_momentum = 1.10

    home_remaining_xg = home_xg_pre * time_fraction * home_momentum
    away_remaining_xg = away_xg_pre * time_fraction * away_momentum

    home_remaining_xg = max(0.05, home_remaining_xg)
    away_remaining_xg = max(0.05, away_remaining_xg)

    # Build probability matrix for additional goals
    MAX = 8
    home_win = draw = away_win = 0.0
    over_total = 0.0  # total goals will exceed 2.5
    btts = 0.0

    current_total = home_score + away_score

    for h_add in range(MAX):
        for a_add in range(MAX):
            p = poisson(home_remaining_xg, h_add) * poisson(away_remaining_xg, a_add)
            final_h = home_score + h_add
            final_a = away_score + a_add

            if final_h > final_a:
                home_win += p
            elif final_h == final_a:
                draw += p
            else:
                away_win += p

            if final_h + final_a > 2:
                over_total += p

            if final_h > 0 and final_a > 0:
                btts += p

    total = home_win + draw + away_win
    hw_pct  = round(home_win / total * 100, 1)
    d_pct   = round(draw     / total * 100, 1)
    aw_pct  = round(100 - hw_pct - d_pct, 1)
    o25_pct = round(over_total * 100, 1)
    u25_pct = round(100 - o25_pct, 1)
    btts_pct = round(btts * 100, 1)

    # Best bet
    candidates = [
        (f"{home} Win", hw_pct),
        ("Draw",        d_pct),
        (f"{away} Win", aw_pct),
        ("Over 2.5",    o25_pct),
        ("Under 2.5",   u25_pct),
        ("BTTS Yes",    btts_pct),
    ]
    best_label, best_pct = max(candidates, key=lambda x: x[1])
    confidence = "HIGH" if best_pct >= 60 else "MEDIUM" if best_pct >= 45 else "LOW"

    # Game state summary
    if minute < 15:
        phase = "Early game"
    elif minute < 45:
        phase = "First half"
    elif minute < 60:
        phase = "Second half started"
    elif minute < 75:
        phase = "Hour mark"
    elif minute < 85:
        phase = "Final stretch"
    else:
        phase = "Last minutes"

    if goal_diff > 0:
        momentum_txt = f"{home} leading — defending advantage"
    elif goal_diff < 0:
        momentum_txt = f"{away} leading — defending advantage"
    else:
        momentum_txt = "Level — both teams pushing"

    return {
        "home_team":    home,
        "away_team":    away,
        "current_score": {"home": home_score, "away": away_score},
        "minute":       minute,
        "phase":        phase,
        "momentum":     momentum_txt,
        "remaining_xg": {
            "home": round(home_remaining_xg, 2),
            "away": round(away_remaining_xg, 2),
        },
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
        "best_bet": {
            "pick":        best_label,
            "probability": best_pct,
            "confidence":  confidence,
        },
        "updated_at": datetime.utcnow().isoformat(),
    }
