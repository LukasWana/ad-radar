import sys
import urllib.request
sys.path.insert(0, '..\\web-scraper')
from web_scraper import WebScraper

scraper = WebScraper()

# Test campaign URLs from discovery
print('=== Direct campaign URL check ===')
campaign_urls = [
    'https://www.adsoftheworld.com/campaigns/helmet-has-always-been-a-good-idea-1676',
    'https://www.adsoftheworld.com/campaigns/nothing-stops-women-2390',
]
for url in campaign_urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f'OK {resp.status}: {url}')
    except Exception as e:
        print(f'FAIL: {url} - {e}')

scraper.close()
