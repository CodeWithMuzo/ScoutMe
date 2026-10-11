import sys
import os
import re
import time
import concurrent.futures
from threading import Lock
from bs4 import BeautifulSoup

# Ensure UTF-8 console output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, init_db
from scraper.ktff_client import KTFFClient

db_lock = Lock()

TARGET_LEAGUES_SEASONS = [
    # 2026-2027 (Season 13)
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA Süper Lig", "comp_id": 60},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA 1.Lig", "comp_id": 62},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA A2 Süper Lig", "comp_id": 64},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA A2 1.Lig", "comp_id": 65},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "U17 Elit Lig", "comp_id": 148},

    # 2025-2026 (Season 11)
    {"season_name": "2025-2026", "season_id": 11, "comp_name": "AKSA Süper Lig", "comp_id": 1},
    {"season_name": "2025-2026", "season_id": 11, "comp_name": "AKSA 1.Lig", "comp_id": 61},
    {"season_name": "2025-2026", "season_id": 11, "comp_name": "AKSA A2 Süper Lig", "comp_id": 63},
    {"season_name": "2025-2026", "season_id": 11, "comp_name": "AKSA A2 1.Lig", "comp_id": 22},
    {"season_name": "2025-2026", "season_id": 11, "comp_name": "U17 Elit Lig", "comp_id": 148},

    # 2024-2025 (Season 10)
    {"season_name": "2024-2025", "season_id": 10, "comp_name": "AKSA Süper Lig", "comp_id": 1},
    {"season_name": "2024-2025", "season_id": 10, "comp_name": "AKSA 1.Lig", "comp_id": 61},
    {"season_name": "2024-2025", "season_id": 10, "comp_name": "AKSA A2 Süper Lig", "comp_id": 63},
    {"season_name": "2024-2025", "season_id": 10, "comp_name": "AKSA A2 1.Lig", "comp_id": 22},
    {"season_name": "2024-2025", "season_id": 10, "comp_name": "U17 Elit Lig", "comp_id": 148},
]

def collect_match_links(client, season_id, comp_id, max_pages=30):
    """Fetches all match URLs for a given season and competition."""
    all_links = []
    for page in range(1, max_pages + 1):
        url = f"https://ktff.org/bilgi-bankasi/maclar?season={season_id}&competition={comp_id}&page={page}"
        soup = client.get_soup(url)
        if not soup:
            break
        links = [a["href"] for a in soup.find_all("a", href=True) if "/maclar/" in a["href"] and ("Maç" in a.text or "#" in a.text)]
        if not links:
            break
        all_links.extend(links)
    return list(dict.fromkeys(all_links))

def parse_match_details(client, match_url, season_name, fallback_league):
    """Fetches and parses a single match's score, metadata, lineups, and events."""
    soup = client.get_soup(match_url)
    if not soup:
        return None
        
    try:
        ktff_match_id = int(match_url.split("?")[0].rstrip("/").split("/")[-1])
    except ValueError:
        return None

    # 1. Teams and scores
    teams = [t.get_text(strip=True) for t in soup.find_all(class_=lambda c: c and "match-hero__team-info" in str(c))]
    if len(teams) < 2:
        teams = [t.get_text(strip=True) for t in soup.find_all(class_=lambda c: c and "team-info" in str(c))]
    if len(teams) < 2:
        return None
        
    home_club = teams[0]
    away_club = teams[1]
    
    score_el = soup.find(class_=lambda c: c and "match-hero__score" in str(c))
    home_score = None
    away_score = None
    if score_el:
        score_text = score_el.get_text(strip=True)
        scores = re.findall(r"\d+", score_text)
        if len(scores) >= 2:
            home_score = int(scores[0])
            away_score = int(scores[1])
            
    # 2. Metadata (League, Date, Time, Stadium)
    league_name = fallback_league
    match_date = ""
    match_time = ""
    stadium_name = ""
    status = "played" if home_score is not None else "scheduled"
    
    meta_items = soup.find_all(class_=lambda c: c and "match-meta__item" in str(c))
    for item in meta_items:
        txt = item.get_text(strip=True)
        if "Lig" in txt or "Kupa" in txt:
            league_name = txt.split("-")[0].strip()
        elif any(m in txt for m in ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]):
            if "-" in txt:
                p = txt.split("-")
                match_date = p[0].strip()
                match_time = p[1].strip()
            else:
                match_date = txt

    # 3. Match Timeline / Events
    events = []
    timeline_rows = soup.find_all(class_=lambda c: c and "match-timeline__row" in str(c))
    for r in timeline_rows:
        min_el = r.find(class_=lambda c: c and "minute" in str(c))
        min_str = min_el.get_text(strip=True).replace("'", "").replace("+", "") if min_el else "0"
        try:
            minute = int(min_str)
        except ValueError:
            minute = 0
            
        home_ev = r.find(class_=lambda c: c and "match-timeline__event--home" in str(c))
        away_ev = r.find(class_=lambda c: c and "match-timeline__event--away" in str(c))
        
        is_home = True if home_ev and home_ev.get_text(strip=True) else False
        ev_node = home_ev if is_home else away_ev
        if not ev_node:
            continue
            
        raw_text = ev_node.get_text(" ", strip=True)
        club = home_club if is_home else away_club
        
        event_type = "unknown"
        raw_lower = raw_text.lower()
        if "penaltı" in raw_lower:
            event_type = "penalty"
        elif "gol" in raw_lower:
            event_type = "goal"
        elif "kırmızı kart" in raw_lower or "kırmızı" in raw_lower:
            event_type = "red_card"
        elif "sarı kart" in raw_lower or "sarı" in raw_lower:
            event_type = "yellow_card"
        elif "girdi" in raw_lower or "çıktı" in raw_lower:
            event_type = "sub"
            
        player_name = raw_text.split("/")[0].strip() if "/" in raw_text else raw_text
        for strip_w in ["Sarı kart", "Kırmızı kart", "Gol", "Penaltı", "sarı kart", "kırmızı kart"]:
            player_name = player_name.replace(strip_w, "").strip()
            
        events.append({
            "club_name": club,
            "minute": minute,
            "event_type": event_type,
            "player_name": player_name,
            "detail": raw_text
        })

    # 4. Lineups Tab
    lineups_url = match_url.split("?")[0] + "?tab=lineups"
    soup_lineup = client.get_soup(lineups_url)
    lineups = []
    
    if soup_lineup:
        groups = soup_lineup.find_all(class_=lambda c: c and "match-lineup__group" in str(c))
        current_side = "home"
        group_idx = 0
        
        for g in groups:
            title_node = g.find(class_=lambda c: c and "title" in str(c))
            title = title_node.get_text(strip=True) if title_node else ""
            if "Teknik Ekip" in title:
                continue
                
            is_starter = 1 if "İlk 11" in title else 0
            if group_idx >= 2 and is_starter == 1:
                current_side = "away"
            group_idx += 1
            
            club_for_group = home_club if current_side == "home" else away_club
            is_home_flag = 1 if current_side == "home" else 0
            
            rows = g.find_all(class_=lambda c: c and "match-lineup__row" in str(c))
            for row in rows:
                pname_node = row.find(class_=lambda c: c and "player" in str(c)) or row.find(class_=lambda c: c and "name" in str(c))
                pname = pname_node.get_text(" ", strip=True) if pname_node else ""
                if not pname:
                    continue
                    
                lic_match = re.search(r"Lisans No:\s*(\d+)", row.get_text())
                license_no = lic_match.group(1) if lic_match else ""
                clean_pname = re.sub(r"Lisans No:\s*\d+", "", pname).strip()
                
                row_text = row.get_text(" ", strip=True)
                num_match = re.match(r"^(\d+)\s+", row_text)
                shirt_number = num_match.group(1) if num_match else ""
                
                is_captain = 1 if re.search(r"\bK\b", row_text) else 0
                is_goalkeeper = 1 if re.search(r"\bKL\b", row_text) else 0
                
                minutes_played = 90 if is_starter == 1 else 0
                sub_in_min = None
                sub_out_min = None
                
                for ev in events:
                    if ev["event_type"] == "sub" and clean_pname.lower() in ev["detail"].lower():
                        if "çıktı" in ev["detail"]:
                            sub_out_min = ev["minute"]
                            if is_starter:
                                minutes_played = sub_out_min
                        elif "girdi" in ev["detail"]:
                            sub_in_min = ev["minute"]
                            minutes_played = max(0, 90 - sub_in_min)
                            
                lineups.append({
                    "club_name": club_for_group,
                    "is_home": is_home_flag,
                    "player_name": clean_pname,
                    "license_no": license_no,
                    "shirt_number": shirt_number,
                    "is_starter": is_starter,
                    "is_captain": is_captain,
                    "is_goalkeeper": is_goalkeeper,
                    "sub_in_minute": sub_in_min,
                    "sub_out_minute": sub_out_min,
                    "minutes_played": minutes_played
                })

    return {
        "ktff_match_id": ktff_match_id,
        "season": season_name,
        "league_name": league_name,
        "home_club": home_club,
        "away_club": away_club,
        "home_score": home_score,
        "away_score": away_score,
        "match_date": match_date,
        "match_time": match_time,
        "stadium_name": stadium_name,
        "status": status,
        "lineups": lineups,
        "events": events
    }

def save_match_to_db(conn, mdata):
    """Atomically writes parsed match data, lineups, and events to SQLite."""
    with db_lock:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO matches (ktff_match_id, season, league_name, home_club, away_club, home_score, away_score, match_date, match_time, stadium_name, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ktff_match_id) DO UPDATE SET
                season=excluded.season,
                league_name=excluded.league_name,
                home_score=excluded.home_score,
                away_score=excluded.away_score,
                match_date=excluded.match_date,
                match_time=excluded.match_time,
                status=excluded.status;
        """, (
            mdata["ktff_match_id"],
            mdata["season"],
            mdata["league_name"],
            mdata["home_club"],
            mdata["away_club"],
            mdata["home_score"],
            mdata["away_score"],
            mdata["match_date"],
            mdata["match_time"],
            mdata["stadium_name"],
            mdata["status"]
        ))
        
        db_match_id = cur.execute("SELECT id FROM matches WHERE ktff_match_id = ?", (mdata["ktff_match_id"],)).fetchone()[0]
        
        # Save Lineups
        cur.execute("DELETE FROM match_lineups WHERE match_id = ?", (db_match_id,))
        for lp in mdata["lineups"]:
            cur.execute("""
                INSERT INTO match_lineups (match_id, club_name, is_home, player_name, license_no, shirt_number, is_starter, is_captain, is_goalkeeper, sub_in_minute, sub_out_minute, minutes_played)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                db_match_id,
                lp["club_name"],
                lp["is_home"],
                lp["player_name"],
                lp["license_no"],
                lp["shirt_number"],
                lp["is_starter"],
                lp["is_captain"],
                lp["is_goalkeeper"],
                lp["sub_in_minute"],
                lp["sub_out_minute"],
                lp["minutes_played"]
            ))
            
        # Save Events
        cur.execute("DELETE FROM match_events WHERE match_id = ?", (db_match_id,))
        for ev in mdata["events"]:
            cur.execute("""
                INSERT INTO match_events (match_id, club_name, minute, event_type, player_name, detail)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                db_match_id,
                ev["club_name"],
                ev["minute"],
                ev["event_type"],
                ev["player_name"],
                ev["detail"]
            ))
            
        conn.commit()

def run_multi_season_scrape(workers=8, limit=None):
    init_db()
    conn = get_connection()
    client = KTFFClient(delay_seconds=0.08)
    
    print("=" * 70)
    print(" ⚽ SCOUTME: AKSA SÜPER LİG & 1. LİG SON 3 SEZON MAÇ KAZIMA MOTORU")
    print("=" * 70)
    
    # Step 1: Collect match links across targets
    tasks_to_scrape = [] # (match_url, season_name, league_name)
    
    for target in TARGET_LEAGUES_SEASONS:
        s_name = target["season_name"]
        s_id = target["season_id"]
        c_name = target["comp_name"]
        c_id = target["comp_id"]
        
        print(f"[*] Tarama yapılıyor: {s_name} | {c_name} (Season: {s_id}, Comp: {c_id})...")
        links = collect_match_links(client, s_id, c_id)
        print(f"    -> Bulunan maç sayısı: {len(links)}")
        for l in links:
            tasks_to_scrape.append((l, s_name, c_name))
            
    # Deduplicate by URL
    seen = set()
    unique_tasks = []
    for l, s, c in tasks_to_scrape:
        if l not in seen:
            seen.add(l)
            unique_tasks.append((l, s, c))
            
    total_found = len(unique_tasks)
    print(f"\n[+] Toplam taranacak benzersiz maç sayısı: {total_found}")
    
    if limit:
        unique_tasks = unique_tasks[:limit]
        print(f"[*] Limit uygulandı: İlk {len(unique_tasks)} maç işlenecek.")

    # Check which matches already exist in DB with lineups
    cur = conn.cursor()
    existing_ids = set([r[0] for r in cur.execute("""
        SELECT m.ktff_match_id 
        FROM matches m 
        JOIN match_lineups l ON m.id = l.match_id 
        GROUP BY m.ktff_match_id
    """).fetchall()])
    print(f"[*] Halihazırda kadrolarıyla veritabanında olan maç sayısı: {len(existing_ids)}")
    
    filtered_tasks = []
    for l, s, c in unique_tasks:
        try:
            mid = int(l.split("?")[0].rstrip("/").split("/")[-1])
            if mid not in existing_ids:
                filtered_tasks.append((l, s, c))
        except ValueError:
            filtered_tasks.append((l, s, c))
            
    print(f"[*] Çekilecek / güncellenecek yeni maç sayısı: {len(filtered_tasks)}")
    
    if not filtered_tasks:
        print("[✓] Tüm maçlar zaten veritabanında mevcut! İşlem tamam.")
        conn.close()
        return

    # Step 2: ThreadPool processing
    print(f"\n[*] {workers} iş parçacığı (worker) ile paralel çekme başlatılıyor...")
    start_time = time.time()
    processed_count = 0
    saved_count = 0
    
    def worker_job(task):
        m_url, s_name, c_name = task
        try:
            mdata = parse_match_details(client, m_url, s_name, c_name)
            if mdata:
                save_match_to_db(conn, mdata)
                return True, mdata
            return False, None
        except Exception as e:
            return False, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(worker_job, t): t for t in filtered_tasks}
        for future in concurrent.futures.as_completed(futures):
            processed_count += 1
            success, res = future.result()
            if success:
                saved_count += 1
                if saved_count % 25 == 0 or saved_count == len(filtered_tasks):
                    elapsed = time.time() - start_time
                    rate = saved_count / elapsed if elapsed > 0 else 0
                    print(f"    [{saved_count}/{len(filtered_tasks)}] Maç kaydedildi ({rate:.1f} maç/sn) - Son: {res['home_club']} {res['home_score']}-{res['away_score']} {res['away_club']}")
            else:
                pass
                
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"[✓] TAMAMLANDI! {saved_count} maç başarıyla çekildi ve veritabanına işlendi. (Süre: {elapsed:.1f} sn)")
    print("=" * 70)
    
    # Final audit counts
    cur = conn.cursor()
    m_cnt = cur.execute("SELECT count(*) FROM matches").fetchone()[0]
    l_cnt = cur.execute("SELECT count(*) FROM match_lineups").fetchone()[0]
    e_cnt = cur.execute("SELECT count(*) FROM match_events").fetchone()[0]
    print(f"  • Toplam Maç (matches)         : {m_cnt}")
    print(f"  • Toplam Kadro (match_lineups) : {l_cnt}")
    print(f"  • Toplam Olay (match_events)   : {e_cnt}")
    
    print("\nSezonlara Göre Maç Dağılımı:")
    for r in cur.execute("SELECT season, league_name, count(*) FROM matches GROUP BY season, league_name ORDER BY season DESC, count(*) DESC").fetchall():
        print(f"  - {r[0]:<12} | {r[1]:<18} : {r[2]} maç")
        
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8, help="Number of worker threads")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of matches for testing")
    args = parser.parse_args()
    run_multi_season_scrape(workers=args.workers, limit=args.limit)
