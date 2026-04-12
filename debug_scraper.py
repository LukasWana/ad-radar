import sys
import urllib.request
import json

sys.path.insert(0, '..\\web-scraper')
from web_scraper import WebScraper

scraper = WebScraper()

# Test adsoftheworld - check discovery first
print('=== Testing URL validity ===')
test_urls = [
    'https://www.adsoftheworld.com/',
    'https://www.Campaignbrief.com/',
    'https://www.mediar.cz/galerie-reklamy/',
]

for url in test_urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            content = resp.read()[:500].decode('utf-8', errors='ignore')
            print(f'OK {status}: {url}')
            print(f'  Content preview: {content[:200]}...')
    except Exception as e:
        print(f'FAIL: {url} - {e}')

scraper.close()
