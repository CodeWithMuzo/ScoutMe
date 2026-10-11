import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection
from scraper.ktff_client import KTFFClient

def parse_coach_detail(client, coach_url):
    soup = client.get_soup(coach_url)
    if not soup:
        return None
        
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name or name == "----- -----":
        return None
        
    try:
        ktff_coach_id = int(coach_url.split("?")[0].rstrip("/").split("/")[-1])
    except ValueError:
        return None
        
    license_no = ""
    role = ""
    club_name = ""
    nationality = ""
    birth_date = ""
    birth_place = ""
    gender = "Erkek"
    
    # Parse dl elements
    for dl in soup.find_all("dl"):
        dts = [dt.get_text(strip=True) for dt in dl.find_all("dt")]
        dds = [dd.get_text(strip=True) for dd in dl.find_all("dd")]
        for term, val in zip(dts, dds):
            if "Lisans" in term:
                license_no = val
            elif "Görev" in term:
                role = val
            elif "Kulüp" in term:
                club_name = val if val != "-" else ""
            elif "Uyruk" in term:
                nationality = val
            elif "Doğum Tarihi" in term:
                birth_date = val
            elif "Doğum Yeri" in term:
                birth_place = val
            elif "Cinsiyet" in term:
                gender = val

    # Fallback to info divs
    for div in soup.find_all("div", class_=lambda c: c and "info" in str(c)):
        text = div.get_text(" ", strip=True)
        if "Lisans No" in text and not license_no:
            license_no = text.replace("Lisans No", "").strip()
        elif "Görev" in text and not role:
            role = text.replace("Görev", "").strip()
        elif "Kulüp" in text and not club_name:
            club_name = text.replace("Kulüp", "").strip()
        elif "Doğum Tarihi" in text and not birth_date:
            birth_date = text.replace("Doğum Tarihi", "").strip()
        elif "Doğum Yeri" in text and not birth_place:
            birth_place = text.replace("Doğum Yeri", "").strip()

    return {
        "ktff_coach_id": ktff_coach_id,
        "name": name,
        "license_no": license_no,
        "role": role,
        "club_name": club_name,
        "nationality": nationality,
        "birth_date": birth_date,
        "birth_place": birth_place,
        "gender": gender
    }

def scrape_all_coaches(max_pages=20):
    client = KTFFClient(delay_seconds=0.3)
    conn = get_connection()
    cur = conn.cursor()
    
    print("[*] Starting KTFF Coaches Scraping...")
    total_saved = 0
    
    for page in range(1, max_pages + 1):
        page_url = f"https://ktff.org/bilgi-bankasi/teknik-direktorler?page={page}"
        print(f"[-] Fetching coaches page {page}...")
        soup = client.get_soup(page_url)
        if not soup:
            break
            
        coach_links = []
        for a in soup.find_all("a", href=True):
            if "/bilgi-bankasi/teknik-direktorler/" in a["href"] and "Detay" in a.text:
                coach_links.append(a["href"])
                
        if not coach_links:
            print(f"[+] Reached end of coaches list at page {page}.")
            break
            
        print(f"    Found {len(coach_links)} coaches on page {page}.")
        for curl in coach_links:
            data = parse_coach_detail(client, curl)
            if data and data["name"]:
                cur.execute("""
                    INSERT INTO coaches (ktff_coach_id, name, license_no, role, club_name, nationality, birth_date, birth_place, gender)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ktff_coach_id) DO UPDATE SET
                        name=excluded.name,
                        license_no=excluded.license_no,
                        role=excluded.role,
                        club_name=excluded.club_name,
                        nationality=excluded.nationality,
                        birth_date=excluded.birth_date,
                        birth_place=excluded.birth_place,
                        gender=excluded.gender;
                """, (
                    data["ktff_coach_id"],
                    data["name"],
                    data["license_no"],
                    data["role"],
                    data["club_name"],
                    data["nationality"],
                    data["birth_date"],
                    data["birth_place"],
                    data["gender"]
                ))
                total_saved += 1
                
        conn.commit()
        print(f"    Total coaches saved so far: {total_saved}")
        
    conn.close()
    print(f"[SUCCESS] Scraped and saved {total_saved} KTFF coaches into database!")

if __name__ == "__main__":
    scrape_all_coaches()
