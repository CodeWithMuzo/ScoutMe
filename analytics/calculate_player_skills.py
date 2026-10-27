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
        return 24  # default average age
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


def classify_league_tier(league_name):
    """
    Classifies a KTFF competition into one of 5 hierarchical tiers:
    - 'SUPER_LIG' : AKSA Süper Lig (A-Takım 1. Kademe)
    - 'FIRST_LIG' : AKSA 1.Lig (A-Takım 2. Kademe)
    - 'A2_SUPER'  : AKSA A2 Süper Lig (Genç/Rezerv 1. Kademe)
    - 'A2_FIRST'  : AKSA A2 1.Lig (Genç/Rezerv 2. Kademe)
    - 'U17_YOUTH' : DIGITURK KIBRIS U17 Elit Lig / Alt Yapı
    """
    lname = str(league_name or "").strip()
    if "U17" in lname or "U15" in lname or "U19" in lname:
        return "U17_YOUTH"
    if "A2" in lname:
        if "Süper" in lname or "Super" in lname:
            return "A2_SUPER"
        return "A2_FIRST"
    if "Süper" in lname or "Super" in lname:
        return "SUPER_LIG"
    if "1.Lig" in lname or "1. Lig" in lname:
        return "FIRST_LIG"
    return "FIRST_LIG"


# Competition difficulty weights:
# (skill_multiplier, goal_equivalency_weight, diff_weight)
TIER_WEIGHTS = {
    "SUPER_LIG": (1.00, 1.00, 1.00),
    "FIRST_LIG": (0.90, 0.82, 0.85),
    "A2_SUPER":  (0.62, 0.28, 0.35),
    "A2_FIRST":  (0.55, 0.22, 0.28),
    "U17_YOUTH": (0.46, 0.15, 0.20),
}


def init_skill_tables(conn):
    """Adds skill columns to players and creates/updates the player_skills table."""
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
        a_team_matches INTEGER DEFAULT 0,
        senior_minutes INTEGER DEFAULT 0,
        competition_factor REAL DEFAULT 1.0,
        updated_at TEXT,
        FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
    );
    """)

    for extra_col in [
        ("a_team_matches", "INTEGER DEFAULT 0"),
        ("senior_minutes", "INTEGER DEFAULT 0"),
        ("competition_factor", "REAL DEFAULT 1.0"),
    ]:
        try:
            cur.execute(f"ALTER TABLE player_skills ADD COLUMN {extra_col[0]} {extra_col[1]};")
        except sqlite3.OperationalError:
            pass

    conn.commit()


def calculate_skills():
    conn = get_connection()
    init_skill_tables(conn)
    cur = conn.cursor()

    print("=" * 75)
    print(" ⚡ SCOUTME: REKABET SEVİYESİ DUYARLI OYUNCU BECERİ (SKILL) MOTORU")
    print("    [ SÜPER LİG | 1. LİG | A2 SÜPER | A2 1. LİG | U17/U15 ALT YAPI ]")
    print("=" * 75)

    # 1. Load clubs to know which club is in Süper Lig vs 1. Lig
    df_clubs = pd.read_sql_query("SELECT name, league_name FROM clubs", conn)
    club_is_super = {}
    for _, crow in df_clubs.iterrows():
        cname = str(crow['name'] or '').strip()
        l_str = str(crow['league_name'] or '')
        club_is_super[cname] = ('Süper' in l_str or 'Super' in l_str)

    # 2. Load players
    df_players = pd.read_sql_query("""
        SELECT id, ktff_player_id, license_no, name, current_club, birth_date, 
               position_category, primary_position, position_confidence
        FROM players
    """, conn)
    print(f"[*] Toplam {len(df_players)} oyuncu profili yüklendi.")

    # 3. Load aggregated season statistics
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

    # 4. Load Match-level lineups with competition tier
    print("[*] Maç esame listelerinden lig kademesi (A-Takım vs A2 vs U17) analitiği yükleniyor...")
    df_lineups = pd.read_sql_query("""
        SELECT 
            l.match_id,
            l.license_no,
            l.player_name,
            l.is_starter,
            l.is_goalkeeper,
            l.minutes_played,
            l.is_home,
            m.home_score,
            m.away_score,
            m.season,
            m.league_name
        FROM match_lineups l
        JOIN matches m ON l.match_id = m.id
        WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
    """, conn)

    # 5. Load Match-level goals by player and competition tier
    df_goal_events = pd.read_sql_query("""
        SELECT 
            l.license_no,
            m.league_name,
            COUNT(*) as goal_cnt
        FROM match_events e
        JOIN matches m ON e.match_id = m.id
        JOIN match_lineups l ON e.match_id = l.match_id 
             AND LOWER(TRIM(l.player_name)) = LOWER(TRIM(e.player_name))
        WHERE e.event_type IN ('goal', 'penalty') AND l.license_no != ''
        GROUP BY l.license_no, m.league_name
    """, conn)

    goals_by_lic_tier = {}
    for _, grow in df_goal_events.iterrows():
        lic = str(grow['license_no']).strip()
        tier = classify_league_tier(grow['league_name'])
        if lic not in goals_by_lic_tier:
            goals_by_lic_tier[lic] = {"SUPER_LIG": 0, "FIRST_LIG": 0, "A2_SUPER": 0, "A2_FIRST": 0, "U17_YOUTH": 0}
        goals_by_lic_tier[lic][tier] += int(grow['goal_cnt'])

    match_metrics_by_lic = {}
    match_metrics_by_name = {}

    def _empty_metric_bucket():
        return {
            "total_match_minutes": 0,
            "senior_minutes": 0,
            "super_lig_minutes": 0,
            "first_lig_minutes": 0,
            "a2_minutes": 0,
            "u17_minutes": 0,
            "senior_matches": 0,
            "senior_starter_matches": 0,
            "a2_matches": 0,
            "u17_matches": 0,
            "team_goals_while_played": 0,
            "opp_goals_while_played": 0,
            "weighted_diff_goals": 0.0,
            "senior_opp_goals": 0,
            "clean_sheets_senior": 0,
            "clean_sheets_youth": 0,
            "match_count": 0
        }

    for _, row in df_lineups.iterrows():
        lic = str(row['license_no']).strip() if row['license_no'] else ""
        norm_n = normalize_name(row['player_name'])

        mins = row['minutes_played'] if row['minutes_played'] is not None else (90 if row['is_starter'] else 0)
        if mins <= 0:
            continue

        tier = classify_league_tier(row['league_name'])
        is_senior = tier in ("SUPER_LIG", "FIRST_LIG")
        _, _, diff_w = TIER_WEIGHTS[tier]

        team_score = row['home_score'] if row['is_home'] == 1 else row['away_score']
        opp_score = row['away_score'] if row['is_home'] == 1 else row['home_score']
        clean_sheet = 1 if (opp_score == 0 and mins >= 60) else 0

        for key_dict, key_val in [(match_metrics_by_lic, lic), (match_metrics_by_name, norm_n)]:
            if not key_val:
                continue
            if key_val not in key_dict:
                key_dict[key_val] = _empty_metric_bucket()
            st = key_dict[key_val]
            st["total_match_minutes"] += mins
            st["team_goals_while_played"] += team_score
            st["opp_goals_while_played"] += opp_score
            st["weighted_diff_goals"] += (team_score - opp_score) * diff_w
            st["match_count"] += 1

            if is_senior:
                st["senior_minutes"] += mins
                st["senior_matches"] += 1
                if row['is_starter'] == 1:
                    st["senior_starter_matches"] += 1
                st["senior_opp_goals"] += opp_score
                st["clean_sheets_senior"] += clean_sheet
                if tier == "SUPER_LIG":
                    st["super_lig_minutes"] += mins
                else:
                    st["first_lig_minutes"] += mins
            elif tier in ("A2_SUPER", "A2_FIRST"):
                st["a2_minutes"] += mins
                st["a2_matches"] += 1
                st["clean_sheets_youth"] += clean_sheet
            else:
                st["u17_minutes"] += mins
                st["u17_matches"] += 1
                st["clean_sheets_youth"] += clean_sheet

    print(f"    -> {len(match_metrics_by_lic)} lisanslı oyuncu maç esameleriyle ve lig kademeleriyle eşleştirildi.")

    # 6. Compute Competition-Calibrated 4 Attributes & Overall Rating for Every Player
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
        club = (p['current_club'] or '').strip()
        is_club_super = club_is_super.get(club, True)

        # Season stats
        st = stats_map.get(pid, None)
        if st is not None:
            starter = int(st['total_starter'])
            sub_in = int(st['total_sub_in'])
            bench = int(st['total_bench'])
            played = int(st['total_played'])
            squad = int(st['total_squad'])
            raw_total_goals = int(st['total_goals'])
            yellow = int(st['total_yellow'])
            red = int(st['total_red'])
        else:
            starter = sub_in = bench = played = squad = raw_total_goals = yellow = red = 0

        # Match lineups stats
        m_st = match_metrics_by_lic.get(lic, match_metrics_by_name.get(norm_name, None))
        if m_st:
            total_minutes = m_st["total_match_minutes"]
            senior_minutes = m_st["senior_minutes"]
            super_mins = m_st["super_lig_minutes"]
            first_mins = m_st["first_lig_minutes"]
            a2_mins = m_st["a2_minutes"]
            u17_mins = m_st["u17_minutes"]
            a_team_matches = m_st["senior_matches"]
            a2_matches = m_st["a2_matches"]
            u17_matches = m_st["u17_matches"]
            clean_sheets_senior = m_st["clean_sheets_senior"]
            clean_sheets_youth = m_st["clean_sheets_youth"]
            clean_sheets = clean_sheets_senior + clean_sheets_youth
            team_goals_match = m_st["team_goals_while_played"]
            opp_goals_match = m_st["opp_goals_while_played"]
            weighted_diff_goals = m_st["weighted_diff_goals"]
        else:
            # Player has NO appearances in our scraped 2024-2027 Senior/A2/U17 match_lineups
            total_minutes = starter * 75 + sub_in * 20
            clean_sheets = int(starter * 0.20)
            clean_sheets_senior = 0 if age <= 19 else clean_sheets
            clean_sheets_youth = clean_sheets if age <= 19 else 0
            team_goals_match = int(starter * 1.3)
            opp_goals_match = int(starter * 1.2)
            # If age <= 19 and not in match_lineups, they played in U15/U17 youth leagues
            if age <= 19:
                senior_minutes = 0
                super_mins = 0
                first_mins = 0
                a2_mins = 0
                u17_mins = total_minutes
                a_team_matches = 0
                a2_matches = 0
                u17_matches = played
                weighted_diff_goals = (team_goals_match - opp_goals_match) * 0.20
            else:
                senior_minutes = total_minutes
                super_mins = total_minutes if is_club_super else 0
                first_mins = 0 if is_club_super else total_minutes
                a2_mins = 0
                u17_mins = 0
                a_team_matches = played
                a2_matches = 0
                u17_matches = 0
                weighted_diff_goals = (team_goals_match - opp_goals_match) * (0.95 if is_club_super else 0.82)

        # -----------------------------------------------------------------
        # REKABET SEVİYESİ KATSAYISI (COMPETITION LEVEL CALIBRATION)
        # -----------------------------------------------------------------
        senior_share = senior_minutes / max(1, total_minutes)
        a2_share = a2_mins / max(1, total_minutes)
        u17_share = u17_mins / max(1, total_minutes)

        # Calculate weighted competition factor (0.42 to 1.00)
        if total_minutes > 0:
            raw_comp_factor = (
                1.00 * (super_mins / total_minutes) +
                0.90 * (first_mins / total_minutes) +
                0.56 * (a2_mins / max(1, total_minutes)) +
                0.42 * (u17_mins / max(1, total_minutes))
            )
        else:
            raw_comp_factor = 0.42 if age <= 18 else (0.55 if age <= 20 else 0.85)

        # Determine Senior Provenness & Maximum Allowed OVR Ceiling
        # Youth players playing in U15/U17/A2 cannot get Senior A-Team star ratings (75-90 OVR)
        # unless they actually play and prove themselves in Senior A-Team (AKSA Süper Lig / 1.Lig)!
        if a_team_matches == 0:
            if age <= 17 or (a2_matches == 0 and u17_matches > 0):
                # Pure U15 / U17 Academy Player
                comp_factor = min(0.50, max(0.40, raw_comp_factor))
                ovr_ceiling = 61.5
            else:
                # Pure A2 Reserve League Player (0 Senior A-Team matches)
                comp_factor = min(0.58, max(0.46, raw_comp_factor))
                ovr_ceiling = 65.5
        elif a_team_matches < 5 or senior_minutes < 270:
            # Transition player: mostly Youth/A2 with 1-4 brief A-Team appearances
            senior_exp_ratio = min(1.0, senior_minutes / 270.0)
            comp_factor = 0.56 + 0.18 * senior_exp_ratio
            ovr_ceiling = 65.5 + 4.5 * senior_exp_ratio  # Max 70.0
        elif a_team_matches < 10 or senior_minutes < 600:
            # Squad rotation player in Senior A-Team (5-9 matches)
            senior_exp_ratio = min(1.0, senior_minutes / 600.0)
            comp_factor = max(0.74, raw_comp_factor * (0.82 + 0.18 * senior_exp_ratio))
            ovr_ceiling = 76.5 if is_club_super else 74.0
        else:
            # Proven Senior A-Team player (10+ Senior matches and 600+ Senior minutes)
            # Even if they also played some A2 matches, judge them by their Senior ratio
            comp_factor = max(0.80, min(1.00, 0.78 + 0.22 * senior_share))
            if super_mins >= 450:
                ovr_ceiling = 95.0
            elif first_mins >= 450:
                ovr_ceiling = 85.5
            else:
                ovr_ceiling = 80.0

        # -----------------------------------------------------------------
        # REKABET SEVİYESİNE GÖRE DÜZELTİLMİŞ GOL VE P90 HESABI
        # -----------------------------------------------------------------
        tier_goals = goals_by_lic_tier.get(lic, None)
        if tier_goals:
            g_super = tier_goals["SUPER_LIG"]
            g_first = tier_goals["FIRST_LIG"]
            g_a2s = tier_goals["A2_SUPER"]
            g_a2f = tier_goals["A2_FIRST"]
            g_u17 = tier_goals["U17_YOUTH"]
            tracked_goals = g_super + g_first + g_a2s + g_a2f + g_u17
            untracked_goals = max(0, raw_total_goals - tracked_goals)

            # Untracked goals from season_stats: if player has 0 or low senior share, they are youth goals
            if a_team_matches == 0 or (age <= 19 and senior_share < 0.25):
                untracked_weight = 0.18 if age <= 17 else 0.25
            else:
                untracked_weight = 0.85 * senior_share + 0.25 * (1.0 - senior_share)

            senior_equiv_goals = (
                g_super * 1.00 +
                g_first * 0.82 +
                g_a2s * 0.28 +
                g_a2f * 0.22 +
                g_u17 * 0.15 +
                untracked_goals * untracked_weight
            )
        else:
            # Fallback if no event rows matched license_no
            if a_team_matches == 0:
                goal_disc = 0.16 if age <= 17 else 0.24
            elif a_team_matches < 5:
                goal_disc = 0.25 + 0.45 * senior_share
            else:
                goal_disc = 0.90 * senior_share + 0.25 * (1.0 - senior_share)
            senior_equiv_goals = raw_total_goals * goal_disc

        # Effective P90 goals (Senior-Equivalent) and raw P90 goals
        raw_p90_goals = (raw_total_goals / max(1, total_minutes)) * 90.0
        effective_p90_goals = (senior_equiv_goals / max(1, total_minutes)) * 90.0

        # Base continuity & minutes variables
        ci = (starter + 0.5 * sub_in) / max(1, squad)
        ci = min(1.0, max(0.0, ci))

        starter_ratio = starter / max(1, played)
        avg_minutes = total_minutes / max(1, played)

        # On-pitch metrics (competition-weighted)
        diff_goals_raw = team_goals_match - opp_goals_match
        on_pitch_diff_per90 = (diff_goals_raw / max(1, total_minutes)) * 90.0
        effective_diff_per90 = (weighted_diff_goals / max(1, total_minutes)) * 90.0
        goals_conceded_per90 = (opp_goals_match / max(1, total_minutes)) * 90.0

        # -------------------------------------------------------------
        # A. FİZİKSEL PUANI (0 - 100)
        # Kondisyon, A-takım maç temposu, süreklilik, biyolojik olgunluk
        # -------------------------------------------------------------
        if age <= 16:
            age_phys_factor = 0.72  # 15-16 yaş fiziksel gelişim aşamasında (A-takım sertliğine göre)
        elif age == 17:
            age_phys_factor = 0.78
        elif age == 18:
            age_phys_factor = 0.84
        elif 19 <= age <= 20:
            age_phys_factor = 0.91 + (0.05 if a_team_matches >= 10 else 0.0)
        elif 21 <= age <= 28:
            age_phys_factor = 1.00
        elif 29 <= age <= 33:
            age_phys_factor = 0.93 - (age - 28) * 0.02
        else:
            age_phys_factor = max(0.65, 0.83 - (age - 33) * 0.03)

        eff_cat = "MF" if "Kanat / Bek" in pos else cat
        pos_phys_base = {"DF": 62, "MF": 58, "FW": 58, "GK": 55}.get(eff_cat, 55)

        # Competition intensity scales physical score (playing 90 mins in U17 != 90 mins in Süper Lig)
        intensity_scale = 0.65 + 0.35 * comp_factor

        raw_physical = (
            pos_phys_base * 0.25 +
            (ci * 35.0 * intensity_scale) +
            (min(1.0, avg_minutes / 85.0) * 25.0 * intensity_scale) +
            (starter_ratio * 15.0 * intensity_scale)
        ) * age_phys_factor

        if red == 0 and a_team_matches >= 10:
            raw_physical += 2.0

        physical_score = round(max(35.0, min(95.0, min(ovr_ceiling + 4.0, raw_physical))), 1)

        # -------------------------------------------------------------
        # B. ŞUT PUANI (0 - 100)
        # Rekabet seviyesine göre ağırlıklandırılmış bitiricilik ve P90 gol
        # -------------------------------------------------------------
        if eff_cat == "FW":
            base_shoot = 46.0 + 6.0 * comp_factor
            p90_factor = min(1.0, effective_p90_goals / 0.60) * 36.0
            volume_bonus = min(8.0, senior_equiv_goals * 0.45)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        elif eff_cat == "MF":
            base_shoot = 40.0 + 5.0 * comp_factor
            p90_factor = min(1.0, effective_p90_goals / 0.32) * 35.0
            volume_bonus = min(12.0, senior_equiv_goals * 0.65)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        elif eff_cat == "DF":
            base_shoot = 32.0 + 4.0 * comp_factor
            p90_factor = min(1.0, effective_p90_goals / 0.14) * 35.0
            volume_bonus = min(15.0, senior_equiv_goals * 1.6)
            raw_shooting = base_shoot + p90_factor + volume_bonus
        else:  # GK
            raw_shooting = 25.0 + min(15.0, senior_equiv_goals * 5.0)

        if played < 3:
            raw_shooting = max(30.0, raw_shooting - 10.0)

        shooting_score = round(max(30.0, min(96.0, min(ovr_ceiling + 5.0, raw_shooting))), 1)

        # -------------------------------------------------------------
        # C. TEKNİK PUANI (0 - 100)
        # Oyun kurma, rekabet düzeltmeli saha içi averaj katkısı, top hakimiyeti
        # -------------------------------------------------------------
        pos_tech_base = {"MF": 60, "FW": 56, "DF": 47, "GK": 38}.get(eff_cat, 50)
        if "10 Numara" in pos or "Kanat" in pos or "Ofansif" in pos:
            pos_tech_base += 5.0
        elif "Ön Libero" in pos:
            pos_tech_base += 2.0

        # Scale base technical by competition level
        scaled_tech_base = pos_tech_base * (0.72 + 0.28 * comp_factor)

        # Competition-weighted on-pitch differential contribution
        diff_contrib = max(-10.0, min(18.0, effective_diff_per90 * 11.0))

        card_rate = (yellow + red * 2) / max(1, played)
        if card_rate <= 0.12 and played >= 10:
            clean_bonus = 5.0 * comp_factor
        elif card_rate <= 0.20 and played >= 5:
            clean_bonus = 2.5 * comp_factor
        else:
            clean_bonus = 0.0

        raw_technical = scaled_tech_base + diff_contrib + clean_bonus
        if played < 3:
            raw_technical = max(35.0, raw_technical - 8.0)

        technical_score = round(max(35.0, min(95.0, min(ovr_ceiling + 4.0, raw_technical))), 1)

        # -------------------------------------------------------------
        # D. DEFANS PUANI (0 - 100)
        # Pozisyon alma, kademe, A-takım clean sheet, az gol yeme
        # -------------------------------------------------------------
        pos_def_base = {"DF": 66, "GK": 61, "MF": 50, "FW": 33}.get(eff_cat, 45)
        if "Stoper" in pos or ("Bek" in pos and "Kanat / Bek" not in pos):
            pos_def_base += 4.0

        scaled_def_base = pos_def_base * (0.72 + 0.28 * comp_factor)

        if played >= 5:
            if goals_conceded_per90 <= 0.90:
                concede_bonus = 12.0 * comp_factor
            elif goals_conceded_per90 <= 1.30:
                concede_bonus = 6.0 * comp_factor
            elif goals_conceded_per90 >= 2.20:
                concede_bonus = -8.0
            else:
                concede_bonus = 0.0
        else:
            concede_bonus = 0.0

        # Senior clean sheets worth 1.5, youth clean sheets worth 0.45
        effective_cs = clean_sheets_senior * 1.5 + clean_sheets_youth * 0.45
        cs_bonus = min(11.0 * comp_factor, effective_cs)

        xi_stability = starter_ratio * 8.0 * comp_factor

        if 0.10 <= card_rate <= 0.28 and red == 0 and eff_cat in ["DF", "MF"]:
            tackle_bonus = 4.0 * comp_factor
        else:
            tackle_bonus = 0.0

        raw_defending = scaled_def_base + concede_bonus + cs_bonus + xi_stability + tackle_bonus
        if played < 3:
            raw_defending = max(30.0, raw_defending - 8.0)

        defending_score = round(max(30.0, min(96.0, min(ovr_ceiling + 4.0, raw_defending))), 1)

        # -------------------------------------------------------------
        # E. GENEL REYTİNG (OVERALL RATING: 0 - 100)
        # Mevki ağırlıklı kompozit reyting + Rekabet Seviyesi Tavanı
        # -------------------------------------------------------------
        if eff_cat == "GK":
            overall = defending_score * 0.45 + physical_score * 0.35 + technical_score * 0.15 + shooting_score * 0.05
        elif eff_cat == "DF":
            overall = defending_score * 0.45 + physical_score * 0.30 + technical_score * 0.15 + shooting_score * 0.10
        elif eff_cat == "MF":
            overall = technical_score * 0.35 + physical_score * 0.25 + defending_score * 0.20 + shooting_score * 0.20
        else:  # FW
            overall = shooting_score * 0.45 + physical_score * 0.25 + technical_score * 0.25 + defending_score * 0.05

        overall_rating = round(max(40.0, min(ovr_ceiling, overall)), 1)

        # Store effective P90 goals for Senior comparison while preserving raw_total_goals
        records_to_insert.append((
            pid, ktff_pid, pname, cat, pos, age, club,
            physical_score, shooting_score, technical_score, defending_score, overall_rating,
            round(ci, 2), round(starter_ratio, 2), round(avg_minutes, 1),
            round(effective_p90_goals, 2), raw_total_goals, round(raw_total_goals / max(1, 40), 2),
            round(effective_diff_per90, 2), round(goals_conceded_per90, 2),
            clean_sheets, played, squad, total_minutes,
            a_team_matches, senior_minutes, round(comp_factor, 3), now_str
        ))

        updates_for_players.append((
            physical_score, shooting_score, technical_score, defending_score, overall_rating, pid
        ))

    # Batch insert into player_skills
    print(f"\n[*] {len(records_to_insert)} oyuncu için rekabet düzeltmeli beceri puanları 'player_skills' tablosuna yazılıyor...")
    cur.execute("DELETE FROM player_skills;")
    cur.executemany("""
        INSERT INTO player_skills (
            player_id, ktff_player_id, name, position_category, primary_position, age, current_club,
            physical_score, shooting_score, technical_score, defending_score, overall_rating,
            ci_continuity_index, starter_ratio, avg_minutes_played,
            p90_goals, total_goals, goal_share,
            on_pitch_diff_per90, goals_conceded_per90,
            clean_sheets, total_played_matches, total_squad_matches, total_minutes_played,
            a_team_matches, senior_minutes, competition_factor, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
    print("[✓] Tüm beceri puanları rekabet seviyesine göre başarıyla hesaplandı!")

    # Print Summary Report
    print("\n" + "=" * 75)
    print(" 📊 SCOUTME REKABET SEVİYESİNE GÖRE REYTİNG DAĞILIM RAPORU")
    print("=" * 75)

    df_senior = pd.read_sql_query("SELECT * FROM player_skills WHERE a_team_matches >= 5", conn)
    df_youth_only = pd.read_sql_query("SELECT * FROM player_skills WHERE a_team_matches = 0 AND total_played_matches >= 5", conn)
    print(f"A-Takım Deneyimli Oyuncu Sayısı (>=5 A-Takım Maçı) : {len(df_senior)} | Ortalama OVR: {df_senior['overall_rating'].mean():.1f} (Max: {df_senior['overall_rating'].max()})")
    print(f"Sadece Genç/A2/U17 Ligi Oynayan Oyuncu Sayısı      : {len(df_youth_only)} | Ortalama OVR: {df_youth_only['overall_rating'].mean():.1f} (Max: {df_youth_only['overall_rating'].max()})")

    print("\n[+] Mevki Bazlı En Yüksek Reytingli A-Takım Oyuncuları:")
    for cat in ["FW", "MF", "DF", "GK"]:
        top = cur.execute("""
            SELECT name, age, current_club, a_team_matches, physical_score, shooting_score, technical_score, defending_score, overall_rating
            FROM player_skills
            WHERE position_category = ? AND a_team_matches >= 10
            ORDER BY overall_rating DESC
            LIMIT 3
        """, (cat,)).fetchall()
        print(f"\n  --- {cat} (Top 3 A-Takım) ---")
        for r in top:
            print(f"  • {r[0]:<24} ({r[1]}y) | {r[2]:<22} | A-Maç: {r[3]:<2} | OVR: {r[8]} | FİZ:{r[4]} ŞUT:{r[5]} TEK:{r[6]} DEF:{r[7]}")

    conn.close()


if __name__ == "__main__":
    calculate_skills()
