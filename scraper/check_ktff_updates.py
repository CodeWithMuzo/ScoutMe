"""
check_ktff_updates.py
=====================
Monitors ktff.org to detect when new match scores, lineups, and events are published.
Compares live KTFF website data against local ktff.db database.
"""

import sys
import os
import re
import sqlite3
from bs4 import BeautifulSoup

# Ensure UTF-8 console output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Ensure ScoutMe root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scraper.ktff_client import KTFFClient

def get_existing_db_matches():
    db_path = os.path.join(BASE_DIR, "data", "ktff.db")
    if not os.path.exists(db_path):
        return set(), None
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT ktff_match_id FROM matches WHERE ktff_match_id IS NOT NULL")
    existing_ids = {row[0] for row in c.fetchall()}
    
    c.execute("""
        SELECT season, league_name, match_date, home_club, away_club, home_score, away_score
        FROM matches
        WHERE season = '2026-2027' AND home_score IS NOT NULL
        ORDER BY id DESC LIMIT 1
    """)
    latest_played = c.fetchone()
    conn.close()
    return existing_ids, latest_played

def check_live_ktff_for_new_matches(season_id=13, comp_id=60, max_pages=3):
    client = KTFFClient(use_cache=False, delay_seconds=0.2)
    print("=" * 70)
    print("           KTFF CANLI MAÇ VE SKOR GÜNCELLEME DENETLEYİCİSİ")
    print("=" * 70)
    
    existing_ids, latest_db_match = get_existing_db_matches()
    print(f"[*] Veritabanındaki Toplam Kayıtlı Maç ID Sayısı : {len(existing_ids)}")
    if latest_db_match:
        print(f"[*] Veritabanımızdaki Son Oynanmış Maç       : {latest_db_match[2]} | {latest_db_match[3]} {latest_db_match[5]}-{latest_db_match[6]} {latest_db_match[4]}")
    print("-" * 70)
    print(f"[*] KTFF Canlı Web Sayfaları Taranıyor (2026-2027 Sezonu, AKSA Süper Lig)...")

    new_matches = []
    updated_scores = []
    scheduled_matches = []

    for page in range(1, max_pages + 1):
        url = f"https://ktff.org/bilgi-bankasi/maclar?season={season_id}&competition={comp_id}&page={page}"
        soup = client.get_soup(url)
        if not soup:
            break
            
        links = [a.get("href") for a in soup.find_all("a", href=True) if "/maclar/" in a.get("href")]
        links = list(dict.fromkeys(links))
        
        for murl in links:
            try:
                mid = int(murl.split("?")[0].rstrip("/").split("/")[-1])
            except ValueError:
                continue
                
            msoup = client.get_soup(murl)
            if not msoup:
                continue
                
            title = msoup.title.string.strip() if msoup.title else ""
            clean_title = title.split("|")[0].strip()
            text = msoup.get_text()
            
            # Check score pattern e.g. "4-1" or "0-0"
            score_m = re.search(r'(\d+)\s*-\s*(\d+)', clean_title)
            date_m = re.search(r'(\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+2026)', text)
            date_str = date_m.group(1) if date_m else "Tarih Belirtilmemiş"
            
            # Check lineup presence
            has_lineup = bool(msoup.find_all("table", class_=lambda c: c and "lineup" in c.lower()) or "İlk 11" in text or "Esame" in text)
            
            item = {
                "id": mid,
                "url": murl,
                "title": clean_title,
                "date": date_str,
                "score": f"{score_m.group(1)}-{score_m.group(2)}" if score_m else None,
                "has_lineup": has_lineup,
                "is_in_db": mid in existing_ids
            }
            
            if score_m:
                if mid not in existing_ids:
                    new_matches.append(item)
                else:
                    updated_scores.append(item)
            else:
                scheduled_matches.append(item)

    print("\n" + "=" * 70)
    print("                      TARAMA SONUÇLARI")
    print("=" * 70)
    print(f"1. Veritabanında Olmayan YENİ Oynanmış Maçlar    : {len(new_matches)}")
    print(f"2. Veritabanında Mevcut Oynanmış Maçlar         : {len(updated_scores)}")
    print(f"3. Henüz Oynanmamış / Fikstürdeki Gelecek Maçlar: {len(scheduled_matches)}")
    print("-" * 70)

    if new_matches:
        print("\n⚡ YENİ EKLENMİŞ / OYNANMIŞ MAÇLAR (Veritabanına eklenmeye hazır):")
        for m in new_matches[:10]:
            print(f"  • [ID: {m['id']}] {m['date']} -> {m['title']} (Skor: {m['score']}) | Kadro: {'Var' if m['has_lineup'] else 'Henüz Yok'}")
    else:
        print("\n✅ Veritabanımız güncel! Taranan sayfalarda skoru girilmiş olup DB'de bulunmayan yeni maç yok.")

    if scheduled_matches:
        print("\n📅 YAKLAŞAN / SKORU BEKLENEN MAÇLAR (İlk 5):")
        for m in scheduled_matches[:5]:
            print(f"  • [ID: {m['id']}] {m['date']} -> {m['title']}")

    return new_matches, scheduled_matches

if __name__ == '__main__':
    check_live_ktff_for_new_matches(max_pages=2)
