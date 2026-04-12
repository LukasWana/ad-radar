#!/usr/bin/env python3
"""
Thematic AD Finder
==================
Na požádání prohledá reklamní zdroje podle tématu.

Použití:
    python discover_ads.py --query "sportovni boty"
    python discover_ads.py --query "letni kosmetika" --format video --max 20
    python discover_ads.py --query "hobby zahrada" --output html

Zdroje:
    Pinterest (query-based)
    adsoftheworld.com (search)
    muz.li (tag-based discovery)
    Google Ad Transparency (brand search)
"""

import sys
import io
import json
import time
import re
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from bs4 import BeautifulSoup
from scraper_manager import scrape as sm_scrape

# === Config ===
SKILL_DIR = Path(__file__).parent
PINTEREST_COOKIES = SKILL_DIR / "pinterest_cookies.json"
OUTPUT_DIR = SKILL_DIR / "www" / "discover"

YOUTUBE_API_KEY = "AIzaSyB0W1rRyYwI0oyC80TotvWQwnr5LyK6wOg"

# Formáty pro klasifikaci
FORMAT_KEYWORDS = {
    'video': ['youtube', 'watch', '.mp4', 'video', 'youtube.com', 'reklamní spot', 'tv spot', 'commercial'],
    'banner': ['banner', 'display', '300x250', '728x90', 'rectangle', 'leaderboard', 'muz.li'],
    'ooh': ['outdoor', 'billboard', 'ooh', 'citylight', 'city board', 'poseen', 'bigboard'],
    'print': ['print', 'tisk', 'magazine', 'noviny', 'televizní', 'print'],
    'social': ['instagram', 'facebook', 'tiktok', 'twitter', 'social', 'influencer'],
}


def parse_args():
    parser = argparse.ArgumentParser(description='Thematic AD Finder')
    parser.add_argument('--query', '-q', required=True, help='Hledané téma (např. "sportovni boty")')
    parser.add_argument('--format', '-f', choices=['video', 'banner', 'ooh', 'print', 'social', 'all'], 
                        default='all', help='Preferovaný formát')
    parser.add_argument('--max', '-m', type=int, default=20, help='Max výsledků na zdroj')
    parser.add_argument('--output', '-o', choices=['html', 'json'], default='html', help='Výstupní formát')
    parser.add_argument('--open', action='store_true', help='Otevřít výsledek v prohlížeči')
    return parser.parse_args()


def classify_format(title, description, image_url, url):
    """Ohodnoť formát podle obsahu"""
    text = f"{title} {description} {image_url} {url}".lower()
    scores = {}
    for fmt, keywords in FORMAT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        scores[fmt] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'other'


def search_pinterest(query, max_results=20):
    """Prohledá Pinterest přes Playwright"""
    print(f"  [Pinterest] hledám: '{query}'")
    results = []
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            search_url = f"https://www.pinterest.com/search/pins/?q={urllib.parse.quote(query)}"
            page.goto(search_url, timeout=30000)
            
            # Scroll pro načtení více výsledků
            for _ in range(4):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.5)
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            
            pins = soup.select('[data-test-id="pin"]') or soup.select('.Pin')
            for pin in pins[:max_results]:
                img = pin.select_one('img')
                title = img.get('alt', '') if img else ''
                image_url = img.get('src', '') or img.get('data-src', '') if img else ''
                link = pin.select_one('a')
                url = f"https://pinterest.com{pin.select_one('a').get('href', '')}" if pin.select_one('a') else ''
                
                if image_url and len(image_url) > 20:
                    results.append({
                        'title': title[:80] or f'Pinterest: {query}',
                        'brand': title.split()[0] if title else query,
                        'description': title,
                        'url': url or image_url,
                        'image_url': image_url,
                        'source': 'Pinterest',
                        'format': classify_format(title, '', image_url, url),
                        'score': 6
                    })
            
            browser.close()
    
    except Exception as e:
        print(f"    Pinterest error: {e}")
    
    print(f"    → {len(results)} výsledků")
    return results


def search_adsoftheworld(query, max_results=20):
    """Prohledá adsoftheworld.com přes Playwright"""
    print(f"  [adsoftheworld] hledám: '{query}'")
    results = []
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            search_url = f"https://www.adsoftheworld.com/search?search={urllib.parse.quote(query)}"
            page.goto(search_url, timeout=30000)
            page.wait_for_timeout(2000)
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            
            campaigns = soup.select('.campaign-item') or soup.select('.campaign') or soup.select('a[href*="/campaigns/"]')
            
            for item in campaigns[:max_results]:
                link = item if item.name == 'a' else item.select_one('a')
                if not link:
                    continue
                    
                href = link.get('href', '')
                if not href or '/campaigns/' not in href:
                    continue
                if href.startswith('/'):
                    href = 'https://www.adsoftheworld.com' + href
                
                img = item.select_one('img')
                image_url = img.get('src', '') or img.get('data-src', '') if img else ''
                title = img.get('alt', '') if img else link.get_text(strip=True)
                title = title[:80] or f'Ad: {href.split("/")[-1][:20]}'
                
                results.append({
                    'title': title,
                    'brand': title.split()[0] if title else '',
                    'description': '',
                    'url': href,
                    'image_url': image_url,
                    'source': 'adsoftheworld',
                    'format': classify_format(title, '', image_url, href),
                    'score': 7
                })
            
            browser.close()
    
    except Exception as e:
        print(f"    adsoftheworld error: {e}")
    
    print(f"    → {len(results)} výsledků")
    return results


def search_muzli(query, max_results=20):
    """Prohledá muz.li - tag-based discovery"""
    print(f"  [muz.li] hledám: '{query}'")
    results = []
    
    try:
        # Muz.li nemá vyhledávání, použijeme scrape hlavní stránky a filtrování
        result = sm_scrape("https://muz.li/inspiration/banner-examples/")
        if not result or not result.get('success'):
            print(f"    muz.li fetch failed")
            return []
        
        soup = BeautifulSoup(result['data'], 'html.parser')
        articles = soup.select('article')
        
        query_words = query.lower().split()
        
        for article in articles[:50]:
            img = article.find('img')
            if not img:
                continue
            
            image_url = img.get('src', '') or img.get('data-src', '')
            alt = img.get('alt', '') or ''
            
            # Filtrování podle relevance
            alt_lower = alt.lower()
            if not any(w in alt_lower for w in query_words):
                continue
            
            if len(results) >= max_results:
                break
            
            results.append({
                'title': alt[:80] or f'Banner: {query}',
                'brand': alt.split()[0] if alt else 'muz.li',
                'description': alt,
                'url': 'https://muz.li/inspiration/banner-examples/',
                'image_url': image_url,
                'source': 'muz.li',
                'format': classify_format(alt, '', image_url, ''),
                'score': 5
            })
    
    except Exception as e:
        print(f"    muz.li error: {e}")
    
    print(f"    → {len(results)} výsledků")
    return results


def search_youtube(query, max_results=15):
    """Hledá video reklamy na YouTube"""
    print(f"  [YouTube] hledám: '{query}'")
    results = []
    
    try:
        # YouTube Data API - search
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query + ' reklama')}&type=video&maxResults={max_results}&key={YOUTUBE_API_KEY}"
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        
        for item in data.get('items', []):
            snippet = item['snippet']
            vid = item['id']['videoId']
            title = snippet.get('title', '')
            thumb = snippet['thumbnails'].get('medium', {}).get('url', '')
            channel = snippet.get('channelTitle', '')
            
            results.append({
                'title': title[:80] or f'YouTube: {query}',
                'brand': channel,
                'description': snippet.get('description', '')[:150],
                'url': f'https://www.youtube.com/watch?v={vid}',
                'image_url': thumb,
                'source': 'YouTube',
                'format': 'video',
                'score': 6
            })
    
    except Exception as e:
        print(f"    YouTube error: {e}")
    
    print(f"    → {len(results)} výsledků")
    return results


def filter_format(results, preferred_format):
    """Filtruje výsledky podle preferovaného formátu"""
    if preferred_format == 'all':
        return results
    
    filtered = [r for r in results if r['format'] == preferred_format]
    
    # Pokud je málo výsledků, doplň i partial match
    if len(filtered) < 5:
        partial = [r for r in results if r['format'] != 'other' and r['format'] != preferred_format]
        filtered.extend(partial[:5 - len(filtered)])
    
    return filtered


def deduplicate(results):
    """Deduplikuje podle URL"""
    seen_urls = set()
    unique = []
    for r in results:
        url = r.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    return unique


def generate_html(results, query, output_path):
    """Generuje HTML stránku s výsledky"""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)
    
    cards = []
    for r in results:
        thumb = f'<img src="{r["image_url"]}" alt="{r["brand"]}" loading="lazy" onerror="this.src=\'https://picsum.photos/400/300?blur\'">' if r.get('image_url') else '<div class="no-img">Bez náhledu</div>'
        format_badge = f'<span class="format-badge {r["format"]}">{r["format"]}</span>' if r.get('format') != 'other' else ''
        
        cards.append(f'''
        <div class="result-card" data-format="{r.get('format', '')}">
            <div class="card-img">{thumb}</div>
            <div class="card-body">
                <div class="card-meta">
                    <span class="source">{r.get('source', '')}</span>
                    {format_badge}
                </div>
                <h3 class="card-title">{r.get('title', 'Untitled')}</h3>
                <p class="card-brand">{r.get('brand', '')}</p>
                <p class="card-desc">{r.get('description', '')[:100]}</p>
                <a href="{r.get('url', '#')}" target="_blank" class="card-link">Otevřít →</a>
            </div>
        </div>''')
    
    cards_html = '\n'.join(cards) if cards else '<p class="no-results">Žádné výsledky nenalezeny.</p>'
    
    html = f'''<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AD Finder — {query}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #0a0a0f;
            --card-bg: #141419;
            --card-hover: #1a1a22;
            --border: #252530;
            --text: #e8e8ec;
            --text-dim: #888894;
            --accent: #f59e0b;
            --link: #3b82f6;
            --video: #ef4444;
            --banner: #22c55e;
            --ooh: #a855f7;
            --print: #06b6d4;
            --social: #ec4899;
        }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
        header {{ text-align: center; padding: 40px 20px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
        h1 {{ font-size: 2.2em; font-weight: 700; color: var(--accent); margin-bottom: 8px; }}
        .search-form {{ margin: 20px 0; }}
        .search-form input {{ 
            font-size: 1.1em; padding: 12px 20px; width: 300px; 
            background: var(--card-bg); border: 1px solid var(--border); 
            color: var(--text); border-radius: 8px;
        }}
        .search-form button {{
            font-size: 1em; padding: 12px 24px; 
            background: var(--accent); border: none; 
            color: #000; border-radius: 8px; cursor: pointer; margin-left: 8px;
        }}
        .meta {{ color: var(--text-dim); font-size: 0.95em; }}
        .results-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .result-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all 0.2s; }}
        .result-card:hover {{ transform: translateY(-4px); border-color: var(--accent); }}
        .card-img {{ height: 200px; overflow: hidden; background: #1a1a22; }}
        .card-img img {{ width: 100%; height: 100%; object-fit: cover; }}
        .no-img {{ height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-dim); }}
        .card-body {{ padding: 16px; }}
        .card-meta {{ display: flex; gap: 8px; margin-bottom: 10px; }}
        .source {{ font-size: 0.7em; color: var(--link); text-transform: uppercase; font-weight: 500; }}
        .format-badge {{ font-size: 0.65em; padding: 2px 8px; border-radius: 12px; font-weight: 500; }}
        .format-badge.video {{ background: rgba(239,68,68,0.2); color: var(--video); }}
        .format-badge.banner {{ background: rgba(34,197,94,0.2); color: var(--banner); }}
        .format-badge.ooh {{ background: rgba(168,85,247,0.2); color: var(--ooh); }}
        .format-badge.print {{ background: rgba(6,182,212,0.2); color: var(--print); }}
        .format-badge.social {{ background: rgba(236,72,153,0.2); color: var(--social); }}
        .card-title {{ font-size: 1em; font-weight: 600; margin-bottom: 6px; line-height: 1.3; }}
        .card-brand {{ font-size: 0.85em; color: var(--accent); margin-bottom: 8px; }}
        .card-desc {{ font-size: 0.8em; color: var(--text-dim); margin-bottom: 12px; }}
        .card-link {{ display: inline-block; font-size: 0.8em; color: var(--link); text-decoration: none; padding: 6px 12px; background: rgba(59,130,246,0.1); border-radius: 6px; }}
        .card-link:hover {{ background: var(--link); color: white; }}
        .no-results {{ text-align: center; color: var(--text-dim); padding: 60px; font-size: 1.2em; }}
        .footer {{ text-align: center; padding: 40px; color: #555; font-size: 0.85em; border-top: 1px solid var(--border); margin-top: 40px; }}
        .filters {{ display: flex; gap: 8px; margin: 20px 0; flex-wrap: wrap; justify-content: center; }}
        .filter-btn {{ padding: 8px 16px; background: var(--card-bg); border: 1px solid var(--border); color: var(--text-dim); border-radius: 20px; cursor: pointer; font-size: 0.85em; }}
        .filter-btn:hover, .filter-btn.active {{ border-color: var(--accent); color: var(--accent); }}
        @media (max-width: 768px) {{ .container {{ padding: 16px; }} h1 {{ font-size: 1.6em; }} .search-form input {{ width: 100%; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 AD Finder</h1>
            <p class="meta">Thematické vyhledávání reklamní inspirace</p>
            <form class="search-form" action="/discover/discover_ads.py" method="GET">
                <input type="text" name="q" value="{query}" placeholder="např. sportovní boty, letní kosmetika...">
                <button type="submit">Hledat</button>
            </form>
            <p class="meta">Nalezeno: {total} výsledků • {date_str}</p>
        </header>
        
        <div class="filters">
            <button class="filter-btn active" data-format="all">Vše</button>
            <button class="filter-btn" data-format="video">🎬 Video</button>
            <button class="filter-btn" data-format="banner">🖼️ Banner</button>
            <button class="filter-btn" data-format="ooh">� Billboard</button>
            <button class="filter-btn" data-format="print">📰 Print</button>
            <button class="filter-btn" data-format="social">📱 Social</button>
        </div>
        
        <div class="results-grid" id="results">
{cards_html}
        </div>
        
        <div class="footer">
            AD Finder — Thematická inspirace pro reklamní kampaně
        </div>
    </div>
    
    <script>
        // Client-side filtering
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const fmt = btn.dataset.format;
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.result-card').forEach(card => {{
                    card.style.display = (fmt === 'all' || card.dataset.format === fmt) ? 'block' : 'none';
                }});
            }});
        }});
    </script>
</body>
</html>'''
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    return output_path


def main():
    args = parse_args()
    query = args.query
    max_per_source = args.max
    
    print(f"\n🔍 AD Finder — hledám: '{query}'")
    print(f"   Formát: {args.format} | Max: {args.max}\n")
    
    all_results = []
    
    # Paralelní vyhledávání
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(search_pinterest, query, max_per_source): 'Pinterest',
            executor.submit(search_adsoftheworld, query, max_per_source): 'adsoftheworld',
            executor.submit(search_muzli, query, max_per_source): 'muz.li',
            executor.submit(search_youtube, query, max_per_source): 'YouTube',
        }
        
        for future in as_completed(futures):
            source = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"  {source} failed: {e}")
    
    # Deduplikace a filtrování
    all_results = deduplicate(all_results)
    all_results = filter_format(all_results, args.format)
    
    # Deduplikace znovu po filtru
    all_results = deduplicate(all_results)
    
    print(f"\n✅ Celkem: {len(all_results)} výsledků\n")
    
    if args.output == 'json':
        import io
        output = SKILL_DIR / f"discover_{query.replace(' ', '_')[:20]}.json"
        with io.open(str(output), 'w', encoding='utf-8') as f:
            f.write(json.dumps(all_results, ensure_ascii=False, indent=2))
        print(f"JSON uložen: {output}")
        return
    
    # HTML výstup
    safe_query = re.sub(r'[^a-zA-Z0-9]', '_', query)[:30]
    timestamp = datetime.now().strftime("%H%M%S")
    output_path = OUTPUT_DIR / f"{safe_query}_{timestamp}.html"
    
    output_path = generate_html(all_results, query, output_path)
    print(f"🌐 Výsledek: {output_path}")
    
    if args.open:
        import webbrowser
        webbrowser.open(f'file:///{output_path}')
    
    # Také ulož jako aktuální discovery
    current = OUTPUT_DIR / "index.html"
    generate_html(all_results, query, current)
    print(f"🌐 Aktuální: {current}")


if __name__ == '__main__':
    import urllib.parse  # pro quote
    main()
