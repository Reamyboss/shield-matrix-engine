import sqlite3, os
DB_PATH = os.getenv("DB_PATH", "shield_matrix.db")
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, sport TEXT NOT NULL, league TEXT, country TEXT, collected_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, sport TEXT NOT NULL, league TEXT, season TEXT, match_date TEXT, home_team TEXT NOT NULL, away_team TEXT NOT NULL, home_score INTEGER, away_score INTEGER, status TEXT DEFAULT 'FT', source_url TEXT, collected_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, sport TEXT, team_name TEXT, collected_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS standings (id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT NOT NULL, season TEXT, sport TEXT, position INTEGER, team_name TEXT, played INTEGER, won INTEGER, drawn INTEGER, lost INTEGER, goals_for INTEGER, goals_against INTEGER, points INTEGER, collected_at TEXT DEFAULT (datetime('now')));
        CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team);
    """)
    db.commit()
    db.close()
    print("[DB] Tables ready.")