# test.py
import requests

# Premium, real-world analytical payload for the Sports Pipeline
sports_payload = {
    "sport_type": "FOOTBALL",
    "event_name": "Real Madrid vs Manchester City",
    "tournament": "UEFA Champions League",
    "raw_stats": {
        "expected_goals_xG": {"home_madrid": 1.94, "away_city": 2.15},
        "recent_form_5_games": {"home_madrid": "W-W-D-W-W", "away_city": "W-D-W-W-W"},
        "historical_head_to_head": {"madrid_wins": 4, "draws": 4, "city_wins": 5},
        "key_injury_impact": "Manchester City starting center-back ruled out; Real Madrid mid-field fully fit.",
        "implied_market_odds": {"home_win": 2.60, "draw": 3.40, "away_win": 2.45}
    },
    "prediction_yield": "Away Win or Draw (X2) probability: 64%. Over 2.5 Match Goals probability: 71%. Match trend favors high-intensity transitional attacking sequences.",
    "risk_assessment": "MEDIUM"
}

print("📊 Pumping analytical data packet into Shield Sports Pipeline...")
response = requests.post("http://127.0.0.1:8000/api/v1/analytics/ingest", json=sports_payload)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")