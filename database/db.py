import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ktff.db")

def get_connection(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Leagues
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leagues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT,
        tier INTEGER,
        gender TEXT DEFAULT 'male'
    );
    """)

    # 2. Seasons
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        ktff_season_id INTEGER
    );
    """)

    # 3. Clubs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE,
        city TEXT,
        stadium_name TEXT,
        president TEXT,
        phone TEXT,
        address TEXT
    );
    """)

    # Add league_name to clubs if not present
    try:
        cursor.execute("ALTER TABLE clubs ADD COLUMN league_name TEXT;")
    except sqlite3.OperationalError:
        pass

    # 4. Coaches
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coaches (
        id INTEGER PRIMARY KEY,
        ktff_coach_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        license_no TEXT,
        role TEXT,
        club_name TEXT,
        nationality TEXT,
        birth_date TEXT,
        birth_place TEXT,
        gender TEXT DEFAULT 'Erkek'
    );
    """)

    # 5. Players
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        ktff_player_id INTEGER UNIQUE,
        license_no TEXT,
        name TEXT NOT NULL,
        nationality TEXT,
        current_club TEXT,
        birth_date TEXT,
        birth_place TEXT,
        gender TEXT,
        positions TEXT,
        status TEXT
    );
    """)

    # 6. Player Career / Transfer Entries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_career (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        season TEXT,
        club_name TEXT,
        league_name TEXT,
        registration_date TEXT,
        license_status TEXT,
        FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
    );
    """)

    # 6b. Player Season Statistics (Goals, Cards, Appearances, Start 11, Subbed in, Bench)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_season_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        ktff_player_id INTEGER NOT NULL,
        season TEXT NOT NULL,
        goals INTEGER DEFAULT 0,
        yellow_cards INTEGER DEFAULT 0,
        red_cards INTEGER DEFAULT 0,
        starter_matches INTEGER DEFAULT 0,
        sub_in_matches INTEGER DEFAULT 0,
        bench_unused_matches INTEGER DEFAULT 0,
        total_played_matches INTEGER DEFAULT 0,
        total_squad_matches INTEGER DEFAULT 0,
        FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE,
        UNIQUE(ktff_player_id, season)
    );
    """)

    # Add position and photo columns to players if not present
    for col_def in [
        ("photo_url", "TEXT"),
        ("position_category", "TEXT"),
        ("primary_position", "TEXT"),
        ("position_confidence", "REAL DEFAULT 0.0"),
        ("position_source", "TEXT DEFAULT 'unassigned'")
    ]:
        try:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {col_def[0]} {col_def[1]};")
        except sqlite3.OperationalError:
            pass

    # 7. Matches
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY,
        ktff_match_id INTEGER UNIQUE,
        season TEXT,
        league_name TEXT,
        home_club TEXT,
        away_club TEXT,
        home_score INTEGER,
        away_score INTEGER,
        match_date TEXT,
        match_time TEXT,
        stadium_name TEXT,
        status TEXT,
        referee TEXT
    );
    """)

    # 8. Match Lineups (Start 11 + Bench)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_lineups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER,
        club_name TEXT,
        is_home INTEGER,
        player_name TEXT NOT NULL,
        license_no TEXT,
        shirt_number TEXT,
        is_starter INTEGER, -- 1: ilk 11, 0: yedek
        is_captain INTEGER DEFAULT 0,
        is_goalkeeper INTEGER DEFAULT 0,
        sub_in_minute INTEGER,
        sub_out_minute INTEGER,
        minutes_played INTEGER,
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
    );
    """)

    # 9. Match Events (Goals, Cards, Substitutions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER,
        club_name TEXT,
        minute INTEGER,
        event_type TEXT, -- 'goal', 'penalty', 'yellow_card', 'red_card', 'sub'
        player_name TEXT,
        detail TEXT,
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {DB_PATH}")

if __name__ == "__main__":
    init_db()
