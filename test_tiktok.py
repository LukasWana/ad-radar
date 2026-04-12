import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape, scrape_playwright
from bs4 import BeautifulSoup

# TikTok has multiple paths - try popular hashtags/top ads
urls = [
    'https://ads.tiktok.com/business/en_US/creative-center',
    'https://ads.tiktok.com/business/en_US/creative-center/board/video',
    'https://www.tiktok.com/business/creative-portal',
]

for url in urls:
    print(f"\n=== {url} ===")
    result = scrape(url)
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # Check for actual content
    has_content = len([l for l in text.split() if len(l) > 10]) > 20
    print(f"  fetch: {len(html)} chars, has meaningful text: {has_content}")
    print(f"  Preview: {text[:300]}")
    
    # Try playwright
    result2 = scrape_playwright(url)
    if result2:
        html2 = result2.get('data', '')
        soup2 = BeautifulSoup(html2, 'html.parser')
        text2 = soup2.get_text(separator=' ', strip=True)
        has_content2 = len([l for l in text2.split() if len(l) > 10]) > 20
        print(f"  playwright: {len(html2)} chars, has meaningful text: {has_content2}")
        print(f"  Preview: {text2[:300]}")
