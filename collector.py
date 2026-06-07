import asyncio, httpx, xml.etree.ElementTree as ET, re
from database import get_db

HEADERS = {"User-Agent": "ShieldMatrixBot/3.0"}

RSS_FEEDS = [
    {"url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "sport": "football", "league": "general"},
    {"url": "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml", "sport": "rugby", "league": "general"},
    {"url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml", "sport": "cricket", "league": "general"},
    {"url": "https://feeds.bbci.co.uk/sport/tennis/rss.xml", "sport": "tennis", "league": "general"},
    {"url": "https://feeds.bbci.co.uk/sport/athletics/rss.xml", "sport": "athletics", "league": "general"},
    {"url": "https://www.skysports.com/rss/12040", "sport": "football", "league": "premier_league"},
    {"url": "https://www.skysports.com/rss/12604", "sport": "basketball", "league": "NBA"},
    {"url": "https://www.skysports.com/rss/12433", "sport": "american_football", "league": "NFL"},
    {"url": "https://www.skysports.com/rss/12110", "sport": "cricket", "league": "general"},
    {"url": "https://www.skysports.com/rss/12198", "sport": "rugby", "league": "general"},
    {"url": "https://www.skysports.com/rss/12609", "sport": "tennis", "league": "general"},
    {"url": "https://www.espn.com/espn/rss/soccer/news", "sport": "football", "league": "general"},
    {"url": "https://www.espn.com/espn/rss/nba/news", "sport": "basketball", "league": "NBA"},
    {"url": "https://www.espn.com/espn/rss/nfl/news", "sport": "american_football", "league": "NFL"},
    {"url": "https://www.espn.com/espn/rss/mlb/news", "sport": "baseball", "league": "MLB"},
    {"url": "https://www.espn.com/espn/rss/tennis/news", "sport": "tennis", "league": "general"},
]

FREE_APIS = [
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4328&s=2023-2024", "league": "Premier League", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4335&s=2023-2024", "league": "La Liga", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4331&s=2023-2024", "league": "Bundesliga", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4332&s=2023-2024", "league": "Serie A", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4334&s=2023-2024", "league": "Ligue 1", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4480&s=2023-2024", "league": "Champions League", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4424&s=2023-2024", "league": "NBA", "sport": "basketball"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4391&s=2023-2024", "league": "NFL", "sport": "american_football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4328&s=2022-2023", "league": "Premier League", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4335&s=2022-2023", "league": "La Liga", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4331&s=2022-2023", "league": "Bundesliga", "sport": "football"},
    {"url": "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4332&s=2022-2023", "league": "Serie A", "sport": "football"},
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
    ("West Ham United","football","Premier League","England"),
    ("Brighton","football","Premier League","England"),
    ("Real Madrid","football","La Liga","Spain"),
    ("Barcelona","football","La Liga","Spain"),
    ("Atletico Madrid","football","La Liga","Spain"),
    ("Sevilla","football","La Liga","Spain"),
    ("Bayern Munich","football","Bundesliga","Germany"),
    ("Borussia Dortmund","football","Bundesliga","Germany"),
    ("RB Leipzig","football","Bundesliga","Germany"),
    ("Bayer Leverkusen","football","Bundesliga","Germany"),
    ("Juventus","football","Serie A","Italy"),
    ("AC Milan","football","Serie A","Italy"),
    ("Inter Milan","football","Serie A","Italy"),
    ("Napoli","football","Serie A","Italy"),
    ("Paris Saint-Germain","football","Ligue 1","France"),
    ("Marseille","football","Ligue 1","France"),
    ("Enyimba","football","NPFL","Nigeria"),
    ("Kano Pillars","football","NPFL","Nigeria"),
    ("Al Ahly","football","Egyptian Premier","Egypt"),
    ("Zamalek","football","Egyptian Premier","Egypt"),
    ("Sundowns","football","PSL","South Africa"),
    ("Orlando Pirates","football","PSL","South Africa"),
    ("Brazil","football","International","Brazil"),
    ("Argentina","football","International","Argentina"),
    ("France","football","International","France"),
    ("England","football","International","England"),
    ("Germany","football","International","Germany"),
    ("Spain","football","International","Spain"),
    ("Portugal","football","International","Portugal"),
    ("Netherlands","football","International","Netherlands"),
    ("Nigeria","football","International","Nigeria"),
    ("Senegal","football","International","Senegal"),
    ("Morocco","football","International","Morocco"),
    ("Ghana","football","International","Ghana"),
    ("Cameroon","football","International","Cameroon"),
    ("Ivory Coast","football","International","Ivory Coast"),
    ("Egypt","football","International","Egypt"),
    ("Japan","football","International","Japan"),
    ("South Korea","football","International","South Korea"),
    ("USA","football","International","USA"),
    ("Mexico","football","International","Mexico"),
    ("Croatia","football","International","Croatia"),
    ("Los Angeles Lakers","basketball","NBA","USA"),
    ("Boston Celtics","basketball","NBA","USA"),
    ("Golden State Warriors","basketball","NBA","USA"),
    ("Miami Heat","basketball","NBA","USA"),
    ("Milwaukee Bucks","basketball","NBA","USA"),
    ("Dallas Mavericks","basketball","NBA","USA"),
    ("Denver Nuggets","basketball","NBA","USA"),
    ("Oklahoma City Thunder","basketball","NBA","USA"),
    ("Kansas City Chiefs","american_football","NFL","USA"),
    ("San Francisco 49ers","american_football","NFL","USA"),
    ("Dallas Cowboys","american_football","NFL","USA"),
    ("Philadelphia Eagles","american_football","NFL","USA"),
    ("Buffalo Bills","american_football","NFL","USA"),
    ("Baltimore Ravens","american_football","NFL","USA"),
    ("India","cricket","International","India"),
    ("Australia","cricket","International","Australia"),
    ("England","cricket","International","England"),
    ("Pakistan","cricket","International","Pakistan"),
    ("South Africa","cricket","International","South Africa"),
    ("New Zealand","cricket","International","New Zealand"),
    ("New Zealand","rugby","International","New Zealand"),
    ("South Africa","rugby","International","South Africa"),
    ("England","rugby","International","England"),
    ("France","rugby","International","France"),
    ("Ireland","rugby","International","Ireland"),
]

SEED_PLAYERS = [
    ("Lionel Messi","football","Inter Miami"),
    ("Cristiano Ronaldo","football","Al Nassr"),
    ("Kylian Mbappe","football","Real Madrid"),
    ("Erling Haaland","football","Manchester City"),
    ("Vinicius Junior","football","Real Madrid"),
    ("Mohamed Salah","football","Liverpool"),
    ("Bukayo Saka","football","Arsenal"),
    ("Jude Bellingham","football","Real Madrid"),
    ("Victor Osimhen","football","Galatasaray"),
    ("LeBron James","basketball","Los Angeles Lakers"),
    ("Stephen Curry","basketball","Golden State Warriors"),
    ("Giannis Antetokounmpo","basketball","Milwaukee Bucks"),
    ("Luka Doncic","basketball","Dallas Mavericks"),
    ("Patrick Mahomes","american_football","Kansas City Chiefs"),
    ("Virat Kohli","cricket","India"),
    ("Ben Stokes","cricket","England"),
    ("Siya Kolisi","rugby","South Africa"),
]

SAMPLE_MATCHES = [
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
    ("football","La Liga","2023-24","2024-01-21","Real Madrid","Barcelona",1,1),
    ("football","La Liga","2023-24","2024-02-04","Barcelona","Atletico Madrid",3,5),
    ("football","La Liga","2023-24","2024-02-11","Real Madrid","Atletico Madrid",1,1),
    ("football","La Liga","2023-24","2024-02-25","Barcelona","Real Madrid",1,2),
    ("football","La Liga","2023-24","2024-03-10","Atletico Madrid","Barcelona",3,0),
    ("football","Champions League","2023-24","2024-02-13","Real Madrid","Leipzig",1,0),
    ("football","Champions League","2023-24","2024-02-14","Paris Saint-Germain","Real Sociedad",2,0),
    ("football","Champions League","2023-24","2024-02-20","Arsenal","Porto",1,0),
    ("football","International","2022","2022-11-20","Qatar","Ecuador",0,2),
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
    ("football","International","2023","2024-01-13","Nigeria","Ivory Coast",1,1),
    ("football","International","2023","2024-01-14","Morocco","Tanzania",3,0),
    ("football","International","2023","2024-01-15","Senegal","Cameroon",3,1),
    ("football","International","2023","2024-02-02","Nigeria","Angola",1,0),
    ("football","International","2023","2024-02-11","Nigeria","Ivory Coast",1,2),
    ("basketball","NBA","2023-24","2024-01-15","Los Angeles Lakers","Boston Celtics",110,118),
    ("basketball","NBA","2023-24","2024-01-22","Golden State Warriors","Miami Heat",120,105),
    ("basketball","NBA","2023-24","2024-01-28","Milwaukee Bucks","Philadelphia 76ers",109,104),
    ("basketball","NBA","2023-24","2024-02-05","Denver Nuggets","Los Angeles Lakers",124,114),
    ("basketball","NBA","2023-24","2024-02-12","Boston Celtics","Golden State Warriors",140,88),
    ("basketball","NBA","2023-24","2024-03-10","Boston Celtics","Milwaukee Bucks",119,91),
    ("basketball","NBA","2023-24","2024-03-17","Los Angeles Lakers","Golden State Warriors",130,106),
    ("american_football","NFL","2023-24","2024-01-13","Kansas City Chiefs","Miami Dolphins",26,7),
    ("american_football","NFL","2023-24","2024-01-20","Kansas City Chiefs","Buffalo Bills",27,24),
    ("american_football","NFL","2023-24","2024-01-20","San Francisco 49ers","Green Bay Packers",24,21),
    ("american_football","NFL","2023-24","2024-02-11","Kansas City Chiefs","San Francisco 49ers",25,22),
    ("cricket","International","2023","2023-10-14","Pakistan","India",191,193),
    ("cricket","International","2023","2023-11-19","Australia","India",241,240),
    ("rugby","International","2023","2023-09-09","France","New Zealand",13,27),
    ("rugby","International","2023","2023-10-28","New Zealand","South Africa",11,12),
]

def seed_static_data():
    db = get_db()
    for (name, sport, league, country) in SEED_TEAMS:
        exists = db.execute("SELECT id FROM teams WHERE name=? AND sport=?", (name, sport)).fetchone()
        if not exists:
            db.execute("INSERT INTO teams (name, sport, league, country) VALUES (?,?,?,?)", (name, sport, league, country))
    for (name, sport, team) in SEED_PLAYERS:
        exists = db.execute("SELECT id FROM players WHERE name=?", (name,)).fetchone()
        if not exists:
            db.execute("INSERT INTO players (name, sport, team_name) VALUES (?,?,?)", (name, sport, team))
    db.commit()
    db.close()
    print("[SEED] Static data loaded.")

def seed_match_history():
    db = get_db()
    for (sport, league, season, mdate, home, away, hs, as_) in SAMPLE_MATCHES:
        exists = db.execute("SELECT id FROM matches WHERE home_team=? AND away_team=? AND match_date=?", (home, away, mdate)).fetchone()
        if not exists:
            db.execute("INSERT INTO matches (sport, league, season, match_date, home_team, away_team, home_score, away_score, status) VALUES (?,?,?,?,?,?,?,?,?)", (sport, league, season, mdate, home, away, hs, as_, "FT"))
    db.commit()
    db.close()
    print("[SEED] Match history loaded.")

def _try_parse_scoreline(title, sport, league, url, pub):
    m = re.match(r"^(.+?)\s+(\d+)\s*[-]\s*(\d+)\s+(.+?)(?:\s*[:|,].*)?$", title.strip())
    if m:
        home, h_score, a_score, away = m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.group(4).strip()
        if len(home) > 50 or len(away) > 50:
            return
        db = get_db()
        exists = db.execute("SELECT id FROM matches WHERE home_team=? AND away_team=? AND source_url=?", (home, away, url)).fetchone()
        if not exists:
            db.execute("INSERT INTO matches (sport, league, match_date, home_team, away_team, home_score, away_score, status, source_url) VALUES (?,?,?,?,?,?,?,?,?)", (sport, league, pub, home, away, h_score, a_score, "FT", url))
            db.commit()
            print(f"[MATCH] {home} {h_score}-{a_score} {away}")
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
            link = item.findtext("link", "")
            pub = item.findtext("pubDate", "")
            if " v " in title or " vs " in title or re.search(r'\d+-\d+', title):
                _try_parse_scoreline(title, feed["sport"], feed["league"], link, pub)
    except Exception as e:
        print(f"[RSS] Error {feed['league']}: {e}")

async def collect_thesportsdb(client, feed):
    try:
        resp = await client.get(feed["url"], headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"[SPORTSDB] {feed['league']} — status {resp.status_code}")
            return
        data = resp.json()
        events = data.get("events") or []
        saved = 0
        db = get_db()
        for e in events:
            home = e.get("strHomeTeam", "")
            away = e.get("strAwayTeam", "")
            h_score = e.get("intHomeScore")
            a_score = e.get("intAwayScore")
            date = e.get("dateEvent", "")
            season = e.get("strSeason", "")
            if not home or not away or h_score is None or a_score is None:
                continue
            try:
                h_score = int(h_score)
                a_score = int(a_score)
            except:
                continue
            exists = db.execute("SELECT id FROM matches WHERE home_team=? AND away_team=? AND match_date=?", (home, away, date)).fetchone()
            if not exists:
                db.execute("INSERT INTO matches (sport, league, season, match_date, home_team, away_team, home_score, away_score, status) VALUES (?,?,?,?,?,?,?,?,?)", (feed["sport"], feed["league"], season, date, home, away, h_score, a_score, "FT"))
                saved += 1
        db.commit()
        db.close()
        print(f"[SPORTSDB] {feed['league']} — saved {saved} matches")
    except Exception as e:
        print(f"[SPORTSDB] Error {feed['league']}: {e}")

async def run_all_collectors():
    print("[COLLECTOR] Starting full pipeline...")
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