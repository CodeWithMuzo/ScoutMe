import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scraper.ktff_client import KTFFClient

client = KTFFClient()
soup = client.get_soup("https://ktff.org/bilgi-bankasi/maclar")

for select in soup.find_all("select"):
    s_name = select.get("name")
    print(f"\nSelect dropdown: {s_name}")
    for opt in select.find_all("option"):
        val = opt.get("value")
        txt = opt.get_text(strip=True)
        if val:
            print(f"  value='{val}' -> {txt}")
