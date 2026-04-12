import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape, scrape_playwright
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_url(name, url, use_pw=False):
    print(f"\n=== {name} ===")
    if use_pw:
        result = scrape_playwright(url)
        if result:
            html = result.get('data', '')
        else:
            print("  Playwright FAILED")
            return
    else:
        result = scrape(url)
        if not result or not result.get('success'):
            print("  FAILED")
            return
        html = result.get('data', '')
    
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
    print(f"  HTML: {len(html)} chars, meaningful lines: {len(lines)}")
    for l in lines[5:25]:
        try:
            print(f"    {l[:90]}")
        except:
            pass

# LBB -ladbible.com — community-focused media with viral ads
test_url("LBB Homepage", 'https://www.ladbible.com/', use_pw=False)

# Pinterest
test_url("Pinterest ads search", 'https://www.pinterest.com/search/pins/?q=online%20ads', use_pw=False)

# Behance - creative portfolio platform
test_url("Behance advertising", 'https://www.behance.net/search?search=advertising%20campaign', use_pw=False)

# Showstream-like: Telegraph creative archive
test_url("Telegraph ads", 'https://www.telegraph.co.uk/money/how-to-save/advertising/', use_pw=False)
