import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape, scrape_playwright
from bs4 import BeautifulSoup

# Try Google Ad Transparency with different approaches
urls = [
    # Base page with CZ region
    'https://adstransparency.google.com/?region=CZ',
    # Search approach
    'https://adstransparency.google.com/search?region=CZ&advertiser=alza',
    'https://adstransparency.google.com/search?advertiser=alza',
]

for url in urls:
    print(f"\n=== {url} ===")
    result = scrape(url)
    if not result.get('success'):
        print(f"  FAILED")
        continue
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
    print(f"  HTML: {len(html)} chars, meaningful lines: {len(lines)}")
    
    # Check for advertiser data
    if 'alza' in text.lower():
        print(f"  ✅ 'alza' FOUND in text")
    if 'nepodařilo' in text.lower():
        print(f"  ❌ 'nepodařilo' found")
    
    for l in lines[:25]:
        print(f"    {l[:100]}")

# Try playwright on base page
print("\n\n=== Playwright on base page ===")
result = scrape_playwright('https://adstransparency.google.com/?region=CZ')
if result:
    html = result.get('data', '')
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
    print(f"HTML: {len(html)} chars, meaningful lines: {len(lines)}")
    for l in lines[:40]:
        print(f"  {l[:100]}")
