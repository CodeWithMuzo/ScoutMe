"""
update_database_full.py
=======================
Full Database Update & Synchronization Pipeline for ScoutMe (KTFF Ecosystem).
1. Scans KTFF live pages for all 2026-2027 competitions.
2. Identifies all finished/played matches needing score, lineup, and event data.
3. Concurrently scrapes match details, full esame lineups, and timeline events (goals, cards, subs).
4. Updates `matches`, `match_lineups`, and `match_events` in `data/ktff.db`.
5. Syncs `player_season_stats` for 2026-2027 based on official match data.
6. Re-calculates 4-pillar player skill ratings (Physical, Shooting, Technical, Defending, OVR).
7. Re-builds HGNN graph topology and latent embeddings (`hgnn_embeddings.pt`).
"""

import sys
import os
import re
import time
import sqlite3
import concurrent.futures
from threading import Lock
from bs4 import BeautifulSoup

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from database.db import get_connection, init_db
from scraper.ktff_client import KTFFClient

db_lock = Lock()

TARGET_LEAGUES_SEASONS_2026 = [
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA Süper Lig", "comp_id": 60, "max_pages": 7},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA 1.Lig", "comp_id": 62, "max_pages": 7},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA A2 Süper Lig", "comp_id": 64, "max_pages": 7},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "AKSA A2 1.Lig", "comp_id": 65, "max_pages": 7},
    {"season_name": "2026-2027", "season_id": 13, "comp_name": "U17 Elit Lig", "comp_id": 148, "max_pages": 7},
]

def scan_for_matches_needing_update(client, conn):
    print("=" * 70)
    print(" 🔍 ADIM 1: KTFF 2026-2027 CANLI MAÇ TARAMASI")
    print("=" * 70)
    
    cur = conn.cursor()
    cur.execute("""
        SELECT m.ktff_match_id, m.home_score, COUNT(l.id) as lc
        FROM matches m
        LEFT JOIN match_lineups l ON m.id = l.match_id
        WHERE m.season = '2026-2027'
        GROUP BY m.ktff_match_id
    """)
    db_match_status = {row[0]: {"has_score": row[1] is not None, "lineups": row[2]} for row in cur.fetchall()}

    def scan_page(target, page):
        url = f"https://ktff.org/bilgi-bankasi/maclar?season={target['season_id']}&competition={target['comp_id']}&page={page}"
        soup = client.get_soup(url)
        if not soup:
            return []
        cards = soup.find_all("a", class_=lambda c: c and "match-fixture-card" in str(c))
        results = []
        for card in cards:
            href = card.get("href", "")
            try:
                mid = int(href.split("?")[0].rstrip("/").split("/")[-1])
            except ValueError:
                continue
            text = card.get_text(" ", strip=True)
            is_finished = "Maç Sonucu" in text or bool(re.search(r'\d+\s*-\s*\d+', text))
            score_m = re.search(r'(\d+)\s*-\s*(\d+)', text)
            score_str = f"{score_m.group(1)}-{score_m.group(2)}" if score_m else None
            
            results.append({
                "mid": mid,
                "url": href,
                "comp_name": target["comp_name"],
                "season_name": target["season_name"],
                "is_finished": is_finished,
                "score": score_str,
                "text": text[:60]
            })
        return results

    all_matches = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for tgt in TARGET_LEAGUES_SEASONS_2026:
            for p in range(1, tgt["max_pages"] + 1):
                futures.append(executor.submit(scan_page, tgt, p))
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                all_matches.extend(res)

    # Deduplicate
    seen = set()
    unique_matches = []
    for m in all_matches:
        if m["mid"] not in seen:
            seen.add(m["mid"])
            unique_matches.append(m)

    to_scrape = []
    for m in unique_matches:
        mid = m["mid"]
        if mid not in db_match_status:
            to_scrape.append(m)
        else:
            st = db_match_status[mid]
            if m["is_finished"] and (not st["has_score"] or st["lineups"] == 0):
                to_scrape.append(m)

    print(f"[*] Toplam taranan 2026-2027 maç sayısı : {len(unique_matches)}")
    print(f"[+] Çekilecek / Güncellenecek maç sayısı : {len(to_scrape)}")
    return to_scrape

def parse_full_match_details(client, match_url, season_name, fallback_league):
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
    sub_outs = {} # player_name_lower -> minute
    sub_ins = {}  # player_name_lower -> minute

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
            
        club = home_club if is_home else away_club
        raw_text = ev_node.get_text(" ", strip=True)
        raw_lower = raw_text.lower()

        # Substitutions
        sub_out_node = ev_node.find(class_=lambda c: c and "substitution-out" in str(c))
        sub_in_node = ev_node.find(class_=lambda c: c and "substitution-in" in str(c))
        if sub_out_node or sub_in_node or "değişikliği" in raw_lower:
            person_links = ev_node.find_all(class_=lambda c: c and "person-link" in str(c))
            if len(person_links) >= 2:
                p_out = person_links[0].get_text(strip=True)
                p_in = person_links[1].get_text(strip=True)
                sub_outs[p_out.lower()] = minute
                sub_ins[p_in.lower()] = minute
                events.append({
                    "club_name": club,
                    "minute": minute,
                    "event_type": "sub",
                    "player_name": f"{p_out} -> {p_in}",
                    "detail": raw_text
                })
                continue

        event_type = "unknown"
        if "değişikliği" in raw_lower or "→" in raw_text or "->" in raw_text:
            event_type = "sub"
        elif "kendi kalesine" in raw_lower:
            event_type = "own_goal"
        elif "penaltı" in raw_lower:
            event_type = "penalty"
        elif "kırmızı kart" in raw_lower or "kırmızı" in raw_lower or "ikinci sarı" in raw_lower:
            event_type = "red_card"
        elif "sarı kart" in raw_lower or "sarı" in raw_lower:
            event_type = "yellow_card"
        elif "gol" in raw_lower or re.search(r'\(\d+-\d+\)', raw_text) or "/" in raw_text:
            event_type = "goal"

        person_link = ev_node.find(class_=lambda c: c and "person-link" in str(c))
        if person_link:
            player_name = person_link.get_text(strip=True)
        else:
            player_name = raw_text.split("/")[0].strip() if "/" in raw_text else raw_text
            player_name = re.sub(r'\(\d+-\d+\)', '', player_name).strip()
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
                
                clean_lower = clean_pname.lower()
                sub_in_min = sub_ins.get(clean_lower)
                sub_out_min = sub_outs.get(clean_lower)
                
                if is_starter == 1:
                    minutes_played = sub_out_min if sub_out_min is not None else 90
                else:
                    minutes_played = max(0, 90 - sub_in_min) if sub_in_min is not None else 0
                            
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

def save_match_records(conn, mdata):
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

def run_match_updates(matches_to_scrape, workers=8):
    print("\n" + "=" * 70)
    print(" 🚀 ADIM 2: MAÇ DETAYLARI, KADROLAR VE OLAYLAR ÇEKİLİYOR")
    print("=" * 70)
    
    conn = get_connection()
    client = KTFFClient(use_cache=False, delay_seconds=0.04)
    start_time = time.time()
    saved = 0
    
    def process_task(m):
        try:
            mdata = parse_full_match_details(client, m["url"], m["season_name"], m["comp_name"])
            if mdata:
                save_match_records(conn, mdata)
                return True, mdata
            return False, None
        except Exception as e:
            return False, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_task, m): m for m in matches_to_scrape}
        for future in concurrent.futures.as_completed(futures):
            success, res = future.result()
            if success:
                saved += 1
                if saved % 10 == 0 or saved == len(matches_to_scrape):
                    rate = saved / (time.time() - start_time)
                    print(f"    [{saved:2d}/{len(matches_to_scrape)}] Maç işlendi ({rate:.1f} maç/sn) -> {res['home_club']} {res['home_score']}-{res['away_score']} {res['away_club']}")
            else:
                pass
                
    elapsed = time.time() - start_time
    print(f"[✓] {saved} maç, esameleri ve olaylarıyla birlikte başarıyla güncellendi! ({elapsed:.1f} sn)")
    conn.close()

def sync_player_season_stats_2026(conn):
    print("\n" + "=" * 70)
    print(" 🔄 ADIM 3: 2026-2027 SEZON İSTATİSTİKLERİ VE OYUNCULAR SENKRONİZE EDİLİYOR")
    print("=" * 70)
    
    cur = conn.cursor()
    # 1. Ensure all players appearing in match_lineups have a row in players
    cur.execute("""
        SELECT DISTINCT license_no, player_name, club_name
        FROM match_lineups
        WHERE license_no != '' AND license_no IS NOT NULL
    """)
    lineup_players = cur.fetchall()
    
    cur.execute("SELECT license_no, id, ktff_player_id FROM players WHERE license_no != ''")
    existing_players = {str(r[0]): (r[1], r[2] if r[2] else (9000000 + r[1])) for r in cur.fetchall()}
    
    new_players_added = 0
    for lic, pname, cname in lineup_players:
        if str(lic) not in existing_players:
            cur.execute("""
                INSERT INTO players (license_no, name, current_club, nationality, status)
                VALUES (?, ?, ?, 'KKTC', 'Aktif')
            """, (lic, pname, cname))
            new_id = cur.lastrowid
            new_kpid = 9000000 + new_id
            cur.execute("UPDATE players SET ktff_player_id = ? WHERE id = ?", (new_kpid, new_id))
            existing_players[str(lic)] = (new_id, new_kpid)
            new_players_added += 1
            
    cur.execute("UPDATE players SET ktff_player_id = 9000000 + id WHERE ktff_player_id IS NULL OR ktff_player_id = 0")
    conn.commit()
    print(f"[*] Veritabanına yeni eklenen futbolcu sayısı: {new_players_added}")

    # 2. Aggregate appearances and events for 2026-2027 directly from match_lineups and match_events
    print("[*] 2026-2027 maç esamelerinden sezonluk istatistikler toplanıyor...")
    
    # Calculate appearances per license_no for 2026-2027
    cur.execute("""
        SELECT 
            l.license_no,
            SUM(l.is_starter) as starters,
            SUM(CASE WHEN l.is_starter = 0 AND l.minutes_played > 0 THEN 1 ELSE 0 END) as sub_ins,
            SUM(CASE WHEN l.is_starter = 0 AND l.minutes_played = 0 THEN 1 ELSE 0 END) as bench_unused,
            SUM(CASE WHEN l.minutes_played > 0 THEN 1 ELSE 0 END) as total_played
        FROM match_lineups l
        JOIN matches m ON l.match_id = m.id
        WHERE m.season = '2026-2027' AND l.license_no != ''
        GROUP BY l.license_no
    """)
    app_stats = {str(r[0]): r for r in cur.fetchall()}

    # Calculate goals and cards per license_no or player_name for 2026-2027
    cur.execute("""
        SELECT 
            l.license_no,
            SUM(CASE WHEN e.event_type IN ('goal', 'penalty') THEN 1 ELSE 0 END) as goals,
            SUM(CASE WHEN e.event_type = 'yellow_card' THEN 1 ELSE 0 END) as yellows,
            SUM(CASE WHEN e.event_type = 'red_card' THEN 1 ELSE 0 END) as reds
        FROM match_events e
        JOIN matches m ON e.match_id = m.id
        JOIN match_lineups l ON e.match_id = l.match_id AND LOWER(TRIM(l.player_name)) = LOWER(TRIM(e.player_name))
        WHERE m.season = '2026-2027' AND l.license_no != ''
        GROUP BY l.license_no
    """)
    event_stats = {str(r[0]): r for r in cur.fetchall()}

    # Update player_season_stats for 2026-2027
    updated_stats_count = 0
    for lic, (pid, k_pid) in existing_players.items():
        if lic in app_stats or lic in event_stats:
            app = app_stats.get(lic)
            ev = event_stats.get(lic)
            
            starters = app[1] if app else 0
            sub_ins = app[2] if app else 0
            bench = app[3] if app else 0
            total_played = app[4] if app else 0
            total_squad = starters + sub_ins + bench
            
            goals = ev[1] if ev else 0
            yellows = ev[2] if ev else 0
            reds = ev[3] if ev else 0
            
            cur.execute("SELECT id FROM player_season_stats WHERE ktff_player_id = ? AND season = '2026-2027'", (k_pid,))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    UPDATE player_season_stats SET
                        player_id = ?,
                        goals = MAX(goals, ?),
                        yellow_cards = MAX(yellow_cards, ?),
                        red_cards = MAX(red_cards, ?),
                        starter_matches = MAX(starter_matches, ?),
                        sub_in_matches = MAX(sub_in_matches, ?),
                        bench_unused_matches = MAX(bench_unused_matches, ?),
                        total_played_matches = MAX(total_played_matches, ?),
                        total_squad_matches = MAX(total_squad_matches, ?)
                    WHERE id = ?
                """, (pid, goals, yellows, reds, starters, sub_ins, bench, total_played, total_squad, row[0]))
            else:
                cur.execute("""
                    INSERT INTO player_season_stats (
                        player_id, ktff_player_id, season, goals, yellow_cards, red_cards,
                        starter_matches, sub_in_matches, bench_unused_matches,
                        total_played_matches, total_squad_matches
                    )
                    VALUES (?, ?, '2026-2027', ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pid, k_pid, goals, yellows, reds, starters, sub_ins, bench, total_played, total_squad))
            updated_stats_count += 1

    conn.commit()
    print(f"[✓] {updated_stats_count} futbolcunun 2026-2027 sezon istatistikleri başarıyla güncellendi.")

def main():
    start_all = time.time()
    conn = get_connection()
    client = KTFFClient(use_cache=False, delay_seconds=0.04)
    
    # Step 1: Scan
    matches_to_scrape = scan_for_matches_needing_update(client, conn)
    
    # Step 2: Scrape & Save
    if matches_to_scrape:
        run_match_updates(matches_to_scrape, workers=8)
    else:
        print("[✓] Tüm maçlar zaten veritabanında en güncel haliyle mevcut.")
        
    # Step 3: Sync Season Stats
    sync_player_season_stats_2026(conn)
    conn.close()

    # Step 4: Recalculate Skills
    print("\n" + "=" * 70)
    print(" ⚡ ADIM 4: OYUNCU BECERİ (SKILL) FORMÜLLERİ YENİDEN HESAPLANIYOR")
    print("=" * 70)
    from analytics.calculate_player_skills import calculate_skills
    calculate_skills()

    # Step 5: Rebuild HGNN Embeddings
    print("\n" + "=" * 70)
    print(" 🧠 ADIM 5: HGNN GRAFİĞİ VE YATAY VEKTÖRLER (EMBEDDINGS) YENİLENİYOR")
    print("=" * 70)
    from recommender.hgnn_model import train_hgnn
    train_hgnn(epochs=80)

    total_time = time.time() - start_all
    print("\n" + "=" * 70)
    print(f" 🎉 TÜM VERİTABANI VE MODEL GÜNCELLEMESİ BAŞARIYLA TAMAMLANDI! ({total_time:.1f} sn)")
    print("=" * 70)

if __name__ == "__main__":
    main()
