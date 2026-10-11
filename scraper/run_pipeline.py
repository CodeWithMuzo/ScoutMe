import sys
import os
import argparse

# Ensure utf-8 encoding on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db, get_connection
from scraper.scrape_leagues import init_leagues_and_seasons
from scraper.scrape_clubs import scrape_all_clubs
from scraper.scrape_coaches import scrape_all_coaches
from scraper.scrape_players import scrape_players_from_clubs
from scraper.scrape_matches import scrape_matches
from scraper.scrape_active_players import scrape_all_active_players
from scraper.scrape_league_coaches import run_scrape_coaches_for_current_season
from scraper.scrape_current_league_clubs import run_scrape_current_clubs

def show_database_status():
    conn = get_connection()
    print("=" * 55)
    print("       📊 SCOUTME KTFF DATABASE STATUS REPORT        ")
    print("=" * 55)
    
    tables = [
        ("Leagues", "leagues"),
        ("Seasons", "seasons"),
        ("Clubs", "clubs"),
        ("Coaches", "coaches"),
        ("Players", "players"),
        ("Player Career History", "player_career"),
        ("Player Season Statistics", "player_season_stats"),
        ("Matches", "matches"),
        ("Match Lineups (Appearances)", "match_lineups"),
        ("Match Events (Goals/Cards)", "match_events"),
    ]
    
    for label, tbl in tables:
        count = conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        print(f"  {label:<30} : {count:>6} records")
        
    print("=" * 55)
    
    # Show active clubs breakdown by city
    print("\n[+] Clubs by City (Top 5):")
    cities = conn.execute("SELECT city, count(*) as cnt FROM clubs WHERE city != '' GROUP BY city ORDER BY cnt DESC LIMIT 5").fetchall()
    for c in cities:
        print(f"    - {c['city']:<15} : {c['cnt']} clubs")

    # Show top goal scorers from events
    print("\n[+] Top Match Scorers (Sample from events):")
    scorers = conn.execute("""
        SELECT player_name, club_name, count(*) as goals
        FROM match_events
        WHERE event_type = 'goal'
        GROUP BY player_name, club_name
        ORDER BY goals DESC
        LIMIT 5
    """).fetchall()
    if scorers:
        for sc in scorers:
            print(f"    - {sc['player_name']} ({sc['club_name']}): {sc['goals']} goals")
    else:
        print("    (Run match scraping to populate scorers)")

    conn.close()

def main():
    parser = argparse.ArgumentParser(description="ScoutMe KTFF Data Pipeline Orchestrator")
    parser.add_argument("--all", action="store_true", help="Run entire scraping pipeline")
    parser.add_argument("--step", choices=["init", "leagues", "clubs", "current_clubs", "coaches", "current_coaches", "players", "matches", "active_players", "status"], default="status", help="Select pipeline step")
    parser.add_argument("--pages", type=int, default=250, help="Number of pages to scrape")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of active players to scrape")
    parser.add_argument("--workers", type=int, default=6, help="Number of concurrent worker threads")
    parser.add_argument("--clubs_limit", type=int, default=10, help="Number of clubs to scrape squads for")
    parser.add_argument("--season", type=str, default="10", help="KTFF Season ID (e.g. 10 for 2024-2025, 11 for 2025-2026)")
    
    args = parser.parse_args()
    
    if args.step == "status":
        show_database_status()
        return

    init_db()
    
    if args.all or args.step in ["init", "leagues"]:
        init_leagues_and_seasons()
        
    if args.step == "clubs":
        scrape_all_clubs(max_pages=args.pages)
        
    if args.step == "current_clubs":
        run_scrape_current_clubs()
        
    if args.step == "coaches":
        scrape_all_coaches(max_pages=args.pages)
        
    if args.step == "current_coaches":
        run_scrape_coaches_for_current_season()
        
    if args.all or args.step == "players":
        scrape_players_from_clubs(seasons=[args.season], limit_clubs=args.clubs_limit)
        
    if args.all or args.step == "active_players":
        scrape_all_active_players(max_pages=args.pages, limit=args.limit, workers=args.workers)
        
    if args.all or args.step == "matches":
        scrape_matches(season_id=args.season, max_pages=args.pages)
        
    show_database_status()

if __name__ == "__main__":
    main()
