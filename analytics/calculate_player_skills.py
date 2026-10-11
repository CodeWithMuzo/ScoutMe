import sys
import os
import re
import math
import sqlite3
import datetime
import numpy as np
import pandas as pd

# Ensure UTF-8 console output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection

def parse_birth_year(birth_date_str):
    """Extracts birth year and calculates age as of 2026."""
    if not birth_date_str:
        return 24 # default average age
    m = re.search(r"(\d{4})", birth_date_str)
    if m:
        year = int(m.group(1))
        return max(15, min(45, 2026 - year))
    return 24

def normalize_name(text):
    if not text:
        return ""
    text = text.upper()
    replacements = {
        'İ': 'I', 'I': 'I', 'ı': 'I', 'i': 'I',
        'Ğ': 'G', 'ğ': 'G',
        'Ü': 'U', 'ü': 'U',
        'Ş': 'S', 'ş': 'S',
        'Ö': 'O', 'ö': 'O',
        'Ç': 'C', 'ç': 'C'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    return " ".join(text.split())

def init_skill_tables(conn):
    """Adds skill columns to players and creates the player_skills table."""
    cur = conn.cursor()
    
    # 1. Add skill columns to players if not present
    for col in [
        ("skill_physical", "REAL DEFAULT 50.0"),
        ("skill_shooting", "REAL DEFAULT 50.0"),
        ("skill_technical", "REAL DEFAULT 50.0"),
        ("skill_defending", "REAL DEFAULT 50.0"),
        ("skill_overall", "REAL DEFAULT 50.0")
    ]:
        try:
            cur.execute(f"ALTER TABLE players ADD COLUMN {col[0]} {col[1]};")
        except sqlite3.OperationalError:
            pass

    # 2. Detailed player_skills table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_skills (
        player_id INTEGER PRIMARY KEY,
        ktff_player_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        position_category TEXT,
        primary_position TEXT,
        age INTEGER,
        current_club TEXT,
        physical_score REAL,
        shooting_score REAL,
        technical_score REAL,
        defending_score REAL,
        overall_rating REAL,
        ci_continuity_index REAL,
        starter_ratio REAL,
        avg_minutes_played REAL,
        p90_goals REAL,
        total_goals INTEGER,
        goal_share REAL,
        on_pitch_diff_per90 REAL,
        goals_conceded_per90 REAL,
        clean_sheets INTEGER,
        total_played_matches INTEGER,
        total_squad_matches INTEGER,
        total_minutes_played INTEGER,
        updated_at TEXT,
        FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
    );
    """)
    conn.commit()

def calculate_skills():
    conn = get_connection()
    init_skill_tables(conn)
    cur = conn.cursor()

    print("=" * 70)
    print(" ⚡ SCOUTME: OYUNCU BECERİ (SKILL) MOTORU VE FORMÜL HESAPLAYICI")
    print("    [ FİZİKSEL | ŞUT | TEKNİK | DEFANS | GENEL REYTİNG ]")
    print("=" * 70)

    # 1. Load players
    df_players = pd.read_sql_query("""
        SELECT id, ktff_player_id, license_no, name, current_club, birth_date, 
               position_category, primary_position, position_confidence
        FROM players
    """, conn)
    print(f"[*] Toplam {len(df_players)} oyuncu profili yüklendi.")

    # 2. Load aggregated season statistics
    df_stats = pd.read_sql_query("""
        SELECT 
            player_id,
            SUM(starter_matches) as total_starter,
            SUM(sub_in_matches) as total_sub_in,
            SUM(bench_unused_matches) as total_bench,
            SUM(total_played_matches) as total_played,
            SUM(total_squad_matches) as total_squad,
            SUM(goals) as total_goals,
            SUM(yellow_cards) as total_yellow,
            SUM(red_cards) as total_red
        FROM player_season_stats
        GROUP BY player_id
    """, conn)
    
    stats_map = {row['player_id']: row for _, row in df_stats.iterrows()}

    # 3. Load Match-level lineups & on-pitch stats
    print("[*] Maç esame listelerinden saha içi averaj ve dakika analitiği yükleniyor...")
    df_lineups = pd.read_sql_query("""
        SELECT 
            l.license_no,
            l.player_name,
            l.is_starter,
            l.is_goalkeeper,
            l.minutes_played,
            l.is_home,
            m.home_score,
            m.away_score,
            m.season
        FROM match_lineups l
        JOIN matches m ON l.match_id = m.id
        WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
    """, conn)

    # Aggregate match metrics per license_no or normalized player_name
    match_metrics_by_lic = {}
    match_metrics_by_name = {}

    for _, row in df_lineups.iterrows():
        lic = str(row['license_no']).strip() if row['license_no'] else ""
        norm_n = normalize_name(row['player_name'])
        
        mins = row['minutes_played'] if row['minutes_played'] is not None else (90 if row['is_starter'] else 0)
        if mins <= 0:
            continue

        team_score = row['home_score'] if row['is_home'] == 1 else row['away_score']
        opp_score = row['away_score'] if row['is_home'] == 1 else row['home_score']
        clean_sheet = 1 if (opp_score == 0 and mins >= 60) else 0

        for key_dict, key_val in [(match_metrics_by_lic, lic), (match_metrics_by_name, norm_n)]:
            if not key_val:
                continue
            if key_val not in key_dict:
                key_dict[key_val] = {
                    "total_match_minutes": 0,
                    "team_goals_while_played": 0,
                    "opp_goals_while_played": 0,
                    "clean_sheets": 0,
                    "match_count": 0
                }
            st = key_dict[key_val]
            st["total_match_minutes"] += mins
            st["team_goals_while_played"] += team_score
            st["opp_goals_while_played"] += opp_score
            st["clean_sheets"] += clean_sheet
            st["match_count"] += 1

    print(f"    -> {len(match_metrics_by_lic)} lisanslı oyuncu maç esameleriyle eşleştirildi.")

    # 4. Compute 4 Attributes for Every Player
    records_to_insert = []
    updates_for_players = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, p in df_players.iterrows():
        pid = p['id']
        ktff_pid = p['ktff_player_id']
        lic = str(p['license_no']).strip() if p['license_no'] else ""
        pname = p['name']
        norm_name = normalize_name(pname)
        cat = p['position_category'] or 'MF'
        pos = p['primary_position'] or 'Orta Saha'
        age = parse_birth_year(p['birth_date'])
        club = p['current_club']

        # Season stats
        st = stats_map.get(pid, None)
        if st is not None:
            starter = int(st['total_starter'])
            sub_in = int(st['total_sub_in'])
            bench = int(st['total_bench'])
            played = int(st['total_played'])
            squad = int(st['total_squad'])
            goals = int(st['total_goals'])
            yellow = int(st['total_yellow'])
            red = int(st['total_red'])
        else:
            starter = sub_in = bench = played = squad = goals = yellow = red = 0

        # Match lineups stats
        m_st = match_metrics_by_lic.get(lic, match_metrics_by_name.get(norm_name, None))
        if m_st:
            total_minutes = m_st["total_match_minutes"]
            clean_sheets = m_st["clean_sheets"]
            team_goals_match = m_st["team_goals_while_played"]
            opp_goals_match = m_st["opp_goals_while_played"]
        else:
            # Fallback estimation based on starter and sub_in matches
            total_minutes = starter * 85 + sub_in * 25
            clean_sheets = int(starter * 0.25)
            team_goals_match = int(starter * 1.5)
            opp_goals_match = int(starter * 1.2)

        # Base variables
        ci = (starter + 0.5 * sub_in) / max(1, squad)
        ci = min(1.0, max(0.0, ci))
        
        starter_ratio = starter / max(1, played)
        avg_minutes = total_minutes / max(1, played)
        p90_goals = (goals / max(1, total_minutes)) * 90.0

        # On-pitch metrics
        diff_goals = team_goals_match - opp_goals_match
        on_pitch_diff_per90 = (diff_goals / max(1, total_minutes)) * 90.0
        goals_conceded_per90 = (opp_goals_match / max(1, total_minutes)) * 90.0

        # -------------------------------------------------------------
        # A. FİZİKSEL PUANI (0 - 100)
        # Kondisyon, maç süresi, süreklilik, yaş dinamiği
        # -------------------------------------------------------------
        # Age factor: Peak at 21-27 (1.0), gentle decay down to 0.70 at 38
        if age <= 20:
            age_factor = 0.90 + min(0.10, played * 0.01)
        elif 21 <= age <= 28:
            age_factor = 1.00
        elif 29 <= age <= 33:
            age_factor = 0.93 - (age - 28) * 0.02
        else:
            age_factor = max(0.65, 0.83 - (age - 33) * 0.03)

        # Baseline physical by position
        pos_phys_base = {"DF": 62, "MF": 58, "FW": 58, "GK": 55}.get(cat, 55)

        # Experience / match volume scaling
        volume_factor = min(1.0, played / 25.0) # Full confidence after 25 games
        
        raw_physical = (
            pos_phys_base * 0.25 +
            (ci * 35.0) +
            (min(1.0, avg_minutes / 85.0) * 25.0) +
            (starter_ratio * 15.0)
        ) * age_factor

        # Small bonus for low red cards (physical self-control)
        if red == 0 and played >= 10:
            raw_physical += 2.0

        physical_score = round(max(35.0, min(95.0, raw_physical)), 1)

        # -------------------------------------------------------------
        # B. ŞUT PUANI (0 - 100)
        # Bitiricilik, P90 gol sıklığı, gol beklenti aşımı
        # -------------------------------------------------------------
        if cat == "FW":
            # For forwards: 0.60 P90 goals is elite (~90+)
            base_shoot = 52.0
            p90_factor = min(1.0, p90_goals / 0.65) * 36.0
            volume_bonus = min(8.0, goals * 0.4)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        elif cat == "MF":
            # For midfielders: 0.30 P90 goals is elite
            base_shoot = 45.0
            p90_factor = min(1.0, p90_goals / 0.35) * 35.0
            volume_bonus = min(12.0, goals * 0.6)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        elif cat == "DF":
            # For defenders: headers, set pieces (0.10 P90 is very high)
            base_shoot = 35.0
            p90_factor = min(1.0, p90_goals / 0.15) * 35.0
            volume_bonus = min(15.0, goals * 1.5)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        else: # GK
            raw_shooting = 25.0 + min(15.0, goals * 5.0)

        # Inactive penalty
        if played < 3:
            raw_shooting = max(30.0, raw_shooting - 10.0)

        shooting_score = round(max(30.0, min(96.0, raw_shooting)), 1)

        # -------------------------------------------------------------
        # C. TEKNİK PUANI (0 - 100)
        # Oyun kurma, saha içi skor üretkenliği, az kartla top hakimiyeti
        # -------------------------------------------------------------
        pos_tech_base = {"MF": 62, "FW": 58, "DF": 48, "GK": 38}.get(cat, 50)
        if "10 Numara" in pos or "Kanat" in pos or "Ofansif" in pos:
            pos_tech_base += 6.0
        elif "Ön Libero" in pos:
            pos_tech_base += 2.0

        # On-pitch differential contribution
        # Positive diff gives up to +18 points; negative subtracts up to -10
        diff_contrib = max(-10.0, min(18.0, on_pitch_diff_per90 * 10.0))

        # Clean play & ball control: many games played with low card rate
        card_rate = (yellow + red * 2) / max(1, played)
        if card_rate <= 0.12 and played >= 10:
            clean_bonus = 6.0
        elif card_rate <= 0.20 and played >= 5:
            clean_bonus = 3.0
        else:
            clean_bonus = 0.0

        raw_technical = pos_tech_base + diff_contrib + clean_bonus
        if played < 3:
            raw_technical = max(35.0, raw_technical - 8.0)

        technical_score = round(max(35.0, min(95.0, raw_technical)), 1)

        # -------------------------------------------------------------
        # D. DEFANS PUANI (0 - 100)
        # Pozisyon alma, kademe, clean sheet, az gol yeme, taktik faul
        # -------------------------------------------------------------
        pos_def_base = {"DF": 68, "GK": 62, "MF": 52, "FW": 34}.get(cat, 45)
        if "Stoper" in pos or "Bek" in pos:
            pos_def_base += 4.0

        # Goals conceded impact: < 1.0 per 90 is elite
        if played >= 5:
            if goals_conceded_per90 <= 0.90:
                concede_bonus = 12.0
            elif goals_conceded_per90 <= 1.30:
                concede_bonus = 6.0
            elif goals_conceded_per90 >= 2.20:
                concede_bonus = -8.0
            else:
                concede_bonus = 0.0
        else:
            concede_bonus = 0.0

        # Clean sheet impact
        cs_bonus = min(10.0, clean_sheets * 1.5)

        # Defensive reliability: coach keeps them in starting XI
        xi_stability = starter_ratio * 8.0

        # Controlled aggressiveness
        if 0.10 <= card_rate <= 0.28 and red == 0 and cat in ["DF", "MF"]:
            tackle_bonus = 4.0
        else:
            tackle_bonus = 0.0

        raw_defending = pos_def_base + concede_bonus + cs_bonus + xi_stability + tackle_bonus
        if played < 3:
            raw_defending = max(30.0, raw_defending - 8.0)

        defending_score = round(max(30.0, min(96.0, raw_defending)), 1)

        # -------------------------------------------------------------
        # E. GENEL REYTİNG (OVERALL RATING: 0 - 100)
        # Mevki ağırlıklı kompozit reyting (FIFA / FM formülü)
        # -------------------------------------------------------------
        if cat == "GK":
            overall = defending_score * 0.45 + physical_score * 0.35 + technical_score * 0.15 + shooting_score * 0.05
        elif cat == "DF":
            overall = defending_score * 0.45 + physical_score * 0.30 + technical_score * 0.15 + shooting_score * 0.10
        elif cat == "MF":
            overall = technical_score * 0.35 + physical_score * 0.25 + defending_score * 0.20 + shooting_score * 0.20
        else: # FW
            overall = shooting_score * 0.45 + physical_score * 0.25 + technical_score * 0.25 + defending_score * 0.05

        overall_rating = round(max(40.0, min(96.0, overall)), 1)

        # Add to batch collections
        records_to_insert.append((
            pid, ktff_pid, pname, cat, pos, age, club,
            physical_score, shooting_score, technical_score, defending_score, overall_rating,
            round(ci, 2), round(starter_ratio, 2), round(avg_minutes, 1),
            round(p90_goals, 2), goals, round(goals / max(1, 40), 2),
            round(on_pitch_diff_per90, 2), round(goals_conceded_per90, 2),
            clean_sheets, played, squad, total_minutes, now_str
        ))

        updates_for_players.append((
            physical_score, shooting_score, technical_score, defending_score, overall_rating, pid
        ))

    # Batch insert into player_skills
    print(f"\n[*] {len(records_to_insert)} oyuncu için beceri puanları 'player_skills' tablosuna yazılıyor...")
    cur.execute("DELETE FROM player_skills;")
    cur.executemany("""
        INSERT INTO player_skills (
            player_id, ktff_player_id, name, position_category, primary_position, age, current_club,
            physical_score, shooting_score, technical_score, defending_score, overall_rating,
            ci_continuity_index, starter_ratio, avg_minutes_played,
            p90_goals, total_goals, goal_share,
            on_pitch_diff_per90, goals_conceded_per90,
            clean_sheets, total_played_matches, total_squad_matches, total_minutes_played, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, records_to_insert)

    # Batch update players table
    print("[*] 'players' tablosundaki beceri sütunları güncelleniyor...")
    cur.executemany("""
        UPDATE players SET
            skill_physical = ?,
            skill_shooting = ?,
            skill_technical = ?,
            skill_defending = ?,
            skill_overall = ?
        WHERE id = ?;
    """, updates_for_players)

    conn.commit()
    print("[✓] Tüm beceri puanları ve radar profilleri başarıyla hesaplandı!")

    # Print Summary Report
    print("\n" + "=" * 70)
    print(" 📊 SCOUTME 4 TEMEL ÖZELLİK VE REYTİNG DAĞILIM RAPORU")
    print("=" * 70)
    
    df_res = pd.read_sql_query("SELECT * FROM player_skills WHERE total_played_matches >= 5", conn)
    print(f"En az 5 maç oynamış aktif oyuncu sayısı: {len(df_res)}")
    print("\nOrtalama Puanlar (Aktif Oyuncular):")
    print(f"  • Fiziksel Ortalama : {df_res['physical_score'].mean():.1f} (Min: {df_res['physical_score'].min()}, Max: {df_res['physical_score'].max()})")
    print(f"  • Şut Ortalama      : {df_res['shooting_score'].mean():.1f} (Min: {df_res['shooting_score'].min()}, Max: {df_res['shooting_score'].max()})")
    print(f"  • Teknik Ortalama   : {df_res['technical_score'].mean():.1f} (Min: {df_res['technical_score'].min()}, Max: {df_res['technical_score'].max()})")
    print(f"  • Defans Ortalama   : {df_res['defending_score'].mean():.1f} (Min: {df_res['defending_score'].min()}, Max: {df_res['defending_score'].max()})")
    print(f"  • Genel Reyting     : {df_res['overall_rating'].mean():.1f} (Min: {df_res['overall_rating'].min()}, Max: {df_res['overall_rating'].max()})")

    print("\n[+] Mevki Bazlı En Yüksek Reytingli Örnek Oyuncular:")
    for cat in ["FW", "MF", "DF", "GK"]:
        top = cur.execute("""
            SELECT name, current_club, primary_position, physical_score, shooting_score, technical_score, defending_score, overall_rating
            FROM player_skills
            WHERE position_category = ? AND total_played_matches >= 15
            ORDER BY overall_rating DESC
            LIMIT 3
        """, (cat,)).fetchall()
        print(f"\n  --- {cat} (Top 3) ---")
        for r in top:
            print(f"  • {r[0]:<22} | {r[1]:<20} | OVR: {r[7]} | FİZ: {r[3]:<4} ŞUT: {r[4]:<4} TEK: {r[5]:<4} DEF: {r[6]:<4}")

    conn.close()

if __name__ == "__main__":
    calculate_skills()
