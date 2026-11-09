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

def parse_match_coaches(client, match_url, league_name, allow_antrenor=False):
    """
    Parses a single match's lineups tab and extracts A takım 'Teknik Direktör' roles
    (and for BTM 1.Lig, 'Antrenör' roles if no Teknik Direktör is present) for home and away clubs.
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
        td_list = []
        ant_list = []
        for r in g.find_all(class_="match-lineup__row"):
            role_node = r.find(class_="match-lineup__license")
            role_text = role_node.get_text(strip=True) if role_node else ""
            strong_node = r.find("strong")
            name_text = strong_node.get_text(strip=True) if strong_node else ""
            name_text = " ".join(name_text.split())
            if not name_text:
                continue

            if "Teknik Direkt" in role_text:
                td_list.append({
                    "name": name_text,
                    "role": "Teknik Direktör",
                    "club_name": current_club,
                    "league_name": league_name,
                    "match_url": match_url
                })
            elif allow_antrenor and role_text == "Antrenör":
                ant_list.append({
                    "name": name_text,
                    "role": "Antrenör (Teknik Sorumlu)",
                    "club_name": current_club,
                    "league_name": league_name,
                    "match_url": match_url
                })

        if td_list:
            results.extend(td_list)
        elif allow_antrenor and ant_list:
            results.extend(ant_list[:1])

    return results

def get_league_registered_coaches(client, league_id, league_name, allow_antrenor=False):
    """Fetches registered 2026-2027 coaches directly from KTFF league filter."""
    coaches = []
    for page in range(1, 5):
        url = f"https://ktff.org/bilgi-bankasi/teknik-direktorler?season=13&league={league_id}&page={page}"
        soup = client.get_soup(url)
        if not soup:
            break
        links = [a["href"] for a in soup.find_all("a", href=True) if "/bilgi-bankasi/teknik-direktorler/" in a["href"] and "Detay" in a.text]
        if not links:
            break
        for curl in dict.fromkeys(links):
            detail = parse_coach_detail(client, curl)
            if not detail or not detail["name"] or not detail["club_name"]:
                continue
            role = detail["role"] or ""
            if "Teknik Direkt" in role or (allow_antrenor and role == "Antrenör"):
                coaches.append({
                    "detail": detail,
                    "name": " ".join(detail["name"].split()),
                    "role": "Teknik Direktör" if "Teknik Direkt" in role else "Antrenör (Teknik Sorumlu)",
                    "club_name": detail["club_name"].strip(),
                    "league_name": league_name
                })
    return coaches

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
    1. Scrapes AKSA Süper Lig, AKSA 1. Lig, and BTM 1. Lig (Kırmızı & Beyaz Grup) matches & registered lists (Season 2026-2027)
    2. Extracts A team Teknik Direktörleri (and BTM 1.Lig Antrenör / Teknik Sorumlu where applicable)
    3. Enriches their biographical/license data from KTFF
    4. Resets and updates the 'coaches' table in SQLite
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    client = KTFFClient(use_cache=False, delay_seconds=0.06)

    print("=" * 75)
    print(" 📋 KTFF 2026-2027 SÜPER LİG, 1. LİG & BTM 1. LİG TEKNİK DİREKTÖRLERİ ")
    print("=" * 75)

    leagues_to_scrape = [
        ("AKSA Süper Lig", "60", "117", False),
        ("AKSA 1.Lig", "62", "123", False),
        ("BTM 1.Lig Kırmızı Grup", "120", "516", True),
        ("BTM 1.Lig Beyaz Grup", "121", "517", True),
    ]

    all_coaches = {} # (norm_name, club) -> coach_dict

    for league_name, comp_id, league_id, allow_ant in leagues_to_scrape:
        print(f"\n[*] Scanning {league_name} (Season 2026-2027)...")
        found_in_league = 0

        # 1. Registered league coaches from KTFF
        reg_coaches = get_league_registered_coaches(client, league_id, league_name, allow_antrenor=allow_ant)
        # Group by club to prefer Teknik Direktör over Antrenör if a club has both in BTM 1.Lig
        club_has_td = {rc["club_name"].upper() for rc in reg_coaches if "Teknik Direkt" in rc["role"]}
        for rc in reg_coaches:
            if allow_ant and rc["club_name"].upper() in club_has_td and "Teknik Direkt" not in rc["role"]:
                continue
            key = (rc["name"].upper(), rc["club_name"].upper())
            if key not in all_coaches:
                all_coaches[key] = rc
                found_in_league += 1
                print(f"    [+] {league_name:<22} | {rc['club_name']:<30} -> {rc['name']} ({rc['role']})")

        # 2. Match sheet coaches from played matches
        match_links = get_match_links(client, comp_id, season_id="13", max_pages=6)
        for m_url in match_links:
            coaches = parse_match_coaches(client, m_url, league_name, allow_antrenor=allow_ant)
            for c in coaches:
                if allow_ant and c["club_name"].upper() in club_has_td and "Teknik Direkt" not in c["role"]:
                    continue
                key = (c["name"].upper(), c["club_name"].upper())
                if key not in all_coaches:
                    all_coaches[key] = c
                    found_in_league += 1
                    print(f"    [+] {league_name:<22} | {c['club_name']:<30} -> {c['name']} ({c['role']})")

        print(f"[✓] {league_name}: Found {found_in_league} distinct head coaches.")

    # Fallback for any BTM 1.Lig clubs that did not list a coach in the first 2 weeks of 2026-2027
    fallback_btm_coaches = [
        {"name": "MEHMET KARŞILI", "role": "Teknik Direktör", "club_name": "Dipkarpaz SK", "league_name": "BTM 1.Lig Kırmızı Grup"},
        {"name": "AZİZ MAHSUCU", "role": "Antrenör (Teknik Sorumlu)", "club_name": "Ağırdağ Boğaz TSK", "league_name": "BTM 1.Lig Beyaz Grup"},
    ]
    clubs_with_coach = {c["club_name"].upper() for c in all_coaches.values()}
    for fb in fallback_btm_coaches:
        if fb["club_name"].upper() not in clubs_with_coach:
            key = (fb["name"].upper(), fb["club_name"].upper())
            all_coaches[key] = fb
            print(f"    [+] {fb['league_name']:<22} | {fb['club_name']:<30} -> {fb['name']} ({fb['role']}) [Son Kayıt]")

    print(f"\n[+] Total distinct head coaches discovered: {len(all_coaches)}")
    print("[*] Enriching coach profiles with KTFF license & biography...")

    enriched_coaches = []
    for (name_key, club_key), c in all_coaches.items():
        coach_name = " ".join(c["name"].split())
        club_name = c["club_name"]
        league_name = c["league_name"]
        
        detail = c.get("detail") or enrich_coach_profile(client, coach_name, club_name)
        
        if detail:
            enriched_coaches.append({
                "ktff_coach_id": detail["ktff_coach_id"],
                "name": " ".join((detail["name"] or coach_name).split()),
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

    # Step 4: Clear existing coaches and insert active head coaches
    print("\n[*] Updating SQLite 'coaches' table...")
    cur.execute("DELETE FROM coaches;")
    
    for c in enriched_coaches:
        cur.execute("""
            INSERT INTO coaches (ktff_coach_id, name, license_no, role, club_name, nationality, birth_date, birth_place, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ktff_coach_id) DO UPDATE SET
                name=excluded.name,
                role=excluded.role,
                club_name=excluded.club_name;
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
    print("\n" + "=" * 75)
    print("      📊 GÜNCEL 2026-2027 A TAKIM TEKNİK DİREKTÖRLERİ LİSTESİ")
    print("=" * 75)
    rows = cur.execute("SELECT id, name, club_name, role, license_no, nationality, birth_date, birth_place FROM coaches ORDER BY club_name").fetchall()
    for idx, r in enumerate(rows, 1):
        print(f" {idx:2d}. {r['name']:<26} | {r['club_name']:<30} | {r['role']:<25} | Lisans: {r['license_no']:<5}")
    print("=" * 75)
    print(f"[✓] Toplam {len(rows)} A Takım Teknik Direktörü / Teknik Sorumlusu veritabanına kaydedildi.")

    conn.close()

if __name__ == "__main__":
    run_scrape_coaches_for_current_season()
