import urllib.request
import re
from bs4 import BeautifulSoup

def check_league(comp, name, max_matches=10):
    url = f'https://ktff.org/bilgi-bankasi/maclar?season=13&competition={comp}&sort=newest&page=1'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'), 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True) if '/maclar/' in a['href'] and ('Maç' in a.text or '#' in a.text)]
    links = list(dict.fromkeys(links))[:max_matches]
    print(f'=== {name} ===')
    
    found_coaches = {}
    
    for m in links:
        try:
            m_req = urllib.request.Request(m, headers={'User-Agent': 'Mozilla/5.0'})
            m_soup = BeautifulSoup(urllib.request.urlopen(m_req, timeout=10).read().decode('utf-8'), 'html.parser')
            teams = [t.get_text(strip=True) for t in m_soup.find_all(class_=lambda c: c and 'match-hero__team-info' in str(c))]
            if len(teams) < 2:
                teams = [t.get_text(strip=True) for t in m_soup.find_all(class_=lambda c: c and 'team-info' in str(c))]
            home = teams[0] if len(teams) > 0 else 'Unknown Home'
            away = teams[1] if len(teams) > 1 else 'Unknown Away'
            
            l_req = urllib.request.Request(m + '?tab=lineups', headers={'User-Agent': 'Mozilla/5.0'})
            l_soup = BeautifulSoup(urllib.request.urlopen(l_req, timeout=10).read().decode('utf-8'), 'html.parser')
            groups = l_soup.find_all(class_='match-lineup__group')
            te_groups = [g for g in groups if 'Teknik Ekip' in g.get_text()]
            
            mid = m.split('/')[-1]
            print(f"Match {mid}: {home} vs {away} | TE groups: {len(te_groups)}")
            
            # Group 0 is home, Group 1 is away
            for idx, g in enumerate(te_groups):
                club = home if idx == 0 else away
                for r in g.find_all(class_='match-lineup__row'):
                    pname = r.find('strong').get_text(strip=True) if r.find('strong') else ''
                    role = r.find(class_='match-lineup__license').get_text(strip=True) if r.find(class_='match-lineup__license') else ''
                    if 'Teknik Direkt' in role and pname:
                        found_coaches[club] = (pname, role)
                        print(f"   -> {club}: {pname} [{role}]")
        except Exception as e:
            print(f"Error on match {m}: {e}")
            
    return found_coaches

if __name__ == '__main__':
    super_coaches = check_league('60', 'AKSA Super Lig', max_matches=8)
    birinci_coaches = check_league('62', 'AKSA 1.Lig', max_matches=8)
    print(f"\nTotal unique clubs found with TD in Super Lig: {len(super_coaches)}")
    print(f"Total unique clubs found with TD in 1. Lig: {len(birinci_coaches)}")
