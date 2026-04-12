import sys
sys.path.insert(0, '..\\web-scraper')
from web_scraper import WebScraper

scraper = WebScraper()
url = 'https://www.adsoftheworld.com/campaigns/helmet-has-always-been-cool'
result = scraper.extract(url, extract_type='article')
print('Title:', result.get('title', 'NONE'))
text = result.get('extracted', '')
print('Text length:', len(text))
print('First 800 chars:')
print(text[:800])
scraper.close()
