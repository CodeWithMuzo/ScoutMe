import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection
from scraper.ktff_client import KTFFClient

def parse_player_profile(client, player_url):
    soup = client.get_soup(player_url)
    if not soup:
        return None
        
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        return None
        
    try:
        ktff_player_id = int(player_url.split("?")[0].rstrip("/").split("/")[-1])
    except ValueError:
        return None
        
    license_no = ""
    nationality = ""
    current_club = ""
    birth_date = ""
    birth_place = ""
    gender = "Erkek"
    positions = ""
    status = "Aktif"
    
    # Parse dl elements
    for dl in soup.find_all("dl"):
        dts = [dt.get_text(strip=True) for dt in dl.find_all("dt")]
        dds = [dd.get_text(strip=True) for dd in dl.find_all("dd")]
        for term, val in zip(dts, dds):
            if "Lisans" in term:
                license_no = val
            elif "Uyruk" in term:
                nationality = val
            elif "Kulüp" in term:
                current_club = val if val != "-" else ""
            elif "Doğum Tarihi" in term:
                birth_date = val
            elif "Doğum Yeri" in term:
                birth_place = val
            elif "Cinsiyet" in term:
                gender = val
            elif "Mevki" in term:
                positions = val if val != "-" else ""

    # Parse career transfer table (Table 2 if exists)
    career_entries = []
    tables = soup.find_all("table")
    if len(tables) >= 3:
        career_table = tables[2]
        for row in career_table.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) >= 5 and "Lisans kaydı bulunmuyor" not in cols[0]:
                career_entries.append({
                    "season": cols[0],
                    "club_name": cols[1],
                    "league_name": cols[2],
                    "registration_date": cols[3],
                    "license_status": cols[4]
                })

    return {
        "ktff_player_id": ktff_player_id,
        "name": name,
        "license_no": license_no,
        "nationality": nationality,
        "current_club": current_club,
        "birth_date": birth_date,
        "birth_place": birth_place,
        "gender": gender,
        "positions": positions,
        "status": status,
        "career_entries": career_entries
    }

def scrape_players_from_clubs(seasons=["10", "11", "13"], limit_clubs=None):
    client = KTFFClient(delay_seconds=0.3)
    conn = get_connection()
    cur = conn.cursor()
    
    # Fetch clubs from DB
    query = "SELECT slug, name FROM clubs"
    if limit_clubs:
        query += f" LIMIT {limit_clubs}"
    clubs = cur.execute(query).fetchall()
    
    print(f"[*] Extracting players from {len(clubs)} clubs across seasons {seasons}...")
    seen_player_ids = set()
    total_saved = 0
    
    for c_idx, club in enumerate(clubs, 1):
        slug = club["slug"]
        print(f"[-] [{c_idx}/{len(clubs)}] Inspecting squad for {club['name']}...")
        
        for season in seasons:
            squad_url = f"https://ktff.org/bilgi-bankasi/kulupler/{slug}?tab=squad&season={season}"
            soup = client.get_soup(squad_url)
            if not soup:
                continue
                
            player_links = []
            for a in soup.find_all("a", href=True):
                if "/bilgi-bankasi/futbolcular/" in a["href"]:
                    player_links.append(a["href"])
                    
            for purl in player_links:
                try:
                    pid = int(purl.split("?")[0].rstrip("/").split("/")[-1])
                except ValueError:
                    continue
                    
                if pid in seen_player_ids:
                    continue
                seen_player_ids.add(pid)
                
                pdata = parse_player_profile(client, purl)
                if pdata and pdata["name"]:
                    cur.execute("""
                        INSERT INTO players (ktff_player_id, license_no, name, nationality, current_club, birth_date, birth_place, gender, positions, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ktff_player_id) DO UPDATE SET
                            name=excluded.name,
                            license_no=excluded.license_no,
                            nationality=excluded.nationality,
                            current_club=excluded.current_club,
                            birth_date=excluded.birth_date,
                            birth_place=excluded.birth_place,
                            positions=excluded.positions;
                    """, (
                        pdata["ktff_player_id"],
                        pdata["license_no"],
                        pdata["name"],
                        pdata["nationality"],
                        pdata["current_club"] or club["name"],
                        pdata["birth_date"],
                        pdata["birth_place"],
                        pdata["gender"],
                        pdata["positions"],
                        pdata["status"]
                    ))
                    
                    db_player_id = cur.execute("SELECT id FROM players WHERE ktff_player_id = ?", (pdata["ktff_player_id"],)).fetchone()[0]
                    
                    for ce in pdata["career_entries"]:
                        cur.execute("""
                            INSERT INTO player_career (player_id, season, club_name, league_name, registration_date, license_status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            db_player_id,
                            ce["season"],
                            ce["club_name"],
                            ce["league_name"],
                            ce["registration_date"],
                            ce["license_status"]
                        ))
                        
                    total_saved += 1
                    
        conn.commit()
        print(f"    Unique players saved so far: {total_saved}")
        
    conn.close()
    print(f"[SUCCESS] Scraped and saved {total_saved} players into database!")

if __name__ == "__main__":
    scrape_players_from_clubs(seasons=["10"], limit_clubs=3)
