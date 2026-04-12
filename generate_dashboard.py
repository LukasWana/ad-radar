#!/usr/bin/env python3
"""
AD Radar Dashboard Generator v2
================================
- Zdroje: Pinterest, Google Ad Transparency, YouTube Awards, Médiář, adsoftheworld
- Denně max 10 nejlepších reklam
- Deduplikace: 30 dní bez opakování
- Konfigurace: sources_config.json
"""

import sys
import io
import json
import sqlite3
import re
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SKILL_DIR = Path(__file__).parent
DB_PATH = SKILL_DIR / "ad_radar.db"
WWW_DIR = SKILL_DIR / "www"
HISTORY_DIR = WWW_DIR / "history"
SOURCES_CONFIG = SKILL_DIR / "sources_config.json"
PINTEREST_CONFIG = SKILL_DIR / "pinterest_config.json"
PINTEREST_JSON = SKILL_DIR / "pinterest_ads.json"
CONFIG_FILE = SKILL_DIR / "sources_config.json"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"dashboard": {"max_daily_ads": 10, "dedup_days": 30, "min_score": 5}}


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def clean_text(text):
    if not text:
        return ""
    text = text.replace('\u2022', '-').replace('\u2023', '-').replace('\u2043', '-')
    text = text.replace('\u2219', '-').replace('\u2122', '').replace('\u00ae', '')
    text = text.replace('\ufffd', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_title(title):
    if not title:
        return "Untitled Campaign"
    title = title.replace('\u2022', ' ').replace('\u2023', ' ').replace('\u2043', ' ')
    title = title.replace('\u2219', ' ').replace('\u2122', '').replace('\u00ae', '')
    title = title.replace('\ufffd', '').replace('\u2024', '.')
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'\s*[•\-\s]*(Ads\s+of\s+the\s+World|Campaign\s+Brief|The\s+Clio\s+Network).*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[-|\s]+$', '', title)
    return title.strip() if title.strip() else "Untitled Campaign"


def get_source_display(url, source_tag=""):
    if not url:
        return source_tag or "Source"
    if "adsoftheworld" in url:
        return "Ads of the World"
    if "campaignbrief" in url:
        return "Campaign Brief"
    if "mediacz" in url or "mediar.cz" in url:
        return "Médiář"
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "pinterest" in url:
        return "Pinterest"
    if "google.com" in url and "advertiser" in url:
        return "Google Ad Transparency"
    if source_tag:
        return source_tag
    return "Source"


def get_video_thumbnail(url):
    match = re.search(r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return f"https://img.youtube.com/vi/{match.group(1)}/mqdefault.jpg"
    return None


def get_youtube_thumbnail(url):
    """YouTube video thumbnail"""
    match = re.search(r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return f"https://img.youtube.com/vi/{match.group(1)}/mqdefault.jpg"
    return None


def get_ad_card(row, sources_config):
    """Generate HTML card pro jednu reklamu"""
    title = clean_title(row.get("title", ""))
    brand = clean_text(row.get("brand", "")) or "Unknown Brand"
    description = clean_text(row.get("description", ""))
    url = row.get("url", "#") or "#"
    score = row.get("score", 5) or 5
    image_url = row.get("image_url", "") or ""
    video_url = row.get("video_url", "") or ""
    source = row.get("source", "") or get_source_display(url)
    
    stars = "★" * min(score, 5)
    
    # Thumbnail
    thumb_url = ""
    if image_url:
        thumb_url = image_url
    elif video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
        thumb_url = get_youtube_thumbnail(video_url) or ""
    
    thumb_html = ""
    if thumb_url:
        thumb_html = f'<img src="{thumb_url}" alt="{brand}" class="card-thumb" loading="lazy" onerror="this.style.display=\'none\'">'
    
    return f'''
    <div class="campaign-card">
        {thumb_html}
        <div class="card-header">
            <span class="source-tag">{source}</span>
            <span class="score">{stars}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-brand">{brand}</p>
        <p class="card-desc">{description if description else "—"}</p>
        <a href="{url}" target="_blank" class="card-link">View →</a>
    </div>
    '''


def get_ads_from_db(db, limit=10, dedup_days=30):
    """Nakrmí reklamy z DB, deduplikované proti posledním dedup_days"""
    cutoff = (datetime.now() - timedelta(days=dedup_days)).isoformat()
    
    rows = db.execute('''
        SELECT * FROM campaigns 
        WHERE delivered_at >= date('now', '-7 days')
        AND url NOT LIKE '%/new'
        AND url NOT LIKE '%/login'
        AND url NOT LIKE '%/sign_in%'
        ORDER BY score DESC, discovered_at DESC
        LIMIT 200
    ''').fetchall()
    
    # Deduplikace: vyřadí reklamy co už byly deliverované v posledních dedup_days
    delivered_ids = set()
    for row in db.execute(
        'SELECT id FROM campaigns WHERE is_delivered = 1 AND delivered_at >= ?',
        (cutoff,)
    ).fetchall():
        delivered_ids.add(row['id'])
    
    seen_hashes = set()
    unique_rows = []
    for row in rows:
        row_dict = dict(row) if not isinstance(row, dict) else row
        title = row_dict.get('title', '') or ''
        brand = row_dict.get('brand', '') or ''
        h = hash((title + brand).lower())
        if h not in seen_hashes and row_dict.get('id') not in delivered_ids:
            seen_hashes.add(h)
            unique_rows.append(row_dict)
    
    return unique_rows[:limit]


def get_ads_from_pinterest(limit=5):
    """Získá reklamy z Pinterest JSON"""
    ads = []
    if not PINTEREST_JSON.exists():
        return ads
    
    try:
        with open(PINTEREST_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data.get('ads', []):
            desc = item.get('description', '') or item.get('alt_text', '') or ''
            if len(desc) > 15:
                ads.append({
                    'title': desc[:60] + '...' if len(desc) > 60 else desc,
                    'brand': item.get('label', 'Pinterest'),
                    'description': desc,
                    'url': item.get('image_url', '#'),
                    'image_url': item.get('image_url', ''),
                    'source': 'Pinterest',
                    'score': 5,
                    'category': 'creative'
                })
        
        # Deduplikace podle URL
        seen = set()
        unique = []
        for a in ads:
            if a['image_url'] not in seen:
                seen.add(a['image_url'])
                unique.append(a)
        
        return unique[:limit]
    except Exception as e:
        print(f"Pinterest JSON error: {e}")
        return ads


def generate_dashboard_v2():
    """Generuje dashboard s novými zdroji, max 10 denně"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    cfg = load_config()
    db = get_db()
    
    max_daily = cfg.get('dashboard', {}).get('max_daily_ads', 10)
    dedup_days = cfg.get('dashboard', {}).get('dedup_days', 30)
    
    # Sbírej reklamy ze všech zdrojů
    all_ads = []
    
    # 1. Pinterest (kreativní inspirace)
    pinterest_ads = get_ads_from_pinterest(limit=5)
    all_ads.extend(pinterest_ads)
    print(f"Pinterest: {len(pinterest_ads)} ads")
    
    # 2. DB (adsoftheworld, YouTube, Médiář atd.)
    db_ads = get_ads_from_db(db, limit=max_daily, dedup_days=dedup_days)
    for row_dict in db_ads:
        all_ads.append(row_dict)
    print(f"DB: {len(db_ads)} ads")
    
    # Deduplikace podle title+brand hash
    seen_hashes = set()
    unique_ads = []
    for ad in all_ads:
        title = ad.get('title', '') or ''
        brand = ad.get('brand', '') or ''
        h = hash((title + brand).lower())
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_ads.append(ad)
    
    # Seřaď podle score (nejlepší první)
    unique_ads.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Omez na max 10
    top_ads = unique_ads[:max_daily]
    print(f"Celkem unique (po dedup): {len(unique_ads)}, TOP 10: {len(top_ads)}")
    
    # Počty podle zdrojů
    sources_count = {}
    for ad in top_ads:
        src = ad.get('source', 'unknown')
        sources_count[src] = sources_count.get(src, 0) + 1
    
    # === Vygeneruj HTML ===
    cards_html = []
    for i, ad in enumerate(top_ads, 1):
        card = get_ad_card(ad, cfg)
        cards_html.append(f'<div class="top-ad" style="animation-delay: {i*0.05}s">{card}</div>')
    
    cards_str = '\n'.join(cards_html) if cards_html else '<p class="no-ads">Žádné nové reklamy dnes. Zkus to zítra!</p>'
    
    # Zdroje info
    sources_info = ' | '.join([f'{src}: {cnt}' for src, cnt in sources_count.items()])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AD RADAR v2 — Daily Top 10</title>
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
            --star: #fbbf24;
        }}
        
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
        
        header {{ text-align: center; padding: 40px 20px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
        
        h1 {{ font-size: 2.8em; font-weight: 700; background: linear-gradient(135deg, #f59e0b, #ef4444, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }}
        
        .subtitle {{ color: var(--text-dim); font-size: 1.1em; margin-bottom: 12px; }}
        
        .stats {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 0.9em; color: var(--text-dim); }}
        .stats span {{ display: flex; align-items: center; gap: 6px; }}
        
        .badge {{ background: var(--accent); color: #000; padding: 2px 10px; border-radius: 20px; font-size: 0.75em; font-weight: 600; }}
        
        .top10-label {{ text-align: center; margin: 24px 0 16px; }}
        .top10-label h2 {{ font-size: 1.1em; color: var(--text-dim); text-transform: uppercase; letter-spacing: 2px; display: inline-flex; align-items: center; gap: 8px; }}
        
        .ads-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
        
        .top-ad {{ animation: fadeIn 0.4s ease forwards; opacity: 0; }}
        
        @keyframes fadeIn {{ to {{ opacity: 1; }} }}
        
        .campaign-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px; transition: all 0.2s; }}
        .campaign-card:hover {{ background: var(--card-hover); border-color: #3a3a4a; transform: translateY(-2px); }}
        
        .card-thumb {{ width: 100%; height: 180px; object-fit: cover; border-radius: 6px; margin-bottom: 12px; background: #1a1a22; }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        
        .source-tag {{ font-size: 0.7em; color: var(--link); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }}
        .score {{ color: var(--star); font-size: 0.85em; letter-spacing: 1px; }}
        
        .card-title {{ font-size: 1em; font-weight: 600; margin-bottom: 6px; line-height: 1.4; }}
        .card-brand {{ font-size: 0.85em; color: var(--accent); margin-bottom: 8px; }}
        .card-desc {{ font-size: 0.8em; color: var(--text-dim); margin-bottom: 12px; }}
        
        .card-link {{ display: inline-block; font-size: 0.8em; color: var(--link); text-decoration: none; padding: 6px 12px; background: rgba(59,130,246,0.1); border-radius: 6px; transition: all 0.2s; }}
        .card-link:hover {{ background: var(--link); color: white; }}
        
        .no-ads {{ text-align: center; color: var(--text-dim); padding: 60px 20px; font-size: 1.2em; }}
        
        .sources-bar {{ background: var(--card-bg); padding: 16px 20px; border-radius: 12px; margin: 24px 0; border: 1px solid var(--border); }}
        .sources-bar h3 {{ font-size: 0.85em; color: var(--text-dim); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        .sources-bar p {{ font-size: 0.85em; color: var(--link); }}
        
        .footer {{ text-align: center; padding: 40px 20px; color: #555; font-size: 0.85em; border-top: 1px solid var(--border); margin-top: 40px; }}
        .footer a {{ color: #666; }}
        
        @media (max-width: 768px) {{ .container {{ padding: 16px; }} h1 {{ font-size: 2em; }} .ads-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 AD RADAR v2</h1>
            <p class="subtitle">Top 10 denních reklam — bez opakování {dedup_days} dní</p>
            <div class="stats">
                <span>📢 {len(top_ads)} / {max_daily} reklam</span>
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
            <p>{sources_info}</p>
        </div>
        
        <div class="footer">
            <p>AD Radar v2 | Zdroje: Pinterest, Google Ad Transparency, YouTube Awards, Médiář, adsoftheworld</p>
            <p>Automatický update denně v 05:00 (Praha)</p>
        </div>
    </div>
</body>
</html>
'''
    
    # Ulož
    index_path = WWW_DIR / "index.html"
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Historický snapshot
    snapshot_path = HISTORY_DIR / f"{date_str}.html"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    db.close()
    
    print(f"Dashboard: {index_path}")
    print(f"Snapshot: {snapshot_path}")
    return str(index_path)


from datetime import timedelta

if __name__ == "__main__":
    generate_dashboard_v2()