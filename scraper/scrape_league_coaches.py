import sys
import os
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import concurrent.futures

# Ensure UTF-8 console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, init_db
from scraper.ktff_client import KTFFClient
from scraper.scrape_coaches import parse_coach_detail

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_match_links(client, comp_id, season_id="13", max_pages=6):
    """Fetches all match URLs for a given competition in season 13 (2026-2027)."""
    match_links = []
    for page in range(1, max_pages + 1):
        url = f"https://ktff.org/bilgi-bankasi/maclar?season={season_id}&competition={comp_id}&page={page}"
        soup = client.get_soup(url)
        if not soup:
            break
        links = [a["href"] for a in soup.find_all("a", href=True) if "/maclar/" in a["href"] and ("Maç" in a.text or "#" in a.text)]
        if not links:
            break
        match_links.extend(links)
    return list(dict.fromkeys(match_links))

def parse_match_coaches(client, match_url, league_name):
    """
    Parses a single match's lineups tab and extracts only A takım 'Teknik Direktör' roles for home and away clubs.
    """
    lineups_url = match_url.split("?")[0] + "?tab=lineups"
    soup = client.get_soup(lineups_url)
    if not soup:
        return []

    # Get home and away team names
    teams = [t.get_text(strip=True) for t in soup.find_all(class_=lambda c: c and "match-hero__team-info" in str(c))]
    if len(teams) < 2:
        teams = [t.get_text(strip=True) for t in soup.find_all(class_=lambda c: c and "team-info" in str(c))]
        
    home_club = teams[0] if len(teams) > 0 else "Bilinmeyen Kulüp"
    away_club = teams[1] if len(teams) > 1 else "Bilinmeyen Kulüp"

    te_groups = [g for g in soup.find_all(class_="match-lineup__group") if "Teknik Ekip" in g.get_text()]
    if not te_groups:
        return []

    results = []
    # In KTFF HTML, first TE group is home, second TE group is away
    for idx, g in enumerate(te_groups):
        current_club = home_club if idx == 0 else away_club
        for r in g.find_all(class_="match-lineup__row"):
            role_node = r.find(class_="match-lineup__license")
            role_text = role_node.get_text(strip=True) if role_node else ""
            
            # STRICT FILTER: Only 'Teknik Direktör'
            if "Teknik Direkt" in role_text:
                strong_node = r.find("strong")
                name_text = strong_node.get_text(strip=True) if strong_node else ""
                # Clean multiple spaces
                name_text = " ".join(name_text.split())
                if name_text:
                    results.append({
                        "name": name_text,
                        "role": role_text,
                        "club_name": current_club,
                        "league_name": league_name,
                        "match_url": match_url
                    })

    return results

def enrich_coach_profile(client, coach_name, current_club):
    """
    Searches KTFF coach database for the coach profile to extract license, birth date, place, nationality.
    """
    query = urllib.parse.quote(coach_name)
    search_url = f"https://ktff.org/bilgi-bankasi/teknik-direktorler?q={query}"
    soup = client.get_soup(search_url)
    if not soup:
        return None

    coach_links = [a["href"] for a in soup.find_all("a", href=True) if "/bilgi-bankasi/teknik-direktorler/" in a["href"]]
    coach_links = list(dict.fromkeys(coach_links))
    
    if not coach_links:
        return None
        
    # Detail from the first matching profile
    detail = parse_coach_detail(client, coach_links[0])
    return detail

def run_scrape_coaches_for_current_season():
    """
    Main orchestrator:
    1. Scrapes AKSA Süper Lig and AKSA 1. Lig matches (Season 2026-2027)
    2. Extracts only A team Teknik Direktörleri
    3. Enriches their biographical/license data from KTFF
    4. Resets and updates the 'coaches' table in SQLite
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    client = KTFFClient(delay_seconds=0.2)

    print("=" * 70)
    print(" 📋 KTFF 2026-2027 AKSA SÜPER LİG & 1. LİG A TAKIM TEKNİK DİREKTÖRLERİ ")
    print("=" * 70)

    leagues_to_scrape = [
        ("AKSA Süper Lig", "60"),
        ("AKSA 1.Lig", "62")
    ]

    all_coaches = {} # (norm_name, club) -> coach_dict

    for league_name, comp_id in leagues_to_scrape:
        print(f"\n[*] Scanning matches for {league_name} (Season 2026-2027)...")
        match_links = get_match_links(client, comp_id, season_id="13", max_pages=6)
        print(f"    Found {len(match_links)} matches in fixture.")
        
        found_in_league = 0
        for m_url in match_links:
            coaches = parse_match_coaches(client, m_url, league_name)
            for c in coaches:
                key = (c["name"].upper(), c["club_name"].upper())
                if key not in all_coaches:
                    all_coaches[key] = c
                    found_in_league += 1
                    print(f"    [+] {league_name:<16} | {c['club_name']:<24} -> {c['name']} ({c['role']})")

        print(f"[✓] {league_name}: Found {found_in_league} distinct A team head coaches.")

    print(f"\n[+] Total distinct A team head coaches discovered: {len(all_coaches)}")
    print("[*] Enriching coach profiles with KTFF license & biography...")

    enriched_coaches = []
    for (name_key, club_key), c in all_coaches.items():
        coach_name = c["name"]
        club_name = c["club_name"]
        league_name = c["league_name"]
        
        # Search and parse profile
        detail = enrich_coach_profile(client, coach_name, club_name)
        
        if detail:
            enriched_coaches.append({
                "ktff_coach_id": detail["ktff_coach_id"],
                "name": detail["name"] or coach_name,
                "license_no": detail["license_no"],
                "role": c["role"],
                "club_name": club_name,
                "league_name": league_name,
                "nationality": detail["nationality"] or "KKTC",
                "birth_date": detail["birth_date"],
                "birth_place": detail["birth_place"],
                "gender": detail["gender"] or "Erkek"
            })
        else:
            enriched_coaches.append({
                "ktff_coach_id": None,
                "name": coach_name,
                "license_no": "",
                "role": c["role"],
                "club_name": club_name,
                "league_name": league_name,
                "nationality": "KKTC",
                "birth_date": "",
                "birth_place": "",
                "gender": "Erkek"
            })

    # Step 4: Clear existing coaches and insert only these active A takım head coaches
    print("\n[*] Updating SQLite 'coaches' table (retaining only current 2026-2027 A takım head coaches)...")
    cur.execute("DELETE FROM coaches;")
    
    for c in enriched_coaches:
        cur.execute("""
            INSERT INTO coaches (ktff_coach_id, name, license_no, role, club_name, nationality, birth_date, birth_place, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            c["ktff_coach_id"],
            c["name"],
            c["license_no"],
            c["role"],
            c["club_name"],
            c["nationality"],
            c["birth_date"],
            c["birth_place"],
            c["gender"]
        ))
    
    conn.commit()

    # Step 5: Print summary report
    print("\n" + "=" * 70)
    print("      📊 GÜNCEL 2026-2027 A TAKIM TEKNİK DİREKTÖRLERİ LİSTESİ")
    print("=" * 70)
    rows = cur.execute("SELECT id, name, club_name, license_no, nationality, birth_date, birth_place FROM coaches ORDER BY club_name").fetchall()
    for idx, r in enumerate(rows, 1):
        print(f" {idx:2d}. {r['name']:<24} | {r['club_name']:<25} | Lisans: {r['license_no']:<5} | D.Yeri: {r['birth_place']}")
    print("=" * 70)
    print(f"[✓] Toplam {len(rows)} A Takım Teknik Direktörü veritabanına başarıyla kaydedildi.")

    conn.close()

if __name__ == "__main__":
    run_scrape_coaches_for_current_season()
