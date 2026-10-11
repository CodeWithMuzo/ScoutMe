import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scraper.ktff_client import KTFFClient
from bs4 import BeautifulSoup

client = KTFFClient()
html = client.get_html("https://ktff.org/maclar/21265")
soup = BeautifulSoup(html, "html.parser")

print("--- ALL TEXT HEADINGS AND HERO ELEMENTS ---")
for tag in soup.find_all(["div", "span", "p", "li"]):
    txt = tag.get_text(" ", strip=True)
    if any(k in txt.lower() for k in ["hakem", "stad", "saha"]):
        if len(txt) < 120:
            print(f"[{tag.name}] class='{tag.get('class')}' -> {txt}")
