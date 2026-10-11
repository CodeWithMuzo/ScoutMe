import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection

CORE_LEAGUES = [
    {"name": "AKSA Süper Lig", "slug": "aksa-super-lig-163", "tier": 1, "gender": "male"},
    {"name": "AKSA 1.Lig", "slug": "aksa-1lig-164", "tier": 2, "gender": "male"},
    {"name": "AKSA A2 Süper Lig", "slug": "aksa-a2-super-lig-165", "tier": 3, "gender": "male"},
    {"name": "AKSA A2 1.Lig", "slug": "aksa-a2-1lig-166", "tier": 4, "gender": "male"},
    {"name": "U17 Elit Lig", "slug": "u17-elit-lig-245", "tier": 5, "gender": "male"},
    {"name": "BTM 1.Lig", "slug": "btm-1lig", "tier": 6, "gender": "male"},
    {"name": "BTM 2.Lig", "slug": "btm-2lig", "tier": 7, "gender": "male"},
]

CORE_SEASONS = [
    {"name": "2026-2027", "ktff_season_id": 13},
    {"name": "2025-2026", "ktff_season_id": 11},
    {"name": "2024-2025", "ktff_season_id": 10},
    {"name": "2023-2024", "ktff_season_id": 9},
]

def init_leagues_and_seasons():
    conn = get_connection()
    cur = conn.cursor()
    
    print("[*] Inserting Core Leagues...")
    for lg in CORE_LEAGUES:
        cur.execute("""
            INSERT INTO leagues (name, slug, tier, gender)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                slug=excluded.slug,
                tier=excluded.tier,
                gender=excluded.gender;
        """, (lg["name"], lg["slug"], lg["tier"], lg["gender"]))
    
    print("[*] Inserting Core Seasons...")
    for s in CORE_SEASONS:
        cur.execute("""
            INSERT INTO seasons (name, ktff_season_id)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                ktff_season_id=excluded.ktff_season_id;
        """, (s["name"], s["ktff_season_id"]))
        
    conn.commit()
    conn.close()
    print("[+] Core leagues and seasons seeded successfully!")

if __name__ == "__main__":
    init_leagues_and_seasons()
