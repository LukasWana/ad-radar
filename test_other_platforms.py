import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from scraper_manager import scrape
from bs4 import BeautifulSoup

# Test LinkedIn and other social platforms
platforms = [
    ('LinkedIn Ads', 'https://www.linkedin.com/business/marketing/blog/creativity/how-brands-are-using-linkedin-ads'),
    ('Pinterest', 'https://ads.pinterest.com/api/v2/pinterest_business_account/ads/'),
    ('Mastodon', 'https://mastodon.social/@GitHubLab/'),
]

for name, url in platforms:
    print(f"\n=== {name} ===")
    try:
        result = scrape(url)
        if not result.get('success'):
            print(f"  FAILED")
            continue
        html = result.get('data', '')
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
        print(f"  HTML: {len(html)} chars, lines: {len(lines)}")
        for l in lines[:20]:
            print(f"    {l[:100]}")
    except Exception as e:
        print(f"  ERROR: {e}")
