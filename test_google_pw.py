import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape_playwright
from bs4 import BeautifulSoup

advertisers = [
    ('alza.cz', 'https://adstransparency.google.com/advertiser/ALZA.CZ'),
    ('rossmann.cz', 'https://adstransparency.google.com/advertiser/ROSSMANN.CZ'),
    ('notino.cz', 'https://adstransparency.google.com/advertiser/NOTINO.CZ'),
    ('mall.cz', 'https://adstransparency.google.com/advertiser/MALL.CZ'),
    ('czc.cz', 'https://adstransparency.google.com/advertiser/CZC.CZ'),
    ('planeo.cz', 'https://adstransparency.google.com/advertiser/PLANEOTEO.CZ'),
]

for name, url in advertisers:
    print(f"\n=== {name} ===")
    result = scrape_playwright(url)
    if not result:
        print("  FAILED: no result")
        continue
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
    print(f"  HTML: {len(html)} chars, lines: {len(lines)}")
    for l in lines[:20]:
        print(f"    {l}")
