import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape
from bs4 import BeautifulSoup

# Facebook - check what we got with fetch
print("=== Facebook Ad Library (fetch) ===")
result = scrape("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=CZ&media_type=image")
html = result.get('data', '')
soup = BeautifulSoup(html, 'html.parser')
print(f"Title: {soup.title.string if soup.title else 'NONE'}")
text = soup.get_text(separator='\n', strip=True)
# Check for login/checkpoint
if 'přihlásit' in text.lower() or 'log in' in text.lower() or 'checkpoint' in text.lower():
    print("LOGIN WALL DETECTED")
lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5][:30]
print(f"Lines: {lines}")

# Google Ad Transparency - try with proper format
print("\n=== Google Ad Transparency (Czech brands) ===")
advertisers = ['alza.cz', 'rossmann.cz', 'notino.cz', 'mall.cz', 'czc.cz']
for adv in advertisers:
    url = f"https://adstransparency.google.com/advertiser/{adv}"
    result = scrape(url)
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    found = 'Nepodařilo se najít inzerenta' not in text and 'Advertiser Details' in text
    print(f"  {adv}: {len(html)} chars, {'FOUND' if found else 'NOT FOUND'}")