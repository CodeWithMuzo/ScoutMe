import sys
import os
import re
import time
import concurrent.futures
from threading import Lock

# Ensure utf-8 console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection, init_db
from scraper.ktff_client import KTFFClient

db_lock = Lock()

def parse_full_player_profile(client, player_url):
    """
    Parses a single player's complete profile from KTFF:
    - Personal / license details
    - Photo URL
    - Season statistics (Goals, Yellow Cards, Red Cards, Start 11, Subbed in, Bench unused)
    - Career transfer entries
    """
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
    nationality = "KKTC"
    current_club = ""
    birth_date = ""
    birth_place = ""
    gender = "Erkek"
    positions = ""
    status = "Aktif"
    photo_url = ""

    # 1. Photo URL
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "uploads/people" in src or "futbolcu" in src.lower():
            photo_url = src
            break

    # 2. Key-value fields from dl / dt / dd
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
            elif "Durum" in term:
                status = val

    tables = soup.find_all("table")
    season_stats = {}

    # 3. Table 0: Goals, Yellow Cards, Red Cards by Season
    if len(tables) >= 1:
        for r in tables[0].find_all("tr")[1:]:
            ths = [th.text.strip() for th in r.find_all("th")]
            tds = [td.text.strip() for td in r.find_all("td")]
            if ths and len(tds) >= 3:
                s_name = ths[0]
                if s_name not in season_stats:
                    season_stats[s_name] = {
                        "season": s_name,
                        "goals": 0,
                        "yellow_cards": 0,
                        "red_cards": 0,
                        "starter": 0,
                        "sub_in": 0,
                        "bench_unused": 0
                    }
                try:
                    season_stats[s_name]["goals"] = int(tds[0]) if tds[0].isdigit() else 0
                    season_stats[s_name]["yellow_cards"] = int(tds[1]) if tds[1].isdigit() else 0
                    season_stats[s_name]["red_cards"] = int(tds[2]) if tds[2].isdigit() else 0
                except (ValueError, IndexError):
                    pass

    # 4. Table 1: Appearances (İlk 11, Oyuna Girdi, Yedek / Girmedi)
    if len(tables) >= 2:
        for r in tables[1].find_all("tr")[1:]:
            ths = [th.text.strip() for th in r.find_all("th")]
            tds = [td.text.strip() for td in r.find_all("td")]
            if ths and len(tds) >= 3:
                s_name = ths[0]
                if s_name not in season_stats:
                    season_stats[s_name] = {
                        "season": s_name,
                        "goals": 0,
                        "yellow_cards": 0,
                        "red_cards": 0,
                        "starter": 0,
                        "sub_in": 0,
                        "bench_unused": 0
                    }
                try:
                    season_stats[s_name]["starter"] = int(tds[0]) if tds[0].isdigit() else 0
                    season_stats[s_name]["sub_in"] = int(tds[1]) if tds[1].isdigit() else 0
                    season_stats[s_name]["bench_unused"] = int(tds[2]) if tds[2].isdigit() else 0
                except (ValueError, IndexError):
                    pass

    # Compute totals
    for s, st in season_stats.items():
        st["total_played"] = st["starter"] + st["sub_in"]
        st["total_squad"] = st["total_played"] + st["bench_unused"]

    # 5. Table 2: Career / Transfer entries
    career_entries = []
    if len(tables) >= 3:
        for row in tables[2].find_all("tr")[1:]:
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
        "photo_url": photo_url,
        "season_stats": list(season_stats.values()),
        "career_entries": career_entries
    }

def fetch_active_listing_page(client, page):
    """Fetches a single page of active players search."""
    url = f"https://ktff.org/bilgi-bankasi/futbolcular?status=active&page={page}"
    soup = client.get_soup(url)
    if not soup:
        return []
    links = [a["href"] for a in soup.find_all("a", href=True) if "/bilgi-bankasi/futbolcular/" in a["href"]]
    return list(dict.fromkeys(links))

def collect_all_active_player_urls(client, max_pages=250, workers=8):
    """Concurrently collects all active player profile URLs."""
    print(f"[*] Discovering active player profile URLs across up to {max_pages} pages...")
    all_urls = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_page = {executor.submit(fetch_active_listing_page, client, p): p for p in range(1, max_pages + 1)}
        for future in concurrent.futures.as_completed(future_to_page):
            p_num = future_to_page[future]
            try:
                links = future.result()
                if links:
                    all_urls.extend(links)
                if p_num % 25 == 0 or p_num == 1:
                    print(f"    - Page {p_num:3d} inspected (found {len(links)} players)")
            except Exception as e:
                print(f"    [!] Error fetching page {p_num}: {e}")

    unique_urls = list(dict.fromkeys(all_urls))
    print(f"[+] Total unique active player URLs found: {len(unique_urls)}")
    return unique_urls

def save_player_data(pdata, conn):
    """Saves player profile, season stats, and career history into SQLite with transaction lock."""
    with db_lock:
        cur = conn.cursor()
        
        # 1. Upsert into players
        cur.execute("""
            INSERT INTO players (ktff_player_id, license_no, name, nationality, current_club, birth_date, birth_place, gender, positions, status, photo_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ktff_player_id) DO UPDATE SET
                name=excluded.name,
                license_no=excluded.license_no,
                nationality=excluded.nationality,
                current_club=CASE WHEN excluded.current_club != '' THEN excluded.current_club ELSE players.current_club END,
                birth_date=excluded.birth_date,
                birth_place=excluded.birth_place,
                positions=CASE WHEN excluded.positions != '' THEN excluded.positions ELSE players.positions END,
                status=excluded.status,
                photo_url=CASE WHEN excluded.photo_url != '' THEN excluded.photo_url ELSE players.photo_url END;
        """, (
            pdata["ktff_player_id"],
            pdata["license_no"],
            pdata["name"],
            pdata["nationality"],
            pdata["current_club"],
            pdata["birth_date"],
            pdata["birth_place"],
            pdata["gender"],
            pdata["positions"],
            pdata["status"],
            pdata["photo_url"]
        ))
        
        db_player_id = cur.execute("SELECT id FROM players WHERE ktff_player_id = ?", (pdata["ktff_player_id"],)).fetchone()[0]

        # 2. Upsert season stats (Goals, Cards, Start 11, Sub In, Bench)
        for st in pdata["season_stats"]:
            cur.execute("""
                INSERT INTO player_season_stats (
                    player_id, ktff_player_id, season, goals, yellow_cards, red_cards,
                    starter_matches, sub_in_matches, bench_unused_matches,
                    total_played_matches, total_squad_matches
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ktff_player_id, season) DO UPDATE SET
                    goals=excluded.goals,
                    yellow_cards=excluded.yellow_cards,
                    red_cards=excluded.red_cards,
                    starter_matches=excluded.starter_matches,
                    sub_in_matches=excluded.sub_in_matches,
                    bench_unused_matches=excluded.bench_unused_matches,
                    total_played_matches=excluded.total_played_matches,
                    total_squad_matches=excluded.total_squad_matches;
            """, (
                db_player_id,
                pdata["ktff_player_id"],
                st["season"],
                st["goals"],
                st["yellow_cards"],
                st["red_cards"],
                st["starter"],
                st["sub_in"],
                st["bench_unused"],
                st["total_played"],
                st["total_squad"]
            ))

        # 3. Career entries
        if pdata["career_entries"]:
            # Delete old career for this player to prevent duplicates on re-runs
            cur.execute("DELETE FROM player_career WHERE player_id = ?", (db_player_id,))
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
        
        conn.commit()

def scrape_all_active_players(max_pages=250, limit=None, workers=6):
    """
    Main orchestrator for active players:
    1. Collects active player profile links.
    2. Concurrently fetches profiles, stats, and career history.
    3. Saves everything to SQLite database.
    """
    init_db()
    client = KTFFClient(delay_seconds=0.05)
    conn = get_connection()
    
    player_urls = collect_all_active_player_urls(client, max_pages=max_pages, workers=workers)
    
    if limit:
        print(f"[*] Limiting execution to first {limit} players for testing.")
        player_urls = player_urls[:limit]

    total_count = len(player_urls)
    print(f"\n[*] Starting profile and season statistics scraping for {total_count} active players ({workers} concurrent workers)...")

    processed = 0
    start_time = time.time()

    def process_url(url):
        pdata = parse_full_player_profile(client, url)
        if pdata:
            save_player_data(pdata, conn)
            return pdata["name"]
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_url, u): u for u in player_urls}
        for future in concurrent.futures.as_completed(futures):
            processed += 1
            res_name = future.result()
            if processed % 50 == 0 or processed == total_count or processed <= 10:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                pct = (processed / total_count) * 100
                print(f"    [{processed:4d}/{total_count}] ({pct:5.1f}%) - Last: {res_name or 'Unknown'} ({rate:.1f} players/sec)")

    conn.close()
    elapsed = time.time() - start_time
    print(f"\n[SUCCESS] Completed scraping {processed} active players in {elapsed:.1f} seconds!")

if __name__ == "__main__":
    scrape_all_active_players(max_pages=5, limit=20, workers=4)
