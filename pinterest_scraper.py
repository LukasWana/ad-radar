"""
Pinterest Ad Scraper for AD Radar
==================================
Sleduje reklamy a kreativní příklady z Pinterestu.
Sledované firmy/dotazy se definují v pinterest_config.json — snadná změna bez úpravy kódu.

Usage:
    python pinterest_scraper.py              # použije config
    python pinterest_scraper.py --query "alza"   # vlastní dotaz
    python pinterest_scraper.py --list             # jen výpis configu
"""

import sys
import io
import json
import os
from pathlib import Path

sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / 'pinterest_config.json'
OUTPUT_FILE = SCRIPT_DIR / 'pinterest_ads.json'

def load_config():
    """Načte konfiguraci sledovaných firem/dotazů"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'queries': [
            {'query': 'alza.cz advertising', 'label': 'Alza', 'language': 'CZ'},
            {'query': 'mall.cz reklama', 'label': 'Mall', 'language': 'CZ'},
            {'query': 'notino advertising', 'label': 'Notino', 'language': 'CZ'},
            {'query': 'online advertising examples', 'label': 'Online Ads', 'language': 'EN'},
        ],
        'scroll_count': 8,
        'scroll_delay_seconds': 1.2
    }

def save_config(cfg):
    """Uloží konfiguraci"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def list_queries():
    """Vypíše aktuálně sledované firmy/dotazy"""
    cfg = load_config()
    print(f"\n=== Sledované firmy/dotazy ({len(cfg['queries'])}) ===")
    for i, q in enumerate(cfg['queries'], 1):
        print(f"  [{i}] {q['label']} ({q['language']}) — \"{q['query']}\"")
    print(f"\nScroll: {cfg['scroll_count']}x, delay: {cfg['scroll_delay_seconds']}s")
    print(f"\nPro úpravu: otevři {CONFIG_FILE}")
    return cfg

def add_query(query, label="", language="CZ"):
    """Přidá nový dotaz do configu"""
    cfg = load_config()
    new_entry = {
        'query': query,
        'label': label or query[:30],
        'language': language
    }
    # Kontrola duplicit
    for existing in cfg['queries']:
        if existing['query'] == query:
            print(f"Dotaz už existuje: {query}")
            return cfg
    cfg['queries'].append(new_entry)
    save_config(cfg)
    print(f"Přidáno: {new_entry}")
    return cfg

def remove_query(query_or_index):
    """Odebere dotaz z configu (podle indexu nebo textu)"""
    cfg = load_config()
    try:
        idx = int(query_or_index) - 1
        if 0 <= idx < len(cfg['queries']):
            removed = cfg['queries'].pop(idx)
            save_config(cfg)
            print(f"Odebráno: {removed}")
            return cfg
    except ValueError:
        # Smazání podle textu
        original_len = len(cfg['queries'])
        cfg['queries'] = [q for q in cfg['queries'] if q['query'] != query_or_index and q['label'] != query_or_index]
        if len(cfg['queries']) < original_len:
            save_config(cfg)
            print(f"Odebráno: {query_or_index}")
        else:
            print(f"Nenalezeno: {query_or_index}")
    return cfg

def pinterest_scrape(query, label="", scroll_count=8, scroll_delay=1.2):
    """Prohledá Pinterest pro daný dotaz"""
    print(f'\n--- Pinterest: "{query}" [{label}] ---')
    ads = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        
        try:
            encoded = query.replace(' ', '%20')
            page.goto(f'https://www.pinterest.com/search/pins/?q={encoded}', timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            time.sleep(3)  # Počkáme na inicializaci JS
            
            # Scroll pro načtení dalších výsledků (Pinterest lazy-loaduje)
            for i in range(scroll_count):
                page.evaluate('window.scrollBy(0, 600)')
                time.sleep(scroll_delay)
            
            # Parsujeme HTML
            soup = BeautifulSoup(page.content(), 'html.parser')
            pins = soup.find_all('div', attrs={'data-test-id': 'pin'})
            print(f"Nalezeno pinů: {len(pins)}")
            
            seen = set()
            for pin in pins:
                img = pin.find('img')
                if img:
                    src = img.get('src', '') or img.get('data-original-src', '') or ''
                    if 'pinimg' in src:
                        alt = img.get('alt', '') or ''
                        if alt and len(alt) > 15:  # Ignorujeme prázdné popisy
                            pid = src.split('/')[-1][:25]
                            if pid not in seen:
                                seen.add(pid)
                                ads.append({
                                    'query': query,
                                    'label': label,
                                    'image_url': src,
                                    'description': alt[:200],
                                    'source': 'pinterest'
                                })
            
            print(f"Unique: {len(ads)}")
            
        except Exception as e:
            print(f"Chyba: {e}")
        finally:
            browser.close()
    
    return ads

def run_full_scrape():
    """Prohledá všechny firmy/dotazy z configu"""
    cfg = load_config()
    all_ads = []
    
    print(f"\n=== Pinterest Ad Scraper ===")
    print(f" sleduje {len(cfg['queries'])} firem/dotazů")
    print(f" scroll: {cfg['scroll_count']}x\n")
    
    for q in cfg['queries']:
        ads = pinterest_scrape(
            query=q['query'],
            label=q.get('label', q['query'][:20]),
            scroll_count=cfg.get('scroll_count', 8),
            scroll_delay=cfg.get('scroll_delay_seconds', 1.2)
        )
        all_ads.extend(ads)
    
    # Deduplikace podle image URL
    seen_urls = set()
    unique_ads = []
    for ad in all_ads:
        if ad['image_url'] not in seen_urls:
            seen_urls.add(ad['image_url'])
            unique_ads.append(ad)
    
    print(f'\n=== CELKEM: {len(unique_ads)} unique ads z {len(all_ads)} raw ===')
    
    # Uložíme výsledky
    output = {
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config_queries': len(cfg['queries']),
        'total_raw': len(all_ads),
        'total_unique': len(unique_ads),
        'ads': unique_ads
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"Uloženo: {OUTPUT_FILE}")
    return unique_ads

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Pinterest Ad Scraper')
    parser.add_argument('--query', '-q', type=str, help='Vlastní dotaz (mimo config)')
    parser.add_argument('--label', '-l', type=str, default='', help='Štítok pro vlastní dotaz')
    parser.add_argument('--list', '-ls', action='store_true', help='Vypíše sledované firmy')
    parser.add_argument('--add', '-a', nargs=2, metavar=('QUERY', 'LABEL'), help='Přidá dotaz: python pinterest_scraper.py --add "nova firma" "Firma"')
    parser.add_argument('--remove', '-r', type=str, help='Odebere dotaz (index nebo text): python pinterest_scraper.py --remove "alza"')
    parser.add_argument('--run', action='store_true', help='Spustí scrapes')
    
    args = parser.parse_args()
    
    if args.list:
        list_queries()
    elif args.add:
        add_query(args.add[0], args.add[1])
    elif args.remove:
        remove_query(args.remove)
    elif args.query:
        ads = pinterest_scrape(args.query, args.label or args.query[:20])
        print(f"\nNalezeno: {len(ads)} ads")
    elif args.run or len(sys.argv) == 1:
        # Default: spustí full scrape
        run_full_scrape()
    else:
        list_queries()
        print("\nPoužití:")
        print("  python pinterest_scraper.py --list          # vizualizovat sledované")
        print("  python pinterest_scraper.py --add \"query\" \"Label\"   # přidat firmu")
        print("  python pinterest_scraper.py --remove \"alza\" # odebrat")
        print("  python pinterest_scraper.py --run           # spustit scrape")
        print("  python pinterest_scraper.py -q \"firma\"      # vlastní dotaz")