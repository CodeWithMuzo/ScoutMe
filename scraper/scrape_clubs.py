import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection
from scraper.ktff_client import KTFFClient

def parse_club_detail(client, club_url):
    soup = client.get_soup(club_url)
    if not soup:
        return None
        
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        return None
        
    slug = club_url.split("?")[0].rstrip("/").split("/")[-1]
    
    city = ""
    stadium = ""
    president = ""
    phone = ""
    address = ""
    
    # Parse info items
    for item in soup.find_all("div", class_=lambda c: c and "info" in str(c)):
        text = item.get_text(" ", strip=True)
        if "Şehir" in text:
            city = text.replace("Şehir", "").strip()
        elif "Bölge" in text:
            stadium = text.replace("Bölge", "").strip()
        elif "Başkan" in text:
            president = text.replace("Başkan", "").strip()
        elif "Telefon" in text:
            phone = text.replace("Telefon", "").strip()
        elif "Adres" in text:
            address = text.replace("Adres", "").strip()

    # Also check dl tags if any were missed
    for dl in soup.find_all("dl"):
        dts = [dt.get_text(strip=True) for dt in dl.find_all("dt")]
        dds = [dd.get_text(strip=True) for dd in dl.find_all("dd")]
        for term, val in zip(dts, dds):
            if "Şehir" in term and not city:
                city = val
            elif "Bölge" in term and not stadium:
                stadium = val
            elif "Başkan" in term and not president:
                president = val
            elif "Telefon" in term and not phone:
                phone = val
            elif "Adres" in term and not address:
                address = val

    return {
        "name": name,
        "slug": slug,
        "city": city,
        "stadium_name": stadium,
        "president": president,
        "phone": phone,
        "address": address
    }

def scrape_all_clubs(max_pages=15):
    client = KTFFClient(delay_seconds=0.3)
    conn = get_connection()
    cur = conn.cursor()
    
    print("[*] Starting KTFF Clubs Scraping...")
    total_saved = 0
    
    for page in range(1, max_pages + 1):
        page_url = f"https://ktff.org/bilgi-bankasi/kulupler?page={page}"
        print(f"[-] Fetching clubs page {page}...")
        soup = client.get_soup(page_url)
        if not soup:
            break
            
        club_links = []
        for a in soup.find_all("a", href=True):
            if "/bilgi-bankasi/kulupler/" in a["href"] and "Detay" in a.text:
                club_links.append(a["href"])
                
        if not club_links:
            print(f"[+] Reached end of club list at page {page}.")
            break
            
        print(f"    Found {len(club_links)} clubs on page {page}.")
        for curl in club_links:
            data = parse_club_detail(client, curl)
            if data and data["name"]:
                cur.execute("""
                    INSERT INTO clubs (name, slug, city, stadium_name, president, phone, address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        name=excluded.name,
                        city=excluded.city,
                        stadium_name=excluded.stadium_name,
                        president=excluded.president,
                        phone=excluded.phone,
                        address=excluded.address;
                """, (
                    data["name"],
                    data["slug"],
                    data["city"],
                    data["stadium_name"],
                    data["president"],
                    data["phone"],
                    data["address"]
                ))
                total_saved += 1
                
        conn.commit()
        print(f"    Total clubs saved so far: {total_saved}")
        
    conn.close()
    print(f"[SUCCESS] Scraped and saved {total_saved} KTFF clubs into database!")

if __name__ == "__main__":
    scrape_all_clubs()
