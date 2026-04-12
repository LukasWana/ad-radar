#!/usr/bin/env python3
"""
Ad Radar Pipeline — Complete monitoring system
Fetches, scrapes, analyzes, deduplicates and delivers best advertising campaigns
"""

import sys
import json
import time
import re
import sqlite3
import hashlib
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# YouTube API Key (from Google Cloud Console)
YOUTUBE_API_KEY = "AIzaSyB0W1rRyYwI0oyC80TotvWQwnr5LyK6wOg"
YOUTUBE_CHANNEL_ID = "UC2EVergrsTcwpZbAeboHSQQ"

# Setup path for imports
WS_DIR = Path(__file__).parent
SCRAPER_PATH = WS_DIR.parent / "web-scraper"
sys.path.insert(0, str(SCRAPER_PATH))

try:
    from web_scraper import WebScraper
except ImportError:
    print("web_scraper not found in skills/web-scraper/")
    sys.exit(1)

# DB_PATH
DB_PATH = WS_DIR / "ad_radar.db"


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
        CREATE INDEX IF NOT EXISTS idx_campaigns_category ON campaigns(category);
        CREATE INDEX IF NOT EXISTS idx_campaigns_score ON campaigns(score DESC);
        CREATE INDEX IF NOT EXISTS idx_campaigns_delivered ON campaigns(is_delivered);
        
        CREATE TABLE IF NOT EXISTS dashboard_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            campaigns_count INTEGER,
            categories TEXT,
            content TEXT
        );
    """)
    db.commit()
    return db


def generate_campaign_id(url: str, brand: str, title: str) -> str:
    raw = f"{url}|{brand}|{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def campaign_exists(db, campaign_id: str) -> bool:
    cursor = db.execute("SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,))
    return cursor.fetchone() is not None


def get_delivered_ids(db, days: int = 30) -> set:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = db.execute(
        "SELECT id FROM campaigns WHERE is_delivered = 1 AND delivered_at >= ?",
        (cutoff,)
    )
    return {row["id"] for row in cursor.fetchall()}


def insert_campaign(db, **kwargs):
    campaign_id = generate_campaign_id(
        kwargs.get("url", ""),
        kwargs.get("brand", ""),
        kwargs.get("title", "")
    )
    now = datetime.now().isoformat()
    
    existing = db.execute(
        "SELECT id, view_count FROM campaigns WHERE id = ?", (campaign_id,)
    ).fetchone()
    
    if existing:
        db.execute("""
            UPDATE campaigns 
            SET view_count = view_count + 1,
                last_seen = ?,
                score = MAX(score, ?)
            WHERE id = ?
        """, (now, kwargs.get("score", 0), campaign_id))
    else:
        db.execute("""
            INSERT INTO campaigns (
                id, url, title, brand, agency, description, category,
                score, image_url, source, discovered_at, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id,
            kwargs.get("url", ""),
            kwargs.get("title", ""),
            kwargs.get("brand", ""),
            kwargs.get("agency", ""),
            kwargs.get("description", ""),
            kwargs.get("category", ""),
            kwargs.get("score", 0),
            kwargs.get("image_url", ""),
            kwargs.get("source", ""),
            now, now, now
        ))
    db.commit()
    return campaign_id


def mark_delivered(db, campaign_ids: List[str]):
    now = datetime.now().isoformat()
    for cid in campaign_ids:
        db.execute(
            "UPDATE campaigns SET is_delivered = 1, delivered_at = ? WHERE id = ?",
            (now, cid)
        )
    db.commit()


def save_dashboard(db, count: int, categories: dict, content: str):
    db.execute("""
        INSERT INTO dashboard_history (generated_at, campaigns_count, categories, content)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), count, json.dumps(categories), content))
    db.commit()


def get_stats(db):
    total = db.execute("SELECT COUNT(*) as c FROM campaigns").fetchone()["c"]
    delivered = db.execute(
        "SELECT COUNT(*) as c FROM campaigns WHERE is_delivered = 1"
    ).fetchone()["c"]
    avg_score = db.execute("SELECT AVG(score) as avg FROM campaigns").fetchone()["avg"]
    return {
        "total_campaigns": total,
        "delivered": delivered,
        "avg_score": round(avg_score, 1) if avg_score else 0
    }


@dataclass
class Campaign:
    url: str
    title: str = ""
    brand: str = ""
    agency: str = ""
    description: str = ""
    category: str = ""
    score: int = 0
    image_url: str = ""
    video_url: str = ""
    source: str = ""
    published_at: str = ""
    why_great: str = ""


class AdRadarPipeline:
    SOURCES = {
        "ads_of_the_world": {
            "url": "https://www.adsoftheworld.com/",
            "selector": "a[href*='/campaigns/' i]",
        },
        "campaign_brief": {
            "url": "https://www.Campaignbrief.com/",
            "selector": "a[href*='/campaigns/' i], a[href*='article/' i]",
        },
        "ceske_reklamy": {
            "type": "youtube_api",
        },
        "mediacz_katovna": {
            "url": "https://www.mediar.cz/galerie-reklamy/",
            "selector": "a[href*='/galerie-reklamy/' i]",
        },
        "youtube_works_awards": {
            "type": "youtube_playlist",
            "playlist_id": "PLzCg1lz81rBeNdKxFlS6fNQnP4rX4MNq-",
        },
        "campaign_brief_awards": {
            "url": "https://www.Campaignbrief.com/awards/",
            "selector": "a[href*='/campaigns/' i], a[href*='article/' i]",
        },
    }
    
    CATEGORIES = {
        "tv": ["tv", "commercial", "spot", "video", "super bowl", "youtube"],
        "print": ["print", "outdoor", "ooh", "billboard", "magazine"],
        "online": ["digital", "online", "social", "display", "pre-roll"],
        "brand": ["brand", "logo", "identity", "rebrand", "typography"]
    }
    
    def __init__(self, max_per_category: int = 3, min_score: int = 5,
                 rate_limit_delay: float = 0.5, limit: int = 30):
        self.max_per_category = max_per_category
        self.min_score = min_score
        self.rate_limit_delay = rate_limit_delay
        self.limit = limit
        self.scraper = WebScraper()
        self.db = get_db()
        self.dashboard_entries: Dict[str, List[Campaign]] = {}
    
    def discover_urls(self) -> List[Tuple[str, str]]:
        discovered = []
        
        for source_name, config in self.SOURCES.items():
            try:
                # Handle YouTube Data API v3 (fetches ALL videos from channel)
                if config.get("type") == "youtube_api":
                    print(f"Discovering from {source_name} (YouTube API)...")
                    
                    try:
                        # Get uploads playlist ID for channel
                        channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}"
                        req = urllib.request.Request(channel_url)
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            channel_data = json.loads(resp.read())
                        
                        uploads_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                        
                        # Fetch ALL videos from uploads playlist
                        all_videos = []
                        next_page = None
                        while True:
                            page_param = f"&pageToken={next_page}" if next_page else ""
                            videos_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={uploads_id}&maxResults=50{page_param}&key={YOUTUBE_API_KEY}"
                            req2 = urllib.request.Request(videos_url)
                            with urllib.request.urlopen(req2, timeout=15) as resp2:
                                videos_data = json.loads(resp2.read())
                            
                            all_videos.extend(videos_data.get("items", []))
                            next_page = videos_data.get("nextPageToken")
                            if not next_page:
                                break
                        
                        for v in all_videos:
                            snippet = v["snippet"]
                            vid = v["contentDetails"]["videoId"]
                            youtube_url = f"https://www.youtube.com/watch?v={vid}"
                            discovered.append((source_name, youtube_url))
                        
                        print(f"  Found {len(all_videos)} videos via API")
                    except Exception as e:
                        print(f"  YouTube API error: {e}")
                    continue
                
                # Handle YouTube playlists (YouTube Works Awards etc.)
                if config.get("type") == "youtube_playlist":
                    print(f"Discovering from {source_name} (YouTube Playlist)...")
                    try:
                        playlist_id = config.get("playlist_id")
                        playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={playlist_id}&maxResults=50&key={YOUTUBE_API_KEY}"
                        req = urllib.request.Request(playlist_url)
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            data = json.loads(resp.read())
                        
                        items = data.get("items", [])
                        for item in items:
                            vid = item.get("contentDetails", {}).get("videoId", "")
                            if vid:
                                youtube_url = f"https://www.youtube.com/watch?v={vid}"
                                discovered.append((source_name, youtube_url))
                        
                        print(f"  Found {len(items)} playlist videos")
                    except Exception as e:
                        print(f"  YouTube playlist error: {e}")
                    continue
                
                # Handle RSS feeds (YouTube channels)
                if config.get("type") == "rss":
                    print(f"Discovering from {source_name} (RSS)...")
                    result = self.scraper.extract(
                        url=config["url"],
                        extract_type="article"
                    )
                    if result["error"]:
                        print(f"  Error: {result['error']}")
                        continue
                    
                    # Parse YouTube RSS: extract video IDs and titles
                    # YouTube RSS is NOT standard XML - titles are plain text lines
                    text = result.get("extracted", "")
                    lines = text.split('\n')
                    
                    # Find all video entries (lines starting with yt:video:)
                    video_entries = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('yt:video:'):
                            video_id = line.strip().split('yt:video:')[1]
                            # Title is 3 lines after the ID line (after ID repeat, channel ID)
                            if i + 3 < len(lines):
                                title = lines[i + 3].strip()
                                video_entries.append((video_id, title))
                    
                    for vid, title in video_entries:
                        youtube_url = f"https://www.youtube.com/watch?v={vid}"
                        discovered.append((source_name, youtube_url))
                    
                    print(f"  Found {len(video_entries)} videos")
                    continue
                
                # Regular web scraping
                print(f"Discovering from {source_name}...")
                result = self.scraper.extract(
                    url=config["url"],
                    selector=config["selector"],
                    extract_type="links"
                )
                
                if result["error"]:
                    print(f"  Error: {result['error']}")
                    continue
                
                links = result["extracted"]
                campaign_links = [
                    (source_name, l) for l in links
                    if ("/campaigns/" in l.lower() or "/galerie-reklamy/" in l.lower())
                    and "/campaigns/new" not in l.lower()
                ]
                
                # Deduplicate
                seen = set()
                unique = []
                for src, link in campaign_links:
                    if link not in seen:
                        seen.add(link)
                        unique.append((src, link))
                
                print(f"  Found {len(unique)} campaign links")
                discovered.extend(unique[:15])
                
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"  Exception: {e}")
                continue
        
        return discovered
    
    def scrape_and_analyze(self, urls: List[Tuple[str, str]]) -> List[Campaign]:
        campaigns = []
        
        for source_name, url in urls[:self.limit]:
            try:
                # Build full URL
                if url.startswith("http"):
                    full_url = url
                elif url.startswith("/"):
                    if "adsoftheworld" in source_name:
                        full_url = f"https://www.adsoftheworld.com{url}"
                    elif "campaignbrief" in source_name:
                        full_url = f"https://www.Campaignbrief.com{url}"
                    elif "mediacz" in source_name:
                        full_url = f"https://www.mediar.cz{url}"
                    else:
                        full_url = f"https://www.adsoftheworld.com{url}"
                else:
                    full_url = url
                
                print(f"Scraping: {full_url[:60]}...")
                
                # YouTube source - use oEmbed for metadata
                if "youtube.com" in full_url or "ceske_reklamy" in source_name:
                    import json
                    # Get video ID from URL
                    video_id_match = re.search(r'(?:v=|/v/)([a-zA-Z0-9_-]{11})', full_url)
                    if not video_id_match:
                        continue
                    video_id = video_id_match.group(1)
                    
                    # Use oEmbed API
                    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                    oembed_result = self.scraper.extract(oembed_url, extract_type="article")
                    
                    if oembed_result["error"] or not oembed_result["extracted"]:
                        continue
                    
                    try:
                        oembed_data = json.loads(oembed_result["extracted"])
                    except:
                        continue
                    
                    title = oembed_data.get("title", "")
                    thumbnail = oembed_data.get("thumbnail_url", "")
                    
                    # Parse brand from title like "Reklama - Vileda (CZ, 2022)"
                    campaign = Campaign(
                        url=full_url,
                        title=title,
                        video_url=full_url,
                        image_url=thumbnail,
                        source=source_name
                    )
                    
                    # Extract brand from title
                    if " - " in title:
                        parts = title.split(" - ", 1)
                        if len(parts) > 1:
                            brand_part = parts[1].split("(")[0].strip()
                            campaign.brand = brand_part
                    
                    # Score based on title keywords
                    text_lower = title.lower()
                    score = 5
                    if any(w in text_lower for w in ["award", "grand prix", "gold", "best"]):
                        score += 2
                    if "cz" in text_lower or "česk" in text_lower:
                        score += 1
                    campaign.score = score
                    campaign.category = self._categorize(text_lower)
                    
                    if campaign.score >= self.min_score:
                        campaigns.append(campaign)
                    
                    time.sleep(self.rate_limit_delay)
                    continue
                
                # Regular web scraping
                result = self.scraper.extract(full_url, extract_type="article")
                
                if result["error"] or not result["extracted"]:
                    continue
                
                text = result["extracted"]
                if isinstance(text, list):
                    text = " ".join(text)
                
                campaign = self._parse_campaign(full_url, text,
                                                result.get("title", ""),
                                                source_name)
                
                campaign.score = self._calculate_score(campaign, text)
                campaign.category = self._categorize(text)
                
                if campaign.score >= self.min_score:
                    campaigns.append(campaign)
                
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        return campaigns
    
    def _parse_campaign(self, url: str, text: str, title: str, source: str) -> Campaign:
        campaign = Campaign(url=url, title=title, source=source)
        
        if title:
            parts = re.split(r'[:\-]', title, 1)
            if len(parts) > 1:
                campaign.brand = parts[0].strip()
                campaign.title = parts[1].strip()
            else:
                campaign.brand = title.split()[0] if title else ""
        
        agency_match = re.search(
            r'by\s+([A-Z][a-zA-Z\s&]+(?:Agency|Studios?|Creative)?)',
            text, re.IGNORECASE
        )
        if agency_match:
            campaign.agency = agency_match.group(1).strip()
        
        lines = text.split("\n")
        meaningful = [l.strip() for l in lines if len(l.strip()) > 50][:5]
        campaign.description = " ".join(meaningful)[:500]
        
        img_result = self.scraper.extract(url, extract_type="images")
        if not img_result["error"]:
            images = img_result["extracted"]
            campaign.image_url = next(
                (i for i in images if i and ("campaign" in i.lower() or "ad" in i.lower())),
                images[0] if images else ""
            )
        
        return campaign
    
    def _calculate_score(self, campaign: Campaign, text: str) -> int:
        score = 5
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["award", "grand prix", "gold"]):
            score += 2
        if any(w in text_lower for w in ["viral", "trending", "most shared"]):
            score += 1
        if campaign.agency:
            score += 1
        if len(text) > 500:
            score += 1
        
        return max(0, min(10, score))
    
    def _categorize(self, text: str) -> str:
        text_lower = text.lower()
        scores = {
            cat: sum(1 for kw in keywords if kw in text_lower)
            for cat, keywords in self.CATEGORIES.items()
        }
        return max(scores, key=scores.get) if scores else "online"
    
    def deduplicate_and_rank(self, campaigns: List[Campaign]) -> Dict[str, List[Campaign]]:
        seen_ids = get_delivered_ids(self.db, days=30)
        
        ranked: Dict[str, List[Campaign]] = {
            "grand_prix": [],
            "tv": [],
            "print": [],
            "online": [],
            "brand": []
        }
        
        for campaign in campaigns:
            cid = generate_campaign_id(campaign.url, campaign.brand, campaign.title)
            
            if cid in seen_ids:
                continue
            
            if not campaign_exists(self.db, cid):
                insert_campaign(
                    self.db,
                    url=campaign.url,
                    title=campaign.title,
                    brand=campaign.brand,
                    agency=campaign.agency,
                    description=campaign.description,
                    category=campaign.category,
                    score=campaign.score,
                    image_url=campaign.image_url,
                    source=campaign.source
                )
            
            if campaign.score >= self.min_score:
                ranked["grand_prix"].append(campaign)
                cat = campaign.category if campaign.category in ranked else "online"
                ranked[cat].append(campaign)
        
        for cat in ranked:
            ranked[cat] = sorted(ranked[cat], key=lambda c: c.score, reverse=True)
            ranked[cat] = ranked[cat][:self.max_per_category]
        
        return ranked
    
    def generate_dashboard(self, ranked: Dict[str, List[Campaign]]) -> str:
        now = datetime.now().strftime("%B %d, %Y")
        
        lines = [
            f"# AD RADAR - Daily Best Advertising Dashboard",
            f"**{now}** | *Generated by Ad Radar Pipeline v2*",
            "",
            "---",
            ""
        ]
        
        if ranked["grand_prix"]:
            lines.append("## GRAND PRIX - Best of the Best")
            lines.append("")
            for c in ranked["grand_prix"][:3]:
                why = c.description[:150] + "..." if len(c.description) > 150 else c.description
                lines.extend([
                    f"### {c.brand} - {c.title}",
                    f"**Why:** {why or 'Outstanding creative work'}",
                    f"**Agency:** {c.agency}" if c.agency else "",
                    f"[View]({c.url})",
                    ""
                ])
        
        category_names = {
            "tv": ("TV / CINEMA", "Best commercials and viral video ads"),
            "print": ("PRINT / OUT-OF-HOME", "Billboards, outdoor, magazine ads"),
            "online": ("ONLINE / DIGITAL", "Social media, display, pre-roll campaigns"),
            "brand": ("BRAND / LOGO", "Logo redesigns, brand identity systems")
        }
        
        for cat, (title, desc) in category_names.items():
            entries = ranked.get(cat, [])
            if entries:
                lines.extend([
                    f"## {title}",
                    f"*{desc}*",
                    ""
                ])
                for c in entries:
                    why = c.description[:100] + "..." if len(c.description) > 100 else c.description
                    lines.extend([
                        f"**{c.brand} - {c.title}**",
                        f"Why: {why or 'Creative campaign'}",
                        f"[Link]({c.url})",
                        ""
                    ])
        
        lines.extend([
            "---",
            "## Sources",
            *[f"- {name}" for name in self.SOURCES.keys()],
            "",
            "*Ad Radar Pipeline v2*"
        ])
        
        return "\n".join(lines)
    
    def run(self, dry_run: bool = False) -> Optional[str]:
        print("=" * 50)
        print("AD RADAR PIPELINE v2")
        print("=" * 50)
        
        start = time.time()
        
        print("\n[1/4] Discovering campaign URLs...")
        urls = self.discover_urls()
        print(f"  Found {len(urls)} total")
        
        if not urls:
            print("  No URLs found")
            return None
        
        print("\n[2/4] Scraping and analyzing...")
        campaigns = self.scrape_and_analyze(urls)
        print(f"  Analyzed {len(campaigns)} campaigns")
        
        if not campaigns:
            return None
        
        print("\n[3/4] Deduplicating and ranking...")
        ranked = self.deduplicate_and_rank(campaigns)
        for cat, entries in ranked.items():
            print(f"  {cat}: {len(entries)} entries")
        
        print("\n[4/4] Generating dashboard...")
        dashboard = self.generate_dashboard(ranked)
        
        if not dry_run:
            save_dashboard(self.db, len(campaigns),
                          {k: len(v) for k, v in ranked.items()},
                          dashboard)
            mark_delivered(self.db, [
                generate_campaign_id(c.url, c.brand, c.title)
                for c in campaigns
            ])
        
        elapsed = time.time() - start
        stats = get_stats(self.db)
        
        print(f"\nComplete in {elapsed:.1f}s")
        print(f"  Total in DB: {stats['total_campaigns']}")
        print(f"  Delivered: {stats['delivered']}")
        
        self.scraper.close()
        self.db.close()
        
        return dashboard


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ad Radar Pipeline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-score", type=int, default=5)
    args = parser.parse_args()
    
    pipeline = AdRadarPipeline(
        max_per_category=3,
        min_score=args.min_score,
        rate_limit_delay=0.5,
        limit=args.limit
    )
    
    result = pipeline.run(dry_run=args.dry_run)
    
    if result:
        print("\n" + "=" * 50)
        print("DASHBOARD OUTPUT")
        print("=" * 50)
        print(result)
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())