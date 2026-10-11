import sys
import os
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

# Ensure UTF-8 console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_connection, init_db
from scraper.ktff_client import KTFFClient
from scraper.scrape_clubs import parse_club_detail

# Official 2026-2027 Season Clubs
LEAGUE_CLUBS = {
    "AKSA Süper Lig": [
        "Alsancak Yeşilova SK",
        "Aslanköy GSD",
        "Baf Ülkü Yurdu",
        "China Bazaar Gençlik Gücü TSK",
        "Cihangir GSK",
        "Değirmenlik SK",
        "Doğan Türk Birliği",
        "Dumlupınar TSK",
        "Esentepe KSKK",
        "Karşıyaka SK",
        "Küçük Kaymaklı TSK",
        "Mağusa Türk Gücü",
        "Mesarya SK",
        "Yenicami AK",
        "Çetinkaya TSK"
    ],
    "AKSA 1.Lig": [
        "Akdoğan SK",
        "DND L. Gençler Birliği SK",
        "Düzkaya KOSK",
        "Geçitkale GSK",
        "Gönyeli SK",
        "Göçmenköy İYSK",
        "Karaoğlanoğlu SK",
        "Lapta Türk Birliği SK",
        "Lefke TSK",
        "M. Hacıali Yılmazköy SK",
        "Maraş GSK",
        "Mormenekşe GBSK",
        "Türk Ocağı Limasol SK",
        "Yeniboğaziçi DSK",
        "Çello Dikmen Gücü SK"
    ]
}

def search_club_url(client, club_name):
    """Searches KTFF database for club profile URL."""
    # Common search queries if name has sponsor prefixes
    search_terms = [club_name]
    if "Gençlik Gücü" in club_name:
        search_terms.append("Gençlik Gücü")
    elif "Gençler Birliği" in club_name:
        search_terms.append("Gençler Birliği")
    elif "Yılmazköy" in club_name:
        search_terms.append("Yılmazköy")
    elif "Dikmen Gücü" in club_name:
        search_terms.append("Dikmen Gücü")

    for term in search_terms:
        query = urllib.parse.quote(term)
        url = f"https://ktff.org/bilgi-bankasi/kulupler?q={query}"
        soup = client.get_soup(url)
        if not soup:
            continue
        links = [a["href"] for a in soup.find_all("a", href=True) if "/bilgi-bankasi/kulupler/" in a["href"] and "Detay" in a.text]
        if links:
            return links[0]
            
    return None

def run_scrape_current_clubs():
    """
    Scrapes and updates the SQLite 'clubs' table so that it ONLY contains
    the official 2026-2027 AKSA Süper Lig and AKSA 1. Lig clubs.
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    client = KTFFClient(delay_seconds=0.2)

    print("=" * 70)
    print(" 🏟️  SCOUTME: 2026-2027 AKSA SÜPER LİG & 1. LİG KULÜPLERİ GÜNCELLEMESİ")
    print("=" * 70)

    club_records = []

    for league_name, clubs in LEAGUE_CLUBS.items():
        print(f"\n[*] Processing {league_name} ({len(clubs)} kulüp)...")
        for club_name in clubs:
            club_url = search_club_url(client, club_name)
            detail = None
            if club_url:
                detail = parse_club_detail(client, club_url)

            if detail:
                club_records.append({
                    "name": detail["name"] or club_name,
                    "slug": detail["slug"] or club_name.lower().replace(" ", "-"),
                    "city": detail["city"],
                    "stadium_name": detail["stadium_name"],
                    "president": detail["president"],
                    "phone": detail["phone"],
                    "address": detail["address"],
                    "league_name": league_name
                })
                print(f"    [+] {detail['name']:<28} | Şehir: {detail['city']:<12} | Başkan: {detail['president']}")
            else:
                # Fallback if no profile detail found
                slug = club_name.lower().replace(" ", "-")
                club_records.append({
                    "name": club_name,
                    "slug": slug,
                    "city": "",
                    "stadium_name": "",
                    "president": "",
                    "phone": "",
                    "address": "",
                    "league_name": league_name
                })
                print(f"    [!] {club_name:<28} | (Temel kayıt eklendi)")

    print(f"\n[*] Veritabanı güncelleniyor: 'clubs' tablosu sıfırlanıp sadece bu {len(club_records)} kulüp yazılıyor...")
    cur.execute("DELETE FROM clubs;")

    for c in club_records:
        cur.execute("""
            INSERT INTO clubs (name, slug, city, stadium_name, president, phone, address, league_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            c["name"],
            c["slug"],
            c["city"],
            c["stadium_name"],
            c["president"],
            c["phone"],
            c["address"],
            c["league_name"]
        ))

    conn.commit()

    print("\n" + "=" * 70)
    print("          📊 GÜNCEL 2026-2027 SEZONU KULÜP LİSTESİ")
    print("=" * 70)
    rows = cur.execute("SELECT id, name, league_name, city, president, stadium_name FROM clubs ORDER BY league_name DESC, name ASC").fetchall()
    for idx, r in enumerate(rows, 1):
        print(f" {idx:2d}. {r['name']:<28} | {r['league_name']:<15} | {r['city']:<12} | {r['president']}")
    print("=" * 70)
    print(f"[✓] Toplam {len(rows)} kulüp 'clubs' tablosuna başarıyla kaydedildi.")

    conn.close()

if __name__ == "__main__":
    run_scrape_current_clubs()
