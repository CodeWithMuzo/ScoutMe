import sqlite3
import os
import pandas as pd
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ktff.db")

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

def audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("=" * 60)
    print("        [AUDIT] SCOUTME KTFF DATABASE COMPREHENSIVE AUDIT")
    print("=" * 60)
    
    # 1. Table Counts
    print("\n[1] TABLE RECORD COUNTS:")
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    for t in tables:
        cnt = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  • {t:<26} : {cnt:>6} rows")
        
    # 2. Players Table Deep Dive
    print("\n[2] PLAYERS TABLE ANALYSIS:")
    df_players = pd.read_sql_query("SELECT * FROM players", conn)
    total_p = len(df_players)
    print(f"  • Total Registered Players : {total_p}")
    print("  • Null/Missing Values:")
    for col in df_players.columns:
        null_cnt = df_players[col].isnull().sum()
        if null_cnt > 0:
            print(f"    - {col:<20} : {null_cnt:>5} nulls ({null_cnt/total_p*100:.1f}%)")
        else:
            print(f"    - {col:<20} : 0 nulls (100% full)")
            
    print("\n  • Position Category Breakdown:")
    pos_cat = df_players['position_category'].value_counts(dropna=False)
    for cat, c in pos_cat.items():
        print(f"    - {str(cat):<6} : {c:>5} ({c/total_p*100:.1f}%)")
        
    print("\n  • Position Source Breakdown:")
    pos_src = df_players['position_source'].value_counts(dropna=False)
    for src, c in pos_src.items():
        print(f"    - {str(src):<25} : {c:>5} ({c/total_p*100:.1f}%)")
        
    print(f"  • Position Confidence Mean : {df_players['position_confidence'].mean():.2f} (Min: {df_players['position_confidence'].min()}, Max: {df_players['position_confidence'].max()})")
    
    # 3. Player Season Stats Deep Dive
    print("\n[3] PLAYER SEASON STATS ANALYSIS:")
    df_stats = pd.read_sql_query("SELECT * FROM player_season_stats", conn)
    print(f"  • Total Season Stats Rows : {len(df_stats)}")
    print(f"  • Distinct Players in Stats: {df_stats['player_id'].nunique()} / {total_p}")
    print(f"  • Distinct Seasons Covered : {df_stats['season'].unique().tolist()}")
    
    print("\n  • Breakdown by Season:")
    for s, cnt in df_stats['season'].value_counts().items():
        print(f"    - {s:<15} : {cnt:>5} player records")
        
    # Aggregate stats per player
    agg = df_stats.groupby('player_id').agg({
        'total_played_matches': 'sum',
        'starter_matches': 'sum',
        'sub_in_matches': 'sum',
        'bench_unused_matches': 'sum',
        'goals': 'sum',
        'yellow_cards': 'sum',
        'red_cards': 'sum'
    })
    
    played_players = (agg['total_played_matches'] > 0).sum()
    zero_game_players = total_p - played_players
    print(f"\n  • Players with at least 1 match played : {played_players:>5} ({played_players/total_p*100:.1f}%)")
    print(f"  • Players with 0 matches played (inactive/bench/reserve): {zero_game_players:>5} ({zero_game_players/total_p*100:.1f}%)")
    
    print(f"  • Players with at least 1 goal scored  : {(agg['goals'] > 0).sum():>5}")
    print(f"  • Total Goals Recorded across all stats: {agg['goals'].sum()}")
    print(f"  • Total Yellow Cards recorded          : {agg['yellow_cards'].sum()}")
    print(f"  • Total Red Cards recorded             : {agg['red_cards'].sum()}")
    
    # Distribution of matches played among active players
    active_agg = agg[agg['total_played_matches'] > 0]
    print("\n  • Played Matches Distribution (among active players):")
    print(f"    - Min: {active_agg['total_played_matches'].min()}, Median: {active_agg['total_played_matches'].median()}, Mean: {active_agg['total_played_matches'].mean():.1f}, Max: {active_agg['total_played_matches'].max()}")
    print(f"    - Players with >= 5 matches played   : {(active_agg['total_played_matches'] >= 5).sum()}")
    print(f"    - Players with >= 10 matches played  : {(active_agg['total_played_matches'] >= 10).sum()}")
    print(f"    - Players with >= 20 matches played  : {(active_agg['total_played_matches'] >= 20).sum()}")
    
    # 4. Matches, Lineups and Events
    print("\n[4] MATCH-LEVEL (LINEUPS & EVENTS) AUDIT:")
    match_cnt = conn.execute("SELECT count(*) FROM matches").fetchone()[0]
    lineup_cnt = conn.execute("SELECT count(*) FROM match_lineups").fetchone()[0]
    event_cnt = conn.execute("SELECT count(*) FROM match_events").fetchone()[0]
    print(f"  • Matches count in DB : {match_cnt}")
    print(f"  • Lineups count in DB : {lineup_cnt}")
    print(f"  • Events count in DB  : {event_cnt}")
    
    # 5. Clubs and Coaches
    print("\n[5] CLUBS & COACHES AUDIT:")
    club_cnt = conn.execute("SELECT count(*) FROM clubs").fetchone()[0]
    coach_cnt = conn.execute("SELECT count(*) FROM coaches").fetchone()[0]
    print(f"  • Current Clubs : {club_cnt} (Target: 30 Super Lig + 1. Lig)")
    print(f"  • Head Coaches  : {coach_cnt} (Target: 36 A Team Head Coaches)")
    
    conn.close()

if __name__ == "__main__":
    audit()
