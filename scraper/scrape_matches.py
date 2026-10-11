import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection
from scraper.ktff_client import KTFFClient

def parse_match(client, match_url):
    soup = client.get_soup(match_url)
    if not soup:
        return None
        
    try:
        ktff_match_id = int(match_url.split("?")[0].rstrip("/").split("/")[-1])
    except ValueError:
        return None

    # 1. Teams and scores
    team_info = soup.find_all(class_=lambda c: c and "match-hero__team-info" in str(c))
    if len(team_info) < 2:
        return None
        
    home_club = team_info[0].get_text(strip=True)
    away_club = team_info[1].get_text(strip=True)
    
    score_el = soup.find(class_=lambda c: c and "match-hero__score" in str(c))
    home_score = None
    away_score = None
    if score_el:
        score_text = score_el.get_text(strip=True)
        scores = re.findall(r"\d+", score_text)
        if len(scores) >= 2:
            home_score = int(scores[0])
            away_score = int(scores[1])
            
    # 2. Metadata (League, Date, Stadium)
    meta_el = soup.find(class_=lambda c: c and "match-hero__details" in str(c))
    league_name = ""
    match_date = ""
    match_time = ""
    stadium_name = ""
    status = "played" if home_score is not None else "scheduled"
    
    if meta_el:
        meta_txt = meta_el.get_text(" | ", strip=True)
        parts = [p.strip() for p in meta_txt.split("|")]
        for p in parts:
            if "Lig" in p or "Kupa" in p:
                league_name = p.split("-")[0].strip()
            elif any(month in p for month in ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]):
                date_time = p.split("-")
                match_date = date_time[0].strip()
                if len(date_time) > 1:
                    match_time = date_time[1].strip()
            elif "Stad" in p or "Saha" in p:
                stadium_name = p

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
        
        # Determine event type
        event_type = "unknown"
        if "Gol" in raw_text or "gol" in raw_text:
            event_type = "goal"
        elif "Penaltı" in raw_text:
            event_type = "penalty"
        elif "Kırmızı kart" in raw_text or "kırmızı" in raw_text.lower():
            event_type = "red_card"
        elif "Sarı kart" in raw_text or "sarı" in raw_text.lower():
            event_type = "yellow_card"
        elif "girdi" in raw_text or "çıktı" in raw_text:
            event_type = "sub"
            
        player_name = raw_text.split("/")[0].strip() if "/" in raw_text else raw_text
        for strip_w in ["Sarı kart", "Kırmızı kart", "Gol", "Penaltı"]:
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
        # Expected order: Home Starters, Home Bench, Home Staff, Away Starters, Away Bench, Away Staff
        current_side = "home"
        current_type = "starters"
        group_idx = 0
        
        for g in groups:
            title_node = g.find(class_=lambda c: c and "title" in str(c))
            title = title_node.get_text(strip=True) if title_node else ""
            if "Teknik Ekip" in title:
                continue
                
            is_starter = 1 if "İlk 11" in title else 0
            # If we already passed home bench and encounter ilk 11 again, it's away team
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
                    
                # Extract license no
                lic_match = re.search(r"Lisans No:\s*(\d+)", row.get_text())
                license_no = lic_match.group(1) if lic_match else ""
                
                clean_pname = re.sub(r"Lisans No:\s*\d+", "", pname).strip()
                
                # Extract shirt number
                row_text = row.get_text(" ", strip=True)
                num_match = re.match(r"^(\d+)\s+", row_text)
                shirt_number = num_match.group(1) if num_match else ""
                
                is_captain = 1 if re.search(r"\bK\b", row_text) else 0
                is_goalkeeper = 1 if re.search(r"\bKL\b", row_text) else 0
                
                # Calculate minutes played
                minutes_played = 90 if is_starter == 1 else 0
                sub_in_min = None
                sub_out_min = None
                
                # Check substitution events
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

def scrape_matches(season_id="10", max_pages=3):
    client = KTFFClient(delay_seconds=0.3)
    conn = get_connection()
    cur = conn.cursor()
    
    print(f"[*] Scraping KTFF Matches for Season ID {season_id} (up to {max_pages} pages)...")
    total_matches_saved = 0
    
    for page in range(1, max_pages + 1):
        list_url = f"https://ktff.org/bilgi-bankasi/maclar?season={season_id}&sort=newest&page={page}"
        print(f"[-] Fetching matches page {page}...")
        soup = client.get_soup(list_url)
        if not soup:
            break
            
        match_links = []
        for a in soup.find_all("a", href=True):
            if "/maclar/" in a["href"] and ("Maç Detayı" in a.text or "Maç Sonucu" in a.text or "#" in a.text):
                match_links.append(a["href"])
                
        # Deduplicate links
        match_links = list(dict.fromkeys(match_links))
        if not match_links:
            print(f"[+] Reached end of matches at page {page}.")
            break
            
        print(f"    Found {len(match_links)} matches on page {page}.")
        for m_url in match_links:
            mdata = parse_match(client, m_url)
            if not mdata:
                continue
                
            cur.execute("""
                INSERT INTO matches (ktff_match_id, season, league_name, home_club, away_club, home_score, away_score, match_date, match_time, stadium_name, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ktff_match_id) DO UPDATE SET
                    home_score=excluded.home_score,
                    away_score=excluded.away_score,
                    status=excluded.status;
            """, (
                mdata["ktff_match_id"],
                "2024-2025" if season_id == "10" else season_id,
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
                
            total_matches_saved += 1
            
        conn.commit()
        print(f"    Total matches saved so far: {total_matches_saved}")
        
    conn.close()
    print(f"[SUCCESS] Scraped and saved {total_matches_saved} matches into database!")

if __name__ == "__main__":
    scrape_matches(season_id="10", max_pages=1)
