# Shield Matrix — Your Own Sports API
## Version 3.0 | Built with FastAPI + SQLite

---

## What This Is

Your own sports data API. No third-party API keys. No scraping.
Data comes from:
- **Wikipedia REST API** — official, free, CC-licensed
- **Wikidata SPARQL** — official public query endpoint
- **RSS feeds** — BBC Sport, Sky Sports (publicly published feeds)
- **Seed data** — well-known team/player reference data

You own the database. You serve the API. You monetize it.

---

## Setup (VS Code)

```bash
# 1. Go into the project folder
cd shield_matrix

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000 — your API is live.
Visit http://localhost:8000/docs — interactive API docs (auto-generated).

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Status + DB stats |
| GET | `/teams` | All teams (filter by sport, league) |
| GET | `/teams/{id}` | Single team |
| GET | `/matches` | Match results (filter by sport, league, team) |
| GET | `/matches/h2h?home=Arsenal&away=Chelsea` | Head to head |
| GET | `/players` | Players (filter by team, sport) |
| GET | `/standings?league=Premier+League` | League table |
| GET | `/predict?home=Arsenal&away=Chelsea` | Poisson prediction |
| POST | `/admin/collect` | Trigger manual data collection |
| GET | `/admin/stats` | DB breakdown by sport/league |

---

## Example Requests (from Android Studio / Retrofit)

```
GET http://yourserver.com/predict?home=Arsenal&away=Chelsea
GET http://yourserver.com/matches?sport=football&league=Premier+League
GET http://yourserver.com/matches/h2h?home=Real+Madrid&away=Barcelona
GET http://yourserver.com/teams?sport=basketball
```

---

## How Data Collection Works

On startup: seeds static data + loads sample match history.
Every 6 hours: fetches fresh data from Wikipedia, Wikidata, RSS feeds.
Everything stored in SQLite: `shield_matrix.db`

To run collector manually:
```bash
python collector.py
```

---

## Adding More Data Sources (next steps)

### Option 1 — Wikipedia match pages
Wikipedia has match-by-match pages for every major tournament.
Use the Wikipedia API to parse them:
```
https://en.wikipedia.org/api/rest_v1/page/summary/2024_UEFA_Champions_League_Final
```

### Option 2 — Official league open data
Some leagues publish open data:
- Premier League: stats.premierleague.com (public JSON endpoints)
- NBA: stats.nba.com (public, no key needed — use proper headers)
- MLB: statsapi.mlb.com (free official API)
- NCAA: ncaa.com RSS feeds

### Option 3 — Wikidata SPARQL queries
Wikidata has structured sports data going back decades.
Query builder: https://query.wikidata.org
Example: all FIFA World Cup matches, all NBA champions, etc.

---

## Monetization Plan

1. **Free tier**: 100 predictions/month per user (API key system)
2. **Pro tier**: Unlimited + real-time + advanced stats
3. **Android app**: Show ads on free tier, subscription for pro
4. **API marketplace**: List on RapidAPI as your own product

To add API key authentication, add this to main.py:
```python
from fastapi import Header

async def verify_key(x_api_key: str = Header(...)):
    valid_keys = get_valid_keys_from_db()
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

## File Structure

```
shield_matrix/
├── main.py          # FastAPI routes + prediction engine
├── database.py      # SQLite setup + table creation
├── collector.py     # Data collection from public sources
├── scheduler.py     # Auto-runs collection every 6 hours
├── requirements.txt # Python dependencies
└── shield_matrix.db # Your database (auto-created on first run)
```
