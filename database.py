import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "shield.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sport       TEXT,
            league      TEXT,
            season      TEXT,
            match_date  TEXT,
            home_team   TEXT,
            away_team   TEXT,
            home_score  INTEGER,
            away_score  INTEGER,
            status      TEXT DEFAULT 'Upcoming',
            source_url  TEXT
        );
        CREATE TABLE IF NOT EXISTS teams (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT,
            sport   TEXT,
            league  TEXT,
            country TEXT
        );
        CREATE TABLE IF NOT EXISTS players (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT,
            sport     TEXT,
            team_name TEXT
        );
    """)
    db.commit()
    db.close()
    print("[DB] Tables ready.")
