import sys
sys.path.insert(0, '..\\web-scraper')
from web_scraper import WebScraper

scraper = WebScraper()

# Test editorial sources directly
print('=== Testing muz.li ===')
result = scraper.extract(
    'https://muz.li/inspiration/banner-examples/',
    extract_type='article'
)
print(f'Title: {result.get("title", "")[:100]}')
text = result.get('extracted', '')
print(f'Text length: {len(text)}')
print(f'First 500: {text[:500]}')
print(f'Error: {result.get("error", "none")}')

print('\n=== Testing bannerflow ===')
result = scraper.extract(
    'https://www.bannerflow.com/blog/display-advertising-best-banner-ads',
    extract_type='article'
)
print(f'Title: {result.get("title", "")[:100]}')
text = result.get('extracted', '')
print(f'Text length: {len(text)}')
print(f'First 500: {text[:500]}')
print(f'Error: {result.get("error", "none")}')

scraper.close()
