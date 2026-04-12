import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape_playwright
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def parse_behance(name, url, wait_sec=5):
    print(f"\n=== {name} ===")
    result = scrape_playwright(url)
    if not result:
        print("  FAILED")
        return
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find project cards - Behance uses specific class patterns
    # Look for links to project pages
    project_links = soup.find_all('a', href=lambda h: h and '/project/' in str(h))
    print(f"  Project links: {len(project_links)}")
    for link in project_links[:5]:
        href = link.get('href', '')
        title = link.get_text(strip=True)[:60]
        print(f"    {href} | {title}")
    
    # Find images with their containers
    img_containers = soup.find_all('img', src=lambda s: s and 'behance.net' in str(s))
    print(f"  Behance images: {len(img_containers)}")
    for img in img_containers[:3]:
        src = img.get('src', '')[:80]
        alt = img.get('alt', '')[:60]
        print(f"    src: {src}")
        print(f"    alt: {alt}")
    
    # Try to find project titles from text
    import re
    text = soup.get_text(separator=' ', strip=True)
    
    # Look for ad-related keywords
    ad_keywords = ['campaign', 'advertising', '品牌', '广告', 'print', 'outdoor', 'tv commercial', 'brand']
    found_keywords = [k for k in ad_keywords if k.lower() in text.lower()]
    print(f"  Ad keywords found: {found_keywords}")

# Search queries relevant to advertising
queries = [
    ('Behance advertising campaigns', 'https://www.behance.net/search?content=images&search=advertising%20campaign'),
    ('Behance print ads', 'https://www.behance.net/search?content=images&search=print%20advertisement'),
    ('Behance outdoor ads', 'https://www.behance.net/search?content=images&search=outdoor%20advertising'),
    ('Behance TV commercials', 'https://www.behance.net/search?content=videos&search=tv%20commercial'),
]

for name, url in queries:
    parse_behance(name, url, wait_sec=5)
