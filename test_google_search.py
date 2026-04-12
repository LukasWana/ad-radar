import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

advertisers_to_test = ['Alza.cz', 'Mall', 'CZC.cz', 'Notino', 'Rossmann']

results = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    page.goto('https://adstransparency.google.com/?region=CZ', timeout=30000)
    page.wait_for_load_state('networkidle', timeout=15000)
    time.sleep(2)
    
    search_input = page.query_selector('input[type="text"], input[placeholder], input[aria-label]')
    if not search_input:
        print("Search input NOT found")
        browser.close()
        sys.exit(1)
    
    for query in advertisers_to_test:
        search_input.fill(query)
        time.sleep(1)
        page.keyboard.press('Enter')
        time.sleep(3)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract advertiser info
        result = {
            'query': query,
            'found': False,
            'advertisers': []
        }
        
        # Look for advertiser entries
        if query.lower() in text.lower():
            result['found'] = True
        
        # Find ad counts
        import re
        ad_counts = re.findall(r'(\d+[\s]?tis\.?\s*reklam)', text)
        if ad_counts:
            result['ad_counts'] = ad_counts[:5]
        
        # Find advertiser names near "Ověřeno" or "Verified"
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'ověřeno' in line.lower() or 'verified' in line.lower():
                # Get surrounding context
                context = ' '.join(lines[max(0,i-2):i+3])
                result['advertisers'].append(context[:200])
        
        results.append(result)
        print(f"Query '{query}': found={result['found']}, ad_counts={result.get('ad_counts', [])[:3]}")
        
        # Clear for next search
        search_input.fill('')
        time.sleep(0.5)
    
    browser.close()

print("\n=== SUMMARY ===")
print(json.dumps(results, ensure_ascii=False, indent=2))
