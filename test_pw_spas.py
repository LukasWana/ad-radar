import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape_playwright
from bs4 import BeautifulSoup
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def inspect_page(name, url, wait_sec=5):
    print(f"\n=== {name} ===")
    result = scrape_playwright(url)
    if not result:
        print("  FAILED")
        return
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check title
    title = soup.find('title')
    print(f"  Title: {title.get_text(strip=True) if title else 'NONE'}")
    
    # Check for images
    imgs = soup.find_all('img')
    print(f"  Images: {len(imgs)}")
    
    # Check for video
    videos = soup.find_all('video')
    print(f"  Videos: {len(videos)}")
    
    # Check for SVG (vector art)
    svgs = soup.find_all('svg')
    print(f"  SVG elements: {len(svgs)}")
    
    # Check meta tags for description
    desc = soup.find('meta', attrs={'name': 'description'})
    if desc:
        print(f"  Meta desc: {desc.get('content', '')[:100]}")
    
    # Get text preview - try to find any text
    text = soup.get_text(separator=' ', strip=True)
    words = [w for w in text.split() if len(w) > 3]
    print(f"  Text words (>3 chars): {len(words)}")
    if words:
        print(f"  Sample words: {words[:20]}")

inspect_page("LBB", 'https://www.ladbible.com/', wait_sec=5)
inspect_page("Pinterest", 'https://www.pinterest.com/search/pins/?q=online%20ads', wait_sec=5)
inspect_page("Behance", 'https://www.behance.net/search?search=advertising%20campaign', wait_sec=5)
