#!/usr/bin/env python3
"""
Ad Radar Dashboard Generator - Clean version with specific sections
"""

import sys
import json
import sqlite3
import re
import os
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent
DB_PATH = SKILL_DIR / "ad_radar.db"
WWW_DIR = SKILL_DIR / "www"
HISTORY_DIR = WWW_DIR / "history"


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def clean_text(text):
    """Remove garbage characters and clean text."""
    if not text:
        return ""
    text = text.replace('\u2022', '-')
    text = text.replace('\u2023', '-')
    text = text.replace('\u2043', '-')
    text = text.replace('\u2219', '-')
    text = text.replace('\u2122', '')
    text = text.replace('\u00ae', '')
    text = text.replace('\ufffd', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_title(title):
    """Clean campaign title from source suffixes."""
    if not title:
        return "Untitled Campaign"
    
    title = title.replace('\u2022', ' ')
    title = title.replace('\u2023', ' ')
    title = title.replace('\u2043', ' ')
    title = title.replace('\u2219', ' ')
    title = title.replace('\u2122', '')
    title = title.replace('\u00ae', '')
    title = title.replace('\ufffd', '')
    title = title.replace('\u2024', '.')
    title = re.sub(r'\s+', ' ', title)
    
    title = re.sub(
        r'\s*[•\-\s]*(Ads\s+of\s+the\s+World|Campaign\s+Brief|The\s+Clio\s+Network).*$',
        '',
        title,
        flags=re.IGNORECASE
    )
    title = re.sub(r'[-|\s]+$', '', title)
    return title.strip() if title.strip() else "Untitled Campaign"


def get_source_display(url):
    """Get source name from URL."""
    if not url:
        return "Unknown"
    if "adsoftheworld" in url:
        return "Ads of the World"
    if "campaignbrief" in url:
        return "Campaign Brief"
    if "mediacz" in url or "mediar.cz" in url:
        return "Médiář"
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "famous" in url.lower():
        return "Famous Campaigns"
    return "Source"


def generate_ad_card(row):
    """Generate HTML for a single ad campaign."""
    # Convert sqlite3.Row to dict for .get() support
    if hasattr(row, 'keys'):
        row = dict(zip(row.keys(), row))
    
    title = clean_title(row.get("title", ""))
    brand = clean_text(row.get("brand", "")) or "Unknown Brand"
    description = clean_text(row.get("description", ""))
    url = row.get("url", "#") or "#"
    source = get_source_display(url)
    score = row.get("score", 5) or 5
    image_url = row.get("image_url", "") or ""
    video_url = row.get("video_url", "") or ""
    
    stars = "★" * min(score, 5)
    
    # Thumbnail if available
    thumbnail_html = ""
    if image_url:
        thumbnail_html = f'<img src="{image_url}" alt="{brand}" class="card-thumb" loading="lazy" onerror="this.style.display=\'none\'">'
    elif video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
        # Generate YouTube thumbnail URL
        video_id_match = re.search(r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
        if video_id_match:
            vid = video_id_match.group(1)
            thumbnail_html = f'<img src="https://img.youtube.com/vi/{vid}/mqdefault.jpg" alt="{brand}" class="card-thumb" loading="lazy" onerror="this.style.display=\'none\'">'
    
    return f'''
    <div class="campaign-card">
        {thumbnail_html}
        <div class="card-header">
            <span class="source-tag">{source}</span>
            <span class="score">{stars}</span>
        </div>
        <h3 class="card-title">{title}</h3>
        <p class="card-brand">{brand}</p>
        <p class="card-desc">{description if description else "No description available."}</p>
        <a href="{url}" target="_blank" class="card-link">View Campaign →</a>
    </div>
'''
def generate_dashboard(db, date_str=None):
    """Generate main dashboard HTML."""
    now = datetime.now()
    date_str = date_str or now.strftime("%Y-%m-%d")
    
    # Get recent campaigns
    rows = db.execute('''
        SELECT * FROM campaigns 
        WHERE delivered_at >= date('now', '-7 days')
        AND url NOT LIKE '%/new'
        AND url NOT LIKE '%/login'
        AND url NOT LIKE '%/sign_in%'
        ORDER BY score DESC, discovered_at DESC
        LIMIT 50
    ''').fetchall()
    
    # Define sections exactly as requested
    sections = {
        "online": {
            "name": "🎯 ONLINE / GOOGLE / META / SEZNAM",
            "emoji": "🎯",
            "title": "ONLINE / GOOGLE / META / SEZNAM",
            "cards": [],
            "keywords": ["google", "meta", "facebook", "instagram", "twitter", "tiktok", 
                        "seznam", "online", "digital", "programmatic", "ppc", "display",
                        "banner", "video ad", "pre-roll", "mid-roll"]
        },
        "tv": {
            "name": "🎬 TV / CINEMA",
            "emoji": "🎬",
            "title": "TV / CINEMA",
            "cards": [],
            "keywords": ["tv", "television", "cinema", "movie", "commercial", "spot",
                        "youtube", "video", "broadcast"]
        },
        "print": {
            "name": "📰 PRINT / OOH",
            "emoji": "📰",
            "title": "PRINT / OOH",
            "cards": [],
            "keywords": ["print", "outdoor", "billboard", "ooh", "magazine", "newspaper",
                        "poster", "transit", "airport", "street"]
        },
        "brand": {
            "name": "🔤 BRAND / LOGO",
            "emoji": "🔤",
            "title": "BRAND / LOGO",
            "cards": [],
            "keywords": ["brand", "logo", "rebrand", "branding", "identity", "visual",
                        "campaign", "awareness", "positioning"]
        }
    }
    
    # Categorize each campaign
    for row in rows:
        title = clean_title(row["title"]).lower()
        desc = clean_text(row["description"]).lower()
        url = (row["url"] or "").lower()
        category = row["category"] or ""
        category = category.lower()
        
        text = f"{title} {desc} {url} {category}"
        
        # Try to match keywords
        assigned = False
        for sec_key, sec in sections.items():
            if any(kw in text for kw in sec["keywords"]):
                if len(sec["cards"]) < 8:  # Max 8 per section
                    sec["cards"].append(generate_ad_card(row))
                    assigned = True
                    break
        
        # If no keyword match, put in brand section (catchall)
        if not assigned:
            sections["brand"]["cards"].append(generate_ad_card(row))
    
    # Count stats
    total = len(rows)
    sources = {}
    for r in rows:
        src = get_source_display(r["url"])
        sources[src] = sources.get(src, 0) + 1
    
    # Build HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AD RADAR - Daily Best Advertising</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --bg-dark: #0a0a0f;
            --bg-card: #141419;
            --bg-card-hover: #1a1a22;
            --border: #252530;
            --text: #e8e8ec;
            --text-dim: #888894;
            --accent: #f59e0b;
            --link: #3b82f6;
            --link-hover: #2563eb;
            --star: #fbbf24;
        }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
        
        header {{
            text-align: center;
            padding: 40px 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 32px;
        }}
        
        h1 {{
            font-size: 2.8em;
            font-weight: 700;
            background: linear-gradient(135deg, #f59e0b, #ef4444, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        
        .subtitle {{
            color: var(--text-dim);
            font-size: 1.1em;
            margin-bottom: 16px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
            color: var(--text-dim);
            font-size: 0.9em;
        }}
        
        .stats span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            background: var(--bg-card);
            border-radius: 12px 12px 0 0;
            border: 1px solid var(--border);
            border-bottom: none;
        }}
        
        .section-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: var(--text);
        }}
        
        .section-count {{
            font-size: 0.85em;
            color: var(--text-dim);
            background: var(--bg-dark);
            padding: 4px 10px;
            border-radius: 20px;
        }}
        
        .section-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 16px;
            padding: 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-top: none;
            border-radius: 0 0 12px 12px;
        }}
        
        .campaign-card {{
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            transition: all 0.2s ease;
        }}
        
        .card-thumb {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-radius: 6px;
            margin-bottom: 12px;
        }}
        
        .campaign-card:hover {{
            background: var(--bg-card-hover);
            border-color: #3a3a4a;
            transform: translateY(-2px);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .source-tag {{
            font-size: 0.7em;
            color: var(--link);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }}
        
        .score {{
            color: var(--star);
            font-size: 0.85em;
            letter-spacing: 1px;
        }}
        
        .card-title {{
            font-size: 1em;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 6px;
            line-height: 1.4;
        }}
        
        .card-brand {{
            font-size: 0.85em;
            color: var(--accent);
            margin-bottom: 8px;
        }}
        
        .card-desc {{
            font-size: 0.8em;
            color: var(--text-dim);
            line-height: 1.5;
            margin-bottom: 12px;
        }}
        
        .card-link {{
            display: inline-block;
            font-size: 0.8em;
            color: var(--link);
            text-decoration: none;
            padding: 6px 12px;
            background: rgba(59, 130, 246, 0.1);
            border-radius: 6px;
            transition: all 0.2s;
        }}
        
        .card-link:hover {{
            background: var(--link);
            color: white;
        }}
        
        .history-bar {{
            background: var(--bg-card);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }}
        
        .history-bar h3 {{
            font-size: 0.9em;
            color: var(--text-dim);
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .history-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .history-link {{
            padding: 8px 14px;
            background: var(--bg-dark);
            border-radius: 8px;
            font-size: 0.85em;
            color: var(--link);
            text-decoration: none;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }}
        
        .history-link:hover {{
            background: var(--bg-card-hover);
            border-color: var(--link);
        }}
        
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #555;
            font-size: 0.85em;
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }}
        
        .footer a {{
            color: #666;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 16px; }}
            h1 {{ font-size: 2em; }}
            .section-grid {{ grid-template-columns: 1fr; }}
            .stats {{ gap: 12px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 AD RADAR</h1>
            <p class="subtitle">Daily Best Advertising Campaigns | {date_str}</p>
            <div class="stats">
                <span>📢 {total} campaigns tracked</span>
                {''.join(f'<span>{src}</span>' for src in sources.keys())}
            </div>
        </header>
        
        <div class="history-bar">
            <h3>📅 Archive (last 30 days)</h3>
            <div class="history-links">
'''
    
    # Add history links (absolute path for GitHub Pages subfolder)
    if HISTORY_DIR.exists():
        history_files = sorted(HISTORY_DIR.glob("????-??-??.html"), reverse=True)[:30]
        for hist_file in history_files:
            hist_date = hist_file.stem
            html += f'<a href="/ad-radar/history/{hist_file.name}" class="history-link">{hist_date}</a>'
    
    html += '''
            </div>
        </div>
'''
    
    # Generate sections
    for sec_key, sec in sections.items():
        cards = sec["cards"]
        html += f'''
        <div class="section">
            <div class="section-header">
                <span class="section-title">{sec['name']}</span>
                <span class="section-count">{len(cards)} campaigns</span>
            </div>
            <div class="section-grid">
'''
        
        if cards:
            html += ''.join(cards)
        else:
            html += '<p style="color: var(--text-dim); padding: 20px; text-align: center;">No campaigns in this category yet.</p>'
        
        html += '''
            </div>
        </div>
'''
    
    html += '''
        <div class="footer">
            <p>Ad Radar monitors advertising creativity from top industry sources</p>
            <p>Sources: Ads of the World, Campaign Brief | Updated daily at 05:00 Prague</p>
        </div>
    </div>
</body>
</html>
'''
    return html


import os
from pathlib import Path

# Ensure directories exist
WWW_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def save_snapshot(html, date_str):
    """Save a dated snapshot."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = HISTORY_DIR / f"{date_str}.html"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(html)
    return snapshot_path


def main():
    # Ensure directories exist
    WWW_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    db = get_db()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    html = generate_dashboard(db, date_str)
    
    index_path = WWW_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    snapshot = save_snapshot(html, date_str)
    
    db.close()
    
    print(f"Dashboard: {index_path}")
    print(f"Snapshot: {snapshot}")
    return str(index_path)


if __name__ == "__main__":
    main()
