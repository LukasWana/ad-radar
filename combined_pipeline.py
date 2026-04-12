#!/usr/bin/env python3
"""
AD Radar Combined Pipeline
==============================
1. Pinterest scraper → pinterest_ads.json
2. YouTube Awards scraper → DB
3. adsoftheworld scraper → DB
4. generate_dashboard.py → www/index.html

Denně max 10 unikátních reklam bez opakování (30 dní dedup)
"""

import sys
import io
import json
import time
import re
import sqlite3
import hashlib
import urllib.request
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SKILL_DIR = Path(__file__).parent
DB_PATH = SKILL_DIR / "ad_radar.db"
PINTEREST_CONFIG = SKILL_DIR / "pinterest_config.json"
PINTEREST_JSON = SKILL_DIR / "pinterest_ads.json"

YOUTUBE_API_KEY = "AIzaSyB0W1rRyYwI0oyC80TotvWQwnr5LyK6wOg"
PLAYLIST_ID = "PLzCg1lz81rBeNdKxFlS6fNQnP4rX4MNq-"


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            brand TEXT,
            agency TEXT,
            description TEXT,
            category TEXT,
            score INTEGER DEFAULT 0,
            image_url TEXT,
            video_url TEXT,
            source TEXT,
            discovered_at TEXT,
            published_at TEXT,
            first_seen TEXT,
            last_seen TEXT,
            view_count INTEGER DEFAULT 0,
            is_delivered INTEGER DEFAULT 0,
            delivered_at TEXT,
            metadata TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_campaigns_brand ON campaigns(brand);
        CREATE INDEX IF NOT EXISTS idx_campaigns_score ON campaigns(score DESC);
        CREATE INDEX IF NOT EXISTS idx_campaigns_delivered ON campaigns(is_delivered);
    """)
    db.commit()
    return db


def gen_id(url, brand, title):
    return hashlib.sha256(f"{url}|{brand}|{title}".lower().strip().encode()).hexdigest()[:16]


def insert_campaign(db, url, title, brand, description, source, score=5, image_url="", video_url=""):
    cid = gen_id(url, brand, title)
    now = datetime.now().isoformat()
    
    existing = db.execute("SELECT id, view_count FROM campaigns WHERE id = ?", (cid,)).fetchone()
    if existing:
        db.execute("""
            UPDATE campaigns SET view_count = view_count + 1, last_seen = ?, score = MAX(score, ?)
            WHERE id = ?
        """, (now, score, cid))
    else:
        db.execute("""
            INSERT INTO campaigns (id, url, title, brand, description, source, score, image_url, video_url, discovered_at, first_seen, last_seen, is_delivered, delivered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (cid, url, title, brand, description, source, score, image_url, video_url, now, now, now))
    db.commit()
    return cid


def mark_delivered(db, ids):
    now = datetime.now().isoformat()
    for cid in ids:
        db.execute("UPDATE campaigns SET is_delivered = 1, delivered_at = ? WHERE id = ?", (now, cid))
    db.commit()


def scrape_pinterest():
    """Spustí Pinterest scraper a načte výsledky"""
    print("\n[1/4] Pinterest scraper...")
    
    # Spusť scraper
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "pinterest_scraper.py"), "--run"],
        capture_output=True, text=True, timeout=120
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:200])
    
    # Načti JSON
    ads = []
    if PINTEREST_JSON.exists():
        with open(PINTEREST_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ads = data.get('ads', [])
    
    print(f"  Pinterest: {len(ads)} ads v JSON")
    return ads


def scrape_youtube_awards(db):
    """YouTube Works Awards → DB"""
    print("\n[2/4] YouTube Awards...")
    
    try:
        pu = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={PLAYLIST_ID}&maxResults=50&key={YOUTUBE_API_KEY}"
        req = urllib.request.Request(pu)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        
        count = 0
        for item in data.get('items', []):
            snippet = item.get('snippet', {})
            vid = item.get('contentDetails', {}).get('videoId', '')
            title = snippet.get('title', '')
            thumb = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
            
            if not title or not vid:
                continue
            
            # Parse brand z "Brand - Ad Title (Year)" format
            if ' - ' in title:
                parts = title.split(' - ', 1)
                brand = parts[0].strip()
                ad_title = parts[1].strip().split('(')[0].strip()
            else:
                brand = 'YouTube'
                ad_title = title
            
            url = f"https://www.youtube.com/watch?v={vid}"
            
            existing = db.execute("SELECT id FROM campaigns WHERE url = ?", (url,)).fetchone()
            if not existing:
                insert_campaign(db, url, ad_title, brand, '', 'YouTube', score=7, image_url=thumb, video_url=url)
                count += 1
        
        print(f"  YouTube Awards: {count} nových")
        
    except Exception as e:
        print(f"  YouTube error: {e}")


def scrape_adsoftheworld(db):
    """adsoftheworld.com → DB"""
    print("\n[3/4] adsoftheworld...")
    
    try:
        from scraper_manager import scrape as sm_scrape
        
        result = sm_scrape("https://www.adsoftheworld.com/")
        if not result or not result.get('success'):
            print("  Failed:", result)
            return
        
        soup = BeautifulSoup(result['data'], 'html.parser')
        
        # Najdi všechny campaign linky
        links = soup.find_all('a', href=lambda h: h and '/campaigns/' in h and '/new' not in h and h != '/campaigns')
        
        seen = set()
        count = 0
        for link in links[:20]:
            href = link.get('href', '')
            if href in seen:
                continue
            seen.add(href)
            
            if href.startswith('/'):
                href = 'https://www.adsoftheworld.com' + href
            
            # Title může být v nested elements
            title_el = link.find(['img', 'span', 'div'])
            title = ''
            if title_el:
                title = title_el.get_text(strip=True) or link.get_text(strip=True)
            else:
                title = link.get_text(strip=True)
            
            title = title[:100] if title else f"Campaign {href.split('/')[-1][:20]}"
            
            existing = db.execute("SELECT id FROM campaigns WHERE url = ?", (href,)).fetchone()
            if not existing:
                insert_campaign(db, href, title, '', '', 'adsoftheworld', score=6)
                count += 1
        
        print(f"  adsoftheworld: {count} nových ({len(seen)} total)")
        
    except Exception as e:
        print(f"  adsoftheworld error: {e}")


def get_top_ads(db, limit=10, dedup_days=30):
    """Získá top 10 reklam z DB bez opakování"""
    cutoff_iso = (datetime.now() - timedelta(days=dedup_days)).isoformat()
    
    # IDs už deliverovaných v posledních dedup_days
    delivered = {r['id'] for r in db.execute(
        "SELECT id FROM campaigns WHERE is_delivered = 1 AND delivered_at >= ?", (cutoff_iso,)
    ).fetchall()}
    
    # Všechny z posledních 7 dní seřazené podle score
    rows = db.execute("""
        SELECT * FROM campaigns 
        WHERE discovered_at >= date('now', '-7 days')
        AND url NOT LIKE '%/new'
        AND url NOT LIKE '%/login'
        AND url NOT LIKE '%/sign_in%'
        ORDER BY score DESC, discovered_at DESC
        LIMIT 100
    """).fetchall()
    
    # Deduplikace: title+brand hash, exclude delivered
    seen_hashes = set()
    unique = []
    for row in rows:
        row = dict(row)
        h = hash((row.get('title', '') + row.get('brand', '')).lower())
        if h not in seen_hashes and row.get('id') not in delivered:
            seen_hashes.add(h)
            unique.append(row)
    
    return unique[:limit]


def save_dashboard_html(ads_by_source):
    """Uloží dashboard HTML"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    total = sum(len(v) for v in ads_by_source.values())
    
    cards = []
    for source, ad_list in ads_by_source.items():
        for ad in ad_list:
            title = ad.get('title', 'Untitled')[:80]
            brand = ad.get('brand', 'Unknown') or 'Unknown'
            desc = ad.get('description', '')[:150] or '—'
            url = ad.get('url', '#')
            score = ad.get('score', 5)
            image = ad.get('image_url', '')
            stars = '★' * min(score, 5)
            
            thumb = ''
            if image:
                thumb = f'<img src="{image}" alt="{brand}" class="card-thumb" loading="lazy" onerror="this.style.display=\'none\'">'
            
            cards.append(f'''
    <div class="campaign-card">
        {thumb}
        <div class="card-header">
            <span class="source-tag">{source}</span>
            <span class="score">{stars}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-brand">{brand}</p>
        <p class="card-desc">{desc}</p>
        <a href="{url}" target="_blank" class="card-link">View →</a>
    </div>''')
    
    cards_str = '\n'.join(cards) if cards else '<p class="no-ads">Žádné reklamy. Spusť scrape znovu.</p>'
    
    sources_line = ' | '.join([f'{s}: {len(v)}' for s, v in ads_by_source.items() if v])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AD RADAR v2 — Daily Top 10</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{ --bg: #0a0a0f; --card-bg: #141419; --card-hover: #1a1a22; --border: #252530; --text: #e8e8ec; --text-dim: #888894; --accent: #f59e0b; --link: #3b82f6; --star: #fbbf24; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
        header {{ text-align: center; padding: 40px 20px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
        h1 {{ font-size: 2.8em; font-weight: 700; background: linear-gradient(135deg, #f59e0b, #ef4444, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }}
        .subtitle {{ color: var(--text-dim); font-size: 1.1em; margin-bottom: 12px; }}
        .stats {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 0.9em; color: var(--text-dim); }}
        .badge {{ background: var(--accent); color: #000; padding: 2px 10px; border-radius: 20px; font-size: 0.75em; font-weight: 600; }}
        .top10-label {{ text-align: center; margin: 24px 0 16px; }}
        .top10-label h2 {{ font-size: 1.1em; color: var(--text-dim); text-transform: uppercase; letter-spacing: 2px; }}
        .ads-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
        .campaign-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px; transition: all 0.2s; }}
        .campaign-card:hover {{ background: var(--card-hover); border-color: #3a3a4a; transform: translateY(-2px); }}
        .card-thumb {{ width: 100%; height: 180px; object-fit: cover; border-radius: 6px; margin-bottom: 12px; background: #1a1a22; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .source-tag {{ font-size: 0.7em; color: var(--link); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }}
        .score {{ color: var(--star); font-size: 0.85em; }}
        .card-title {{ font-size: 1em; font-weight: 600; margin-bottom: 6px; line-height: 1.4; }}
        .card-brand {{ font-size: 0.85em; color: var(--accent); margin-bottom: 8px; }}
        .card-desc {{ font-size: 0.8em; color: var(--text-dim); margin-bottom: 12px; }}
        .card-link {{ display: inline-block; font-size: 0.8em; color: var(--link); text-decoration: none; padding: 6px 12px; background: rgba(59,130,246,0.1); border-radius: 6px; }}
        .card-link:hover {{ background: var(--link); color: white; }}
        .no-ads {{ text-align: center; color: var(--text-dim); padding: 60px 20px; font-size: 1.2em; }}
        .sources-bar {{ background: var(--card-bg); padding: 16px 20px; border-radius: 12px; margin: 24px 0; border: 1px solid var(--border); }}
        .sources-bar h3 {{ font-size: 0.85em; color: var(--text-dim); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }}
        .sources-bar p {{ font-size: 0.85em; color: var(--link); }}
        .footer {{ text-align: center; padding: 40px 20px; color: #555; font-size: 0.85em; border-top: 1px solid var(--border); margin-top: 40px; }}
        @media (max-width: 768px) {{ .container {{ padding: 16px; }} h1 {{ font-size: 2em; }} .ads-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 AD RADAR v2</h1>
            <p class="subtitle">Top 10 denních reklam — bez opakování 30 dní</p>
            <div class="stats">
                <span>📢 {total} / 10 reklam</span>
                <span class="badge">{date_str}</span>
            </div>
        </header>
        
        <div class="top10-label">
            <h2>🏆 Top 10 dnešních reklam</h2>
        </div>
        
        <div class="ads-grid">
            {cards_str}
        </div>
        
        <div class="sources-bar">
            <h3>📡 Zdroje dnešního updatu</h3>
            <p>{sources_line}</p>
        </div>
        
        <div class="footer">
            <p>AD Radar v2 | Zdroje: Pinterest, YouTube Awards, adsoftheworld</p>
            <p>Automatický update denně v 05:00 (Praha)</p>
        </div>
    </div>
</body>
</html>'''
    
    www_dir = SKILL_DIR / "www"
    www_dir.mkdir(parents=True, exist_ok=True)
    (www_dir / "history").mkdir(parents=True, exist_ok=True)
    
    index_path = www_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    snapshot = www_dir / "history" / f"{date_str}.html"
    with open(snapshot, "w", encoding="utf-8") as f:
        f.write(html)
    
    return str(index_path)


def run():
    print("=" * 50)
    print("AD RADAR COMBINED PIPELINE v2")
    print("=" * 50)
    
    db = get_db()
    
    # 1. Pinterest
    pinterest_ads = scrape_pinterest()
    
    # 2. YouTube Awards
    scrape_youtube_awards(db)
    
    # 3. adsoftheworld
    scrape_adsoftheworld(db)
    
    # 4. Získej TOP 10 z DB + Pinterest
    top_ads = get_top_ads(db, limit=10)
    
    # Přidej Pinterest (omezené na 3)
    pinterest_limited = pinterest_ads[:3]
    pinterest_source = [
        {
            'title': a.get('description', '')[:60] or 'Pinterest',
            'brand': a.get('label', 'Pinterest'),
            'description': a.get('description', '')[:150],
            'url': a.get('image_url', '#'),
            'image_url': a.get('image_url', ''),
            'source': 'Pinterest',
            'score': 5
        }
        for a in pinterest_limited
    ]
    
    # Kombinuj a deduplikuj
    all_ads = pinterest_source + [dict(row) for row in top_ads]
    
    seen = set()
    unique = []
    for ad in all_ads:
        h = hash((ad.get('title', '') + ad.get('brand', '')).lower())
        if h not in seen:
            seen.add(h)
            unique.append(ad)
    
    unique.sort(key=lambda x: x.get('score', 0), reverse=True)
    top10 = unique[:10]
    
    # Označ jako deliverované
    mark_delivered(db, [gen_id(a.get('url',''), a.get('brand',''), a.get('title','')) for a in top10])
    
    # Seskup podle zdroje
    by_source = {}
    for ad in top10:
        src = ad.get('source', 'unknown')
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(ad)
    
    # Ulož dashboard
    save_dashboard_html(by_source)
    
    db.close()
    
    print(f"\n{'='*50}")
    print(f"Hotovo! {len(top10)} TOP reklam uloženo")
    for src, ads in by_source.items():
        print(f"  {src}: {len(ads)}")


if __name__ == "__main__":
    run()