CREATE TABLE leagues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT,
        tier INTEGER,
        gender TEXT DEFAULT 'male'
    );

CREATE TABLE seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        ktff_season_id INTEGER
    );

CREATE TABLE clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE,
        city TEXT,
        stadium_name TEXT,
        president TEXT,
        phone TEXT,
        address TEXT
    );

CREATE TABLE coaches (
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

CREATE TABLE players (
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
    , photo_url TEXT);

CREATE TABLE player_career (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        season TEXT,
        club_name TEXT,
        league_name TEXT,
        registration_date TEXT,
        license_status TEXT,
        FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
    );

CREATE TABLE matches (
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

CREATE TABLE match_lineups (
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

CREATE TABLE match_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER,
        club_name TEXT,
        minute INTEGER,
        event_type TEXT, -- 'goal', 'penalty', 'yellow_card', 'red_card', 'sub'
        player_name TEXT,
        detail TEXT,
        FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE
    );

CREATE TABLE player_season_stats (
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