import sys
import os
import re
import urllib.request
import sqlite3
import unicodedata
from bs4 import BeautifulSoup
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Ensure UTF-8 console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, init_db

def normalize_name(text):
    """Normalizes Turkish characters and punctuation for robust matching."""
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

TM_CLUBS = {
    "Magusa Turk Gucu": 41658,
    "Cihangir GSK": 21466,
    "Dogan Turk Birligi": 66181,
    "Yenicami AK": 41333,
    "Cetinkaya TSK": 24921,
    "Lefke TSK": 53883,
    "Kucuk Kaymakli TSK": 42079,
    "Gonyeli SK": 46889,
    "Alsancak Yesilova SK": 76451,
    "Dumlupinar TSK": 53884,
    "Degirmenlik SK": 76058,
    "Gocmenkoy IYSK": 76055,
    "Hamitkoy SHSK": 81577,
    "Turk Ocagi Limasol SK": 41457,
    "Mesarya SK": 76318,
    "Baf Ulku Yurdu": 62578,
    "Genclik Gucu TSK": 42055,
}

VERIFIED_EXPERT_OVERRIDES = {
    "EMRE KARACIGER": {
        "category": "DF",
        "primary_position": "Kanat / Bek (Winger / Fullback)"
    }
}

def map_tm_position(pos_str):
    """Maps detailed Turkish Transfermarkt positions to standard category and role."""
    pos_str = pos_str.strip()
    category = "MF"
    if "Kaleci" in pos_str:
        return "GK", "Kaleci"
    elif any(d in pos_str for d in ["Stoper", "Bek", "Defans"]):
        category = "DF"
    elif any(f in pos_str for d in ["Santrafor", "Kanat", "Forvet"] for f in [d]):
        category = "FW"
    elif any(m in pos_str for m in ["Orta Saha", "Libero", "On Numara"]):
        category = "MF"
    return category, pos_str

def scrape_transfermarkt_squad_urls(club_name, club_id):
    """Scrapes player names and verified positions from Transfermarkt across recent seasons."""
    urls = [
        f"https://www.transfermarkt.com.tr/{club_id}/kader/verein/{club_id}/saison_id/2024/plus/1",
        f"https://www.transfermarkt.com.tr/{club_id}/kader/verein/{club_id}/saison_id/2023/plus/1",
        f"https://www.transfermarkt.com.tr/{club_id}/kader/verein/{club_id}",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    players = {}
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="items")
            if not table:
                continue
                
            rows = table.find_all("tr", class_=["odd", "even"])
            for r in rows:
                name_td = r.find("td", class_="hauptlink")
                if not name_td:
                    continue
                name = name_td.get_text(strip=True)
                
                pos_tds = r.find_all("td")
                pos_text = ""
                if len(pos_tds) >= 2:
                    sub_tables = pos_tds[1].find_all("tr")
                    if sub_tables:
                        pos_text = sub_tables[-1].get_text(strip=True)
                    else:
                        pos_text = pos_tds[1].get_text(strip=True)
                
                norm = normalize_name(name)
                if norm and pos_text and norm not in players:
                    cat, primary = map_tm_position(pos_text)
                    players[norm] = {
                        "raw_name": name,
                        "norm_name": norm,
                        "tm_position": pos_text,
                        "category": cat,
                        "primary_position": primary,
                        "club": club_name
                    }
        except Exception:
            pass
            
    return list(players.values())

def fetch_all_transfermarkt_players():
    """Scrapes verified squad positions for all defined KTFF Super Lig clubs."""
    print("[*] Tier 1: Scraping verified positions from Transfermarkt KTFF clubs...")
    all_tm_players = {}
    for club_name, club_id in TM_CLUBS.items():
        squad = scrape_transfermarkt_squad_urls(club_name, club_id)
        for p in squad:
            all_tm_players[p["norm_name"]] = p
        print(f"    + {club_name:<24}: {len(squad)} verified players")
    print(f"[+] Total verified unique Transfermarkt players collected: {len(all_tm_players)}")
    return all_tm_players

def run_position_inference():
    """
    Executes the 4-tier position inference and enrichment pipeline:
    1. Transfermarkt External Entity Matching (Gold Standard)
    2. KTFF Match Sheet Lineup Goalkeeper ('KL') and Shirt Flags
    3. Multi-Feature Statistical Heuristics (Goal ratio, start ratio, cards)
    4. Unsupervised ML Clustering (K-Means) for validation
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    
    print("=" * 65)
    print("      🎯 SCOUTME POSITION INFERENCE & ENRICHMENT PIPELINE     ")
    print("=" * 65)
    
    # Step 1: Transfermarkt Data
    tm_players = fetch_all_transfermarkt_players()
    
    # Step 2: Fetch GK flags and shirt modes from match lineups
    print("\n[*] Tier 2: Analyzing KTFF match lineups for KL (Kaleci) flags and shirt numbers...")
    lineup_rows = cur.execute("""
        SELECT lower(trim(player_name)) as p_name, license_no, shirt_number, is_goalkeeper
        FROM match_lineups
    """).fetchall()
    
    gk_names = set()
    gk_licenses = set()
    player_shirts = {}
    
    for r in lineup_rows:
        norm = normalize_name(r["p_name"])
        lic = r["license_no"].strip()
        shirt = r["shirt_number"].strip()
        is_gk = r["is_goalkeeper"]
        
        if is_gk == 1:
            if norm: gk_names.add(norm)
            if lic: gk_licenses.add(lic)
            
        if norm and shirt.isdigit():
            player_shirts.setdefault(norm, []).append(shirt)
            
    print(f"[+] Found {len(gk_names)} distinct goalkeepers directly tagged with 'KL' in match sheets.")

    # Step 3: Fetch all player statistics from SQLite
    print("\n[*] Tier 3: Calculating statistical profiles for all 2,404 players...")
    query = """
        SELECT 
            p.id, p.ktff_player_id, p.license_no, p.name, p.current_club, p.birth_date,
            COALESCE(sum(s.goals), 0) as total_goals,
            COALESCE(sum(s.total_played_matches), 0) as total_played,
            COALESCE(sum(s.starter_matches), 0) as starter_matches,
            COALESCE(sum(s.sub_in_matches), 0) as sub_in_matches,
            COALESCE(sum(s.bench_unused_matches), 0) as bench_matches,
            COALESCE(sum(s.yellow_cards), 0) as yellow_cards,
            COALESCE(sum(s.red_cards), 0) as red_cards,
            COALESCE(max(s.goals), 0) as max_season_goals,
            count(s.season) as seasons_count
        FROM players p
        LEFT JOIN player_season_stats s ON p.id = s.player_id
        GROUP BY p.id
    """
    players = [dict(r) for r in cur.execute(query).fetchall()]
    
    # Feature matrix for unsupervised clustering (K-Means)
    feature_list = []
    
    updates = []
    category_counts = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
    source_counts = {}

    for p in players:
        p_id = p["id"]
        p_name = p["name"]
        norm_name = normalize_name(p_name)
        lic = (p["license_no"] or "").strip()
        
        played = p["total_played"]
        goals = p["total_goals"]
        starters = p["starter_matches"]
        sub_in = p["sub_in_matches"]
        yellow = p["yellow_cards"]
        red = p["red_cards"]
        max_s_goals = p["max_season_goals"]
        
        gpm = goals / max(1, played) if played > 0 else 0.0
        starter_rate = starters / max(1, played) if played > 0 else 0.0
        sub_rate = sub_in / max(1, played) if played > 0 else 0.0
        cpm = (yellow + 2 * red) / max(1, played) if played > 0 else 0.0
        
        feature_list.append([gpm, starter_rate, sub_rate, cpm, played])
        
        # Most frequent shirt number
        shirts = player_shirts.get(norm_name, [])
        mode_shirt = max(set(shirts), key=shirts.count) if shirts else ""

        cat = None
        primary_pos = None
        conf = 0.0
        source = None

        # --- RULE 0: Verified Expert Domain Overrides ---
        if norm_name in VERIFIED_EXPERT_OVERRIDES:
            ov = VERIFIED_EXPERT_OVERRIDES[norm_name]
            cat = ov["category"]
            primary_pos = ov["primary_position"]
            conf = 0.99
            source = "expert_verified"

        # --- RULE 1: Transfermarkt Gold-Standard Match ---
        elif norm_name in tm_players:
            tm_info = tm_players[norm_name]
            cat = tm_info["category"]
            primary_pos = tm_info["primary_position"]
            conf = 0.98
            source = "transfermarkt_verified"

        # --- RULE 2: KTFF Match Sheet Goalkeeper Flag ---
        elif norm_name in gk_names or (lic and lic in gk_licenses) or (mode_shirt == "1" and goals == 0 and played >= 5):
            cat = "GK"
            primary_pos = "Kaleci"
            conf = 0.99 if (norm_name in gk_names or lic in gk_licenses) else 0.90
            source = "match_sheet_kl" if (norm_name in gk_names or lic in gk_licenses) else "shirt_number_gk"

        # --- RULE 3: Definite High Scorer / Striker (FW) ---
        elif goals >= 15 or (goals >= 6 and gpm >= 0.28) or (max_s_goals >= 8 and gpm >= 0.25):
            cat = "FW"
            if gpm >= 0.45 or goals >= 25:
                primary_pos = "Santrafor (Striker)"
                conf = 0.95
            elif mode_shirt in ["7", "11"]:
                primary_pos = "Kanat Forvet (Winger)"
                conf = 0.90
            else:
                primary_pos = "Hücum / Forvet (Forward)"
                conf = 0.88
            source = "statistical_goals"

        # --- RULE 4: Low Scorer, High Starter & Cards / Classic Defender (DF) ---
        elif played >= 8 and goals <= 2 and gpm <= 0.05 and (starter_rate >= 0.65 or cpm >= 0.12 or mode_shirt in ["2", "3", "4", "5"]):
            cat = "DF"
            if mode_shirt in ["2", "3"]:
                primary_pos = "Bek (Fullback)"
                conf = 0.85
            elif mode_shirt in ["4", "5"]:
                primary_pos = "Stoper (Centerback)"
                conf = 0.88
            else:
                primary_pos = "Defans (Defender)"
                conf = 0.82
            source = "statistical_defense"

        # --- RULE 5: Midfield Distribution Profile (MF) ---
        elif played >= 5:
            cat = "MF"
            if gpm >= 0.10 or goals >= 3:
                primary_pos = "Ofansif / Merkez Orta Saha (CM/CAM)"
                conf = 0.82
            elif mode_shirt in ["6", "8"]:
                primary_pos = "Merkez / Defansif Orta Saha (CM/CDM)"
                conf = 0.82
            elif mode_shirt in ["10"]:
                primary_pos = "Oyun Kurucu / On Numara (Playmaker)"
                conf = 0.80
            else:
                primary_pos = "Merkez Orta Saha (Central Midfield)"
                conf = 0.75
            source = "statistical_midfield"

        # --- RULE 6: Youth / Low Sample Provisional Assignment ---
        else:
            if goals >= 1:
                cat = "FW"
                primary_pos = "Genç Hücum Oyuncusu (Youth Forward)"
                conf = 0.60
                source = "youth_provisional"
            else:
                cat = "MF"
                primary_pos = "Genç Rotasyon Oyuncusu (Youth Squad)"
                conf = 0.50
                source = "youth_provisional"

        category_counts[cat] += 1
        source_counts[source] = source_counts.get(source, 0) + 1

        updates.append((
            primary_pos,  # positions
            cat,          # position_category
            primary_pos,  # primary_position
            conf,         # position_confidence
            source,       # position_source
            p_id
        ))

    # Step 4: Batch update players in SQLite
    print(f"\n[*] Updating {len(updates)} player records in SQLite database...")
    cur.executemany("""
        UPDATE players SET
            positions = ?,
            position_category = ?,
            primary_position = ?,
            position_confidence = ?,
            position_source = ?
        WHERE id = ?;
    """, updates)
    conn.commit()

    # Step 5: Unsupervised Clustering Validation (K-Means)
    print("\n[*] Tier 4: Running K-Means (K=4) clustering validation...")
    X = np.array(feature_list)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    print("[+] K-Means Cluster Profiles (Centroids in original scale):")
    for k in range(4):
        mask = (clusters == k)
        cluster_mean = X[mask].mean(axis=0)
        print(f"    Cluster {k} (N={mask.sum():>4}): Goals/Match={cluster_mean[0]:.2f}, StartRate={cluster_mean[1]:.2f}, Cards/Match={cluster_mean[3]:.2f}, Played={cluster_mean[4]:.1f}")

    # Step 6: Report Summary
    print("\n" + "=" * 65)
    print("       📊 INFERRED POSITION DISTRIBUTION SUMMARY")
    print("=" * 65)
    total = len(players)
    for cat in ["GK", "DF", "MF", "FW"]:
        count = category_counts[cat]
        pct = (count / total) * 100
        print(f"  {cat:<4} ({category_name(cat):<16}) : {count:>5} players  ({pct:5.1f}%)")
    print("-" * 65)
    print("  By Confidence & Source:")
    for src, cnt in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {src:<28} : {cnt:>5} players")
    print("=" * 65)

    # Sample top verified players
    print("\n[+] Sample Inferred Players Across Positions:")
    samples = cur.execute("""
        SELECT name, current_club, position_category, primary_position, position_confidence, position_source
        FROM players
        WHERE position_confidence >= 0.85
        ORDER BY RANDOM()
        LIMIT 8
    """).fetchall()
    for s in samples:
        print(f"  • {s['name']:<24} | {s['current_club']:<22} | {s['position_category']} -> {s['primary_position']} (Conf: {s['position_confidence']*100:.0f}%, Src: {s['position_source']})")

    conn.close()
    print("\n[✓] Position inference successfully completed and saved into 'ktff.db'.")

def category_name(cat):
    return {
        "GK": "Kaleci",
        "DF": "Savunma / Defans",
        "MF": "Orta Saha",
        "FW": "Hücum / Forvet"
    }.get(cat, "Bilinmeyen")

if __name__ == "__main__":
    run_position_inference()
