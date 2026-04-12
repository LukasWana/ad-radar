import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape
from bs4 import BeautifulSoup

print("=== TikTok Creative Center ===")
# TikTok Creative Center - top ads
tt_urls = [
    'https://ads.tiktok.com/business/en_US/creative-center/board/hashtag',
    'https://ads.tiktok.com/business/en_US/creative-center/detail/video/7267888619748039941',
]
for url in tt_urls:
    print(f"\n-- {url[:60]}...")
    result = scrape(url)
    if not result.get('success'):
        print(f"  FAILED")
        continue
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
    print(f"  HTML: {len(html)} chars, meaningful lines: {len(lines)}")
    for l in lines[:15]:
        print(f"    {l}")

print("\n\n=== SpyFu ===")
# SpyFu - PPC ads
spyfu_urls = [
    'https://www.spyfu.com/competitors/competitor-keywords/alza.cz',
    'https://www.spyfu.com/competitors/ppc-competitor-analysis/alza.cz',
]
for url in spyfu_urls:
    print(f"\n-- {url[:60]}...")
    result = scrape(url)
    if not result.get('success'):
        print(f"  FAILED")
        continue
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
    print(f"  HTML: {len(html)} chars, meaningful lines: {len(lines)}")
    for l in lines[:15]:
        print(f"    {l}")
