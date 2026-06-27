"""
live_engine.py - Shield Matrix Live Engine
Uses football-data.org API for real live scores
Falls back to manual input if API unavailable
"""
import math
import requests
from datetime import datetime, date

import os

FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "")
LIVE_URL = "https://api.football-data.org/v4/matches"
HEADERS = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

# WC2026 competition ID on football-data.org
WC_COMPETITION = "WC"


def _extract_score(score: dict) -> tuple:
    """
    Shared helper — extracts current home/away score from a match score block.
    Prefers fullTime if available, falls back to halfTime.
    Returns (home_score, away_score) as ints.
    """
    full = score.get("fullTime", {})
    half = score.get("halfTime", {})
    current = full if full.get("home") is not None else half
    return (current.get("home") or 0, current.get("away") or 0)


def _extract_minute(m: dict) -> int:
    """
    FIX 3: football-data.org v4 stores current minute at
    score.currentMinute, not at the top-level m['minute'].
    Falls back to top-level just in case.
    """
    return m.get("score", {}).get("currentMinute") or m.get("minute") or 0


def fetch_live_scores() -> list:
    """Fetch live WC2026 matches from football-data.org"""
    # FIX 6: Guard against missing token — avoids silent 401s
    if not FOOTBALL_DATA_TOKEN:
        print("[LIVE] No API token set — skipping live fetch.")
        return []

    live_matches = []

    try:
        # Fetch LIVE matches
        r = requests.get(
            f"{LIVE_URL}?status=LIVE&competitions={WC_COMPETITION}",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            for m in r.json().get("matches", []):
                home_score, away_score = _extract_score(m.get("score", {}))
                live_matches.append({
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "home_score": home_score,
                    "away_score": away_score,
                    "minute": _extract_minute(m),
                    "status": m.get("status", "LIVE"),
                })
            print(f"[LIVE] Fetched {len(live_matches)} live matches from API")

        # FIX 1: Only return early if we actually found matches.
        # Previously this returned immediately even on empty list,
        # making the IN_PLAY branch permanently dead code.
        if live_matches:
            return live_matches

        # Try IN_PLAY status as fallback
        r2 = requests.get(
            f"{LIVE_URL}?status=IN_PLAY&competitions={WC_COMPETITION}",
            headers=HEADERS, timeout=10
        )
        if r2.status_code == 200:
            for m in r2.json().get("matches", []):
                # FIX 2: Use shared _extract_score helper so halfTime
                # scores are captured correctly (was only checking fullTime)
                home_score, away_score = _extract_score(m.get("score", {}))
                live_matches.append({
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "home_score": home_score,
                    "away_score": away_score,
                    "minute": _extract_minute(m),
                    "status": "LIVE",
                })
            return live_matches

    except Exception as e:
        print(f"[LIVE] API fetch failed: {e}")

    return []


def fetch_todays_scores() -> list:
    """Fetch today's WC2026 match scores including finished ones."""
    # FIX 6: Guard against missing token
    if not FOOTBALL_DATA_TOKEN:
        print("[LIVE] No API token set — skipping today's scores fetch.")
        return []

    try:
        today = str(date.today())
        r = requests.get(
            f"{LIVE_URL}?competitions={WC_COMPETITION}&dateFrom={today}&dateTo={today}",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            matches = []
            for m in r.json().get("matches", []):
                score = m.get("score", {})
                ft = score.get("fullTime", {})
                ht = score.get("halfTime", {})
                status = m.get("status", "")

                matches.append({
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "home_score": ft.get("home"),
                    "away_score": ft.get("away"),
                    "ht_home": ht.get("home"),
                    "ht_away": ht.get("away"),
                    "minute": _extract_minute(m),
                    "status": status,
                })
            return matches
    except Exception as e:
        print(f"[LIVE] Today scores fetch failed: {e}")
    return []


def poisson(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def live_predict(home, away, home_score, away_score, minute, home_xg_pre, away_xg_pre):
    """Recalculate probabilities based on current score and minute."""
    total_time = 90
    minute = min(minute, 90)
    time_remaining = max(0, total_time - minute)
    time_fraction = time_remaining / total_time

    goal_diff = home_score - away_score

    # Momentum factors:
    # When home leads, home sits back (0.85) and away chases (1.20) — and vice versa.
    # When level after 70 mins, both sides push (1.10).
    home_momentum = 1.0
    away_momentum = 1.0

    if goal_diff > 0:
        home_momentum = 0.85   # home sitting back
        away_momentum = 1.20   # away chasing
    elif goal_diff < 0:
        home_momentum = 1.20   # home chasing
        away_momentum = 0.85   # away sitting back
    elif minute > 70:
        home_momentum = 1.10   # level — both pushing late
        away_momentum = 1.10

    home_rxg = max(0.05, home_xg_pre * time_fraction * home_momentum)
    away_rxg = max(0.05, away_xg_pre * time_fraction * away_momentum)

    hw = d = aw = o25 = btts = 0.0
    current_total = home_score + away_score

    for h_add in range(8):
        for a_add in range(8):
            p = poisson(home_rxg, h_add) * poisson(away_rxg, a_add)
            fh = home_score + h_add
            fa = away_score + a_add
            if fh > fa:    hw  += p
            elif fh == fa: d   += p
            else:          aw  += p
            if fh + fa > 2:        o25  += p
            if fh > 0 and fa > 0:  btts += p

    total = hw + d + aw
    hw_p  = round(hw/total*100, 1)
    d_p   = round(d/total*100,  1)
    aw_p  = round(100-hw_p-d_p, 1)
    o25_p = round(o25*100, 1)
    b_p   = round(btts*100, 1)

    # If game is nearly over and score is clear — reflect that
    if minute >= 85 and abs(goal_diff) >= 2:
        if goal_diff > 0:
            hw_p = 98.0; d_p = 1.5; aw_p = 0.5
        else:
            aw_p = 98.0; d_p = 1.5; hw_p = 0.5

    # FIX 5: Handle all three cases — 3+ goals (Over certain), 2 goals
    # (very unlikely to add one more in 5 mins), 0-1 goals (small chance)
    if minute >= 85:
        if current_total > 2:
            o25_p = 100.0                        # already over 2.5
        elif current_total == 2:
            o25_p = round(o25_p * 0.15, 1)      # exactly 2 — one more goal very unlikely
        else:
            o25_p = round(o25_p * 0.3, 1)       # 0 or 1 goals — needs 3+ in last mins

    cands = [
        (f"{home} Win", hw_p), ("Draw", d_p), (f"{away} Win", aw_p),
        ("Over 2.5", o25_p), ("Under 2.5", round(100-o25_p, 1)),
        ("BTTS Yes", b_p),
    ]
    best, best_p = max(cands, key=lambda x: x[1])
    conf = "HIGH" if best_p >= 60 else "MEDIUM" if best_p >= 45 else "LOW"

    if minute < 15:     phase = "Early game"
    elif minute < 45:   phase = "First half"
    elif minute < 60:   phase = "Second half"
    elif minute < 75:   phase = "Hour mark"
    elif minute < 85:   phase = "Final stretch"
    else:               phase = "Last minutes"

    if goal_diff > 0:   momentum = f"{home} leading"
    elif goal_diff < 0: momentum = f"{away} leading"
    else:               momentum = "Level — both pushing"

    return {
        "home_team": home, "away_team": away,
        "current_score": {"home": home_score, "away": away_score},
        "minute": minute, "phase": phase, "momentum": momentum,
        "remaining_xg": {"home": round(home_rxg,2), "away": round(away_rxg,2)},
        "probabilities": {"home_win": hw_p, "draw": d_p, "away_win": aw_p},
        "markets": {"over_2_5": o25_p, "under_2_5": round(100-o25_p,1), "btts_yes": b_p, "btts_no": round(100-b_p,1)},
        "best_bet": {"pick": best, "probability": best_p, "confidence": conf},
        "updated_at": datetime.utcnow().isoformat(),
    }
