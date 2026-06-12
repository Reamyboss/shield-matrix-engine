import asyncio, httpx, xml.etree.ElementTree as ET, re
from database import get_db

HEADERS = {"User-Agent": "ShieldMatrixBot/3.0"}

RSS_FEEDS = [
    {"url": "https://feeds.bbci.co.uk/sport/football/rss.xml",    "sport": "football", "league": "general"},
    {"url": "https://www.skysports.com/rss/12040",                 "sport": "football", "league": "Premier League"},
    {"url": "https://www.espn.com/espn/rss/soccer/news",           "sport": "football", "league": "general"},
]

FREE_APIS = [
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4328&s=2024-2025", "league": "Premier League",   "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4335&s=2024-2025", "league": "La Liga",          "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4331&s=2024-2025", "league": "Bundesliga",       "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4332&s=2024-2025", "league": "Serie A",          "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4334&s=2024-2025", "league": "Ligue 1",          "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4480&s=2024-2025", "league": "Champions League", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4328&s=2023-2024", "league": "Premier League",   "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4335&s=2023-2024", "league": "La Liga",          "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4443&s=2026",      "league": "World Cup 2026",   "sport": "football"},
]

SEED_TEAMS = [
    ("Arsenal","football","Premier League","England"),
    ("Chelsea","football","Premier League","England"),
    ("Liverpool","football","Premier League","England"),
    ("Manchester City","football","Premier League","England"),
    ("Manchester United","football","Premier League","England"),
    ("Tottenham Hotspur","football","Premier League","England"),
    ("Newcastle United","football","Premier League","England"),
    ("Aston Villa","football","Premier League","England"),
    ("Real Madrid","football","La Liga","Spain"),
    ("Barcelona","football","La Liga","Spain"),
    ("Atletico Madrid","football","La Liga","Spain"),
    ("Bayern Munich","football","Bundesliga","Germany"),
    ("Borussia Dortmund","football","Bundesliga","Germany"),
    ("Bayer Leverkusen","football","Bundesliga","Germany"),
    ("Inter Milan","football","Serie A","Italy"),
    ("AC Milan","football","Serie A","Italy"),
    ("Juventus","football","Serie A","Italy"),
    ("Paris Saint-Germain","football","Ligue 1","France"),
    # World Cup 2026
    ("Brazil","football","World Cup 2026","Brazil"),
    ("Argentina","football","World Cup 2026","Argentina"),
    ("France","football","World Cup 2026","France"),
    ("England","football","World Cup 2026","England"),
    ("Germany","football","World Cup 2026","Germany"),
    ("Spain","football","World Cup 2026","Spain"),
    ("Portugal","football","World Cup 2026","Portugal"),
    ("Netherlands","football","World Cup 2026","Netherlands"),
    ("Belgium","football","World Cup 2026","Belgium"),
    ("Croatia","football","World Cup 2026","Croatia"),
    ("Uruguay","football","World Cup 2026","Uruguay"),
    ("Colombia","football","World Cup 2026","Colombia"),
    ("Mexico","football","World Cup 2026","Mexico"),
    ("USA","football","World Cup 2026","USA"),
    ("Canada","football","World Cup 2026","Canada"),
    ("Italy","football","World Cup 2026","Italy"),
    ("Switzerland","football","World Cup 2026","Switzerland"),
    ("Denmark","football","World Cup 2026","Denmark"),
    ("Japan","football","World Cup 2026","Japan"),
    ("South Korea","football","World Cup 2026","South Korea"),
    ("Morocco","football","World Cup 2026","Morocco"),
    ("Senegal","football","World Cup 2026","Senegal"),
    ("Australia","football","World Cup 2026","Australia"),
    ("Ecuador","football","World Cup 2026","Ecuador"),
    ("Serbia","football","World Cup 2026","Serbia"),
    ("Austria","football","World Cup 2026","Austria"),
    ("Norway","football","World Cup 2026","Norway"),
    ("Turkey","football","World Cup 2026","Turkey"),
    ("Iran","football","World Cup 2026","Iran"),
    ("Saudi Arabia","football","World Cup 2026","Saudi Arabia"),
    ("Ghana","football","World Cup 2026","Ghana"),
    ("Ivory Coast","football","World Cup 2026","Ivory Coast"),
    ("Cameroon","football","World Cup 2026","Cameroon"),
    ("Egypt","football","World Cup 2026","Egypt"),
    ("Algeria","football","World Cup 2026","Algeria"),
    ("Mali","football","World Cup 2026","Mali"),
    ("DR Congo","football","World Cup 2026","DR Congo"),
    ("Tunisia","football","World Cup 2026","Tunisia"),
    ("South Africa","football","World Cup 2026","South Africa"),
    ("Nigeria","football","World Cup 2026","Nigeria"),
    ("Paraguay","football","World Cup 2026","Paraguay"),
    ("Chile","football","World Cup 2026","Chile"),
    ("Qatar","football","World Cup 2026","Qatar"),
    ("Iraq","football","World Cup 2026","Iraq"),
    ("Panama","football","World Cup 2026","Panama"),
    ("New Zealand","football","World Cup 2026","New Zealand"),
    ("Scotland","football","World Cup 2026","Scotland"),
    ("Ukraine","football","World Cup 2026","Ukraine"),
    ("Romania","football","World Cup 2026","Romania"),
    ("Slovakia","football","World Cup 2026","Slovakia"),
    ("Albania","football","World Cup 2026","Albania"),
    ("Hungary","football","World Cup 2026","Hungary"),
    ("Czechia","football","World Cup 2026","Czech Republic"),
    ("Slovenia","football","World Cup 2026","Slovenia"),
    ("Greece","football","World Cup 2026","Greece"),
    ("Venezuela","football","World Cup 2026","Venezuela"),
    ("Peru","football","World Cup 2026","Peru"),
    ("Haiti","football","World Cup 2026","Haiti"),
    ("Uzbekistan","football","World Cup 2026","Uzbekistan"),
    ("Jordan","football","World Cup 2026","Jordan"),
    ("Bosnia and Herzegovina","football","World Cup 2026","Bosnia and Herzegovina"),
    ("Cape Verde","football","World Cup 2026","Cape Verde"),
    ("Benin","football","World Cup 2026","Benin"),
    ("Curacao","football","World Cup 2026","Curacao"),
    ("Sweden","football","World Cup 2026","Sweden"),
    ("Poland","football","World Cup 2026","Poland"),
]

# Real football match history — used for Poisson lambda calculations
SAMPLE_MATCHES = [
    # ── Premier League 2023-24 ──────────────────────────────────────
    ("football","Premier League","2023-24","2024-01-14","Arsenal","Chelsea",2,1),
    ("football","Premier League","2023-24","2024-01-20","Manchester City","Liverpool",1,1),
    ("football","Premier League","2023-24","2024-02-03","Arsenal","Liverpool",3,1),
    ("football","Premier League","2023-24","2024-02-10","Chelsea","Manchester United",2,0),
    ("football","Premier League","2023-24","2024-02-24","Manchester City","Arsenal",0,0),
    ("football","Premier League","2023-24","2024-03-02","Liverpool","Manchester City",1,1),
    ("football","Premier League","2023-24","2024-03-16","Chelsea","Newcastle United",3,2),
    ("football","Premier League","2023-24","2024-03-23","Liverpool","Manchester United",2,2),
    ("football","Premier League","2023-24","2024-04-06","Arsenal","Aston Villa",2,0),
    ("football","Premier League","2023-24","2024-04-13","Manchester City","Chelsea",4,4),
    ("football","Premier League","2023-24","2024-04-20","Tottenham Hotspur","Arsenal",0,3),
    ("football","Premier League","2023-24","2024-05-04","Arsenal","Bournemouth",3,0),
    ("football","Premier League","2023-24","2024-05-11","Manchester City","Fulham",4,0),
    ("football","Premier League","2023-24","2024-05-19","Liverpool","Wolves",2,0),
    ("football","Premier League","2023-24","2024-05-19","Arsenal","Everton",2,1),
    # ── La Liga 2023-24 ────────────────────────────────────────────
    ("football","La Liga","2023-24","2024-01-21","Real Madrid","Barcelona",1,1),
    ("football","La Liga","2023-24","2024-02-04","Barcelona","Atletico Madrid",3,5),
    ("football","La Liga","2023-24","2024-02-11","Real Madrid","Atletico Madrid",1,1),
    ("football","La Liga","2023-24","2024-02-25","Barcelona","Real Madrid",1,2),
    ("football","La Liga","2023-24","2024-03-10","Atletico Madrid","Barcelona",3,0),
    ("football","La Liga","2023-24","2024-04-21","Real Madrid","Barcelona",3,2),
    ("football","La Liga","2023-24","2024-04-14","Real Madrid","Manchester City",3,3),
    # ── Champions League 2023-24 ───────────────────────────────────
    ("football","Champions League","2023-24","2024-02-13","Real Madrid","Leipzig",1,0),
    ("football","Champions League","2023-24","2024-02-14","Paris Saint-Germain","Real Sociedad",2,0),
    ("football","Champions League","2023-24","2024-02-20","Arsenal","Porto",1,0),
    ("football","Champions League","2023-24","2024-04-09","Manchester City","Real Madrid",1,1),
    ("football","Champions League","2023-24","2024-05-08","Real Madrid","Bayern Munich",2,2),
    ("football","Champions League","2023-24","2024-06-01","Real Madrid","Borussia Dortmund",2,0),
    # ── Bundesliga 2023-24 ─────────────────────────────────────────
    ("football","Bundesliga","2023-24","2024-02-10","Bayern Munich","Bayer Leverkusen",0,3),
    ("football","Bundesliga","2023-24","2024-03-30","Bayer Leverkusen","Bayern Munich",3,0),
    ("football","Bundesliga","2023-24","2024-04-13","Borussia Dortmund","Bayern Munich",0,0),
    # ── Serie A 2023-24 ────────────────────────────────────────────
    ("football","Serie A","2023-24","2024-02-04","Inter Milan","Juventus",1,0),
    ("football","Serie A","2023-24","2024-03-17","AC Milan","Napoli",1,0),
    ("football","Serie A","2023-24","2024-04-22","Inter Milan","AC Milan",2,1),
    # ── Ligue 1 2023-24 ────────────────────────────────────────────
    ("football","Ligue 1","2023-24","2024-03-03","Paris Saint-Germain","Marseille",2,0),
    ("football","Ligue 1","2023-24","2024-04-21","Paris Saint-Germain","Lyon",4,1),
    # ── World Cup 2022 — international base data ───────────────────
    ("football","International","2022","2022-11-21","England","Iran",6,2),
    ("football","International","2022","2022-11-22","Argentina","Saudi Arabia",1,2),
    ("football","International","2022","2022-11-23","France","Australia",4,1),
    ("football","International","2022","2022-11-24","Spain","Costa Rica",7,0),
    ("football","International","2022","2022-11-24","Germany","Japan",1,2),
    ("football","International","2022","2022-11-25","Brazil","Serbia",2,0),
    ("football","International","2022","2022-11-26","France","Denmark",2,1),
    ("football","International","2022","2022-11-26","Argentina","Mexico",2,0),
    ("football","International","2022","2022-11-26","England","USA",0,0),
    ("football","International","2022","2022-11-27","Portugal","Uruguay",2,0),
    ("football","International","2022","2022-11-28","Brazil","Switzerland",1,0),
    ("football","International","2022","2022-12-05","Brazil","South Korea",4,1),
    ("football","International","2022","2022-12-06","Morocco","Spain",0,0),
    ("football","International","2022","2022-12-09","Argentina","Netherlands",2,2),
    ("football","International","2022","2022-12-10","France","England",2,1),
    ("football","International","2022","2022-12-10","Morocco","Portugal",1,0),
    ("football","International","2022","2022-12-13","Argentina","Croatia",3,0),
    ("football","International","2022","2022-12-14","France","Morocco",2,0),
    ("football","International","2022","2022-12-18","Argentina","France",3,3),
    # ── AFCON 2024 ─────────────────────────────────────────────────
    ("football","International","2023","2024-01-13","Nigeria","Ivory Coast",1,1),
    ("football","International","2023","2024-01-14","Morocco","Tanzania",3,0),
    ("football","International","2023","2024-01-15","Senegal","Cameroon",3,1),
    ("football","International","2023","2024-02-02","Nigeria","Angola",1,0),
    ("football","International","2023","2024-02-11","Nigeria","Ivory Coast",1,2),
    ("football","International","2023","2024-01-19","Ghana","Ivory Coast",1,1),
    ("football","International","2023","2024-01-22","Egypt","Mozambique",2,2),
    ("football","International","2023","2024-02-02","Morocco","South Africa",0,2),
    ("football","International","2023","2024-02-11","Ivory Coast","DR Congo",1,0),
    # ── 2026 World Cup Qualifiers ──────────────────────────────────
    ("football","International","2025","2025-03-21","England","Albania",2,0),
    ("football","International","2025","2025-03-24","France","Croatia",0,1),
    ("football","International","2025","2025-03-21","Germany","Netherlands",1,0),
    ("football","International","2025","2025-03-24","Spain","Netherlands",3,2),
    ("football","International","2025","2025-03-22","Portugal","Denmark",2,0),
    ("football","International","2025","2025-03-25","Argentina","Brazil",1,1),
    ("football","International","2025","2025-03-25","Colombia","Uruguay",1,0),
    ("football","International","2025","2025-03-25","USA","Canada",2,1),
    ("football","International","2025","2025-03-25","Mexico","Panama",2,0),
    ("football","International","2025","2025-03-21","Morocco","Ivory Coast",1,0),
    ("football","International","2025","2025-03-22","Senegal","DR Congo",1,1),
    ("football","International","2025","2025-03-21","Japan","Bahrain",2,0),
    ("football","International","2025","2025-03-25","South Korea","China",1,0),
    # ── Extra international results for broader team coverage ──────
    ("football","International","2024","2024-06-14","Germany","Scotland",5,1),
    ("football","International","2024","2024-06-15","Hungary","Switzerland",1,3),
    ("football","International","2024","2024-06-15","Spain","Croatia",3,0),
    ("football","International","2024","2024-06-16","Italy","Albania",2,1),
    ("football","International","2024","2024-06-16","Poland","Netherlands",1,2),
    ("football","International","2024","2024-06-17","Slovenia","Denmark",1,1),
    ("football","International","2024","2024-06-17","Serbia","England",0,1),
    ("football","International","2024","2024-06-18","Austria","France",0,1),
    ("football","International","2024","2024-06-18","Turkey","Georgia",3,1),
    ("football","International","2024","2024-06-19","Belgium","Slovakia",0,1),
    ("football","International","2024","2024-06-20","Romania","Ukraine",3,0),
    ("football","International","2024","2024-06-22","England","Denmark",1,1),
    ("football","International","2024","2024-06-24","France","Poland",1,1),
    ("football","International","2024","2024-06-24","Netherlands","Austria",2,3),
    ("football","International","2024","2024-06-25","Germany","Switzerland",0,0),
    ("football","International","2024","2024-06-25","Spain","Albania",1,0),
    ("football","International","2024","2024-06-29","Spain","Georgia",4,1),
    ("football","International","2024","2024-06-29","Germany","Denmark",2,0),
    ("football","International","2024","2024-06-30","England","Slovakia",2,1),
    ("football","International","2024","2024-06-30","France","Belgium",1,0),
    ("football","International","2024","2024-07-01","Portugal","Slovenia",0,0),
    ("football","International","2024","2024-07-02","Romania","Netherlands",0,3),
    ("football","International","2024","2024-07-05","Spain","Germany",2,1),
    ("football","International","2024","2024-07-06","France","Portugal",0,0),
    ("football","International","2024","2024-07-09","Spain","France",2,1),
    ("football","International","2024","2024-07-10","England","Netherlands",2,1),
    ("football","International","2024","2024-07-14","Spain","England",2,1),
    ("football","International","2024","2024-09-07","England","Finland",2,0),
    ("football","International","2024","2024-09-10","France","Belgium",2,0),
    ("football","International","2024","2024-09-07","Germany","Hungary",5,0),
    ("football","International","2024","2024-09-09","Spain","Serbia",3,0),
    ("football","International","2024","2024-09-10","Portugal","Croatia",2,2),
    ("football","International","2024","2024-09-09","Netherlands","Germany",2,2),
    ("football","International","2024","2024-10-11","France","Israel",4,1),
    ("football","International","2024","2024-10-14","England","Greece",2,1),
    ("football","International","2024","2024-10-12","Germany","Netherlands",1,0),
    ("football","International","2024","2024-10-15","Spain","Denmark",1,0),
    ("football","International","2024","2024-10-15","Portugal","Poland",3,1),
    ("football","International","2024","2024-11-18","Germany","Bosnia and Herzegovina",7,0),
    ("football","International","2024","2024-11-15","England","Republic of Ireland",5,0),
    ("football","International","2024","2024-11-18","France","Italy",1,3),
    ("football","International","2024","2024-11-16","Spain","Switzerland",3,2),
    ("football","International","2024","2024-11-18","Netherlands","Hungary",4,0),
    ("football","International","2025","2025-03-22","Belgium","Ukraine",5,1),
    ("football","International","2025","2025-03-23","Norway","Israel",5,0),
]

def seed_static_data():
    db = get_db()
    for (name, sport, league, country) in SEED_TEAMS:
        exists = db.execute(
            "SELECT id FROM teams WHERE name=? AND sport=? AND league=?",
            (name, sport, league)
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO teams (name, sport, league, country) VALUES (?,?,?,?)",
                (name, sport, league, country)
            )
    db.commit()
    db.close()
    print("[SEED] Teams loaded.")

def seed_match_history():
    db = get_db()
    added = 0
    for (sport, league, season, mdate, home, away, hs, as_) in SAMPLE_MATCHES:
        exists = db.execute(
            "SELECT id FROM matches WHERE home_team=? AND away_team=? AND match_date=?",
            (home, away, mdate)
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO matches (sport, league, season, match_date, home_team, away_team, home_score, away_score, status) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sport, league, season, mdate, home, away, hs, as_, "FT")
            )
            added += 1
    db.commit()
    db.close()
    print(f"[SEED] Match history loaded — {added} new records.")

def _try_parse_scoreline(title, sport, league, url, pub):
    m = re.match(r"^(.+?)\s+(\d+)\s*[-]\s*(\d+)\s+(.+?)(?:\s*[:|,].*)?$", title.strip())
    if not m:
        return
    home, h_score, a_score, away = m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.group(4).strip()
    if len(home) > 50 or len(away) > 50:
        return
    # reject basketball/cricket scores sneaking in
    if h_score > 15 or a_score > 15:
        return
    db = get_db()
    exists = db.execute(
        "SELECT id FROM matches WHERE home_team=? AND away_team=? AND source_url=?",
        (home, away, url)
    ).fetchone()
    if not exists:
        db.execute(
            "INSERT INTO matches (sport, league, match_date, home_team, away_team, home_score, away_score, status, source_url) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (sport, league, pub, home, away, h_score, a_score, "FT", url)
        )
        db.commit()
    db.close()

async def collect_rss_feed(client, feed):
    try:
        resp = await client.get(feed["url"], headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return
        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            return
        items = channel.findall("item")
        print(f"[RSS] {feed['sport']} — {len(items)} items from {feed['league']}")
        for item in items[:30]:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            pub   = item.findtext("pubDate", "")
            if re.search(r'\d+-\d+', title):
                _try_parse_scoreline(title, feed["sport"], feed["league"], link, pub)
    except Exception as e:
        print(f"[RSS] Error {feed['league']}: {e}")

async def collect_thesportsdb(client, feed):
    try:
        resp = await client.get(feed["url"], headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return
        data   = resp.json()
        events = data.get("events") or []
        saved  = 0
        db     = get_db()
        for e in events:
            home    = e.get("strHomeTeam", "")
            away    = e.get("strAwayTeam", "")
            h_score = e.get("intHomeScore")
            a_score = e.get("intAwayScore")
            date    = e.get("dateEvent", "")
            season  = e.get("strSeason", "")
            if not home or not away or h_score is None or a_score is None:
                continue
            try:
                h_score = int(h_score)
                a_score = int(a_score)
            except:
                continue
            # Only save football-range scores
            if h_score > 15 or a_score > 15:
                continue
            exists = db.execute(
                "SELECT id FROM matches WHERE home_team=? AND away_team=? AND match_date=?",
                (home, away, date)
            ).fetchone()
            if not exists:
                db.execute(
                    "INSERT INTO matches (sport, league, season, match_date, home_team, away_team, home_score, away_score, status) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (feed["sport"], feed["league"], season, date, home, away, h_score, a_score, "FT")
                )
                saved += 1
        db.commit()
        db.close()
        if saved:
            print(f"[SPORTSDB] {feed['league']} — saved {saved} matches")
    except Exception as e:
        print(f"[SPORTSDB] Error {feed['league']}: {e}")

async def run_all_collectors():
    print("[COLLECTOR] Starting pipeline...")
    seed_static_data()
    seed_match_history()
    async with httpx.AsyncClient() as client:
        rss_tasks = [collect_rss_feed(client, feed) for feed in RSS_FEEDS]
        await asyncio.gather(*rss_tasks, return_exceptions=True)
        sdb_tasks = [collect_thesportsdb(client, feed) for feed in FREE_APIS]
        await asyncio.gather(*sdb_tasks, return_exceptions=True)
    print("[COLLECTOR] Pipeline complete.")

if __name__ == "__main__":
    asyncio.run(run_all_collectors())
