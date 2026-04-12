#!/usr/bin/env python3
"""
Ad Radar — SQLite Database for History Tracking
Stores campaign history for dedup and trend analysis
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "ad_radar.db"


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    _init_db(db)
    return db


def _init_db(db: sqlite3.Connection):
    """Initialize database schema."""
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
        CREATE INDEX IF NOT EXISTS idx_campaigns_discovered ON campaigns(discovered_at);
        CREATE INDEX IF NOT EXISTS idx_campaigns_score ON campaigns(score DESC);
        CREATE INDEX IF NOT EXISTS idx_campaigns_delivered ON campaigns(is_delivered);
        
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            last_checked TEXT,
            campaigns_found INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS dashboard_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            campaigns_count INTEGER,
            categories TEXT,
            content TEXT,
            raw_json TEXT
        );
        
        CREATE TABLE IF NOT EXISTS dedup_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT,
            reason TEXT,
            checked_at TEXT
        );
    """)
    db.commit()


def generate_campaign_id(url: str, brand: str, title: str) -> str:
    """Generate unique ID from campaign data."""
    raw = f"{url}|{brand}|{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def campaign_exists(db: sqlite3.Connection, campaign_id: str) -> bool:
    """Check if campaign already exists."""
    cursor = db.execute(
        "SELECT 1 FROM campaigns WHERE id = ?", (campaign_id,)
    )
    return cursor.fetchone() is not None


def is_recently_delivered(db: sqlite3.Connection, campaign_id: str, days: int = 30) -> bool:
    """Check if campaign was delivered within last N days."""
    cursor = db.execute("""
        SELECT delivered_at FROM campaigns 
        WHERE id = ? AND is_delivered = 1
    """, (campaign_id,))
    row = cursor.fetchone()
    if not row or not row["delivered_at"]:
        return False
    delivered_at = datetime.fromisoformat(row["delivered_at"])
    return datetime.now() - delivered_at < timedelta(days=days)


def insert_campaign(
    db: sqlite3.Connection,
    url: str,
    title: str = None,
    brand: str = None,
    agency: str = None,
    description: str = None,
    category: str = None,
    score: int = 0,
    image_url: str = None,
    video_url: str = None,
    source: str = None,
    published_at: str = None,
    metadata: dict = None
) -> str:
    """Insert or update campaign."""
    campaign_id = generate_campaign_id(url, brand or "", title or "")
    
    now = datetime.now().isoformat()
    
    # Check if exists
    existing = db.execute(
        "SELECT id, view_count FROM campaigns WHERE id = ?", (campaign_id,)
    ).fetchone()
    
    if existing:
        # Update view count and last_seen
        db.execute("""
            UPDATE campaigns 
            SET view_count = view_count + 1,
                last_seen = ?,
                score = MAX(score, ?)
            WHERE id = ?
        """, (now, score, campaign_id))
    else:
        db.execute("""
            INSERT INTO campaigns (
                id, url, title, brand, agency, description, category,
                score, image_url, video_url, source, published_at,
                discovered_at, first_seen, last_seen, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id, url, title, brand, agency, description, category,
            score, image_url, video_url, source, published_at,
            now, now, now, json.dumps(metadata) if metadata else None
        ))
    
    db.commit()
    return campaign_id


def get_fresh_candidates(
    db: sqlite3.Connection,
    days: int = 7,
    min_score: int = 5,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent campaigns with high score not yet delivered."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = db.execute("""
        SELECT * FROM campaigns 
        WHERE discovered_at >= ?
          AND score >= ?
          AND is_delivered = 0
        ORDER BY score DESC, discovered_at DESC
        LIMIT ?
    """, (cutoff, min_score, limit))
    return [dict(row) for row in cursor.fetchall()]


def get_delivered_ids(
    db: sqlite3.Connection,
    days: int = 30
) -> set:
    """Get IDs of recently delivered campaigns."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = db.execute("""
        SELECT id FROM campaigns 
        WHERE is_delivered = 1 AND delivered_at >= ?
    """, (cutoff,))
    return {row["id"] for row in cursor.fetchall()}


def mark_delivered(db: sqlite3.Connection, campaign_ids: List[str]):
    """Mark campaigns as delivered."""
    now = datetime.now().isoformat()
    for cid in campaign_ids:
        db.execute("""
            UPDATE campaigns 
            SET is_delivered = 1, delivered_at = ?
            WHERE id = ?
        """, (now, cid))
    db.commit()


def save_dashboard(
    db: sqlite3.Connection,
    campaigns_count: int,
    categories: dict,
    content: str,
    raw_json: dict = None
) -> int:
    """Save generated dashboard to history."""
    cursor = db.execute("""
        INSERT INTO dashboard_history (
            generated_at, campaigns_count, categories, content, raw_json
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        campaigns_count,
        json.dumps(categories),
        content,
        json.dumps(raw_json) if raw_json else None
    ))
    db.commit()
    return cursor.lastrowid


def update_source(db: sqlite3.Connection, name: str, url: str, priority: int = 1):
    """Update or insert source."""
    now = datetime.now().isoformat()
    db.execute("""
        INSERT INTO sources (name, url, priority, last_checked, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(name) DO UPDATE SET
            last_checked = excluded.last_checked,
            url = excluded.url
    """, (name, url, priority, now))
    db.commit()


def log_dedup(db: sqlite3.Connection, campaign_id: str, reason: str):
    """Log deduplication events."""
    db.execute("""
        INSERT INTO dedup_log (campaign_id, reason, checked_at)
        VALUES (?, ?, ?)
    """, (campaign_id, reason, datetime.now().isoformat()))
    db.commit()


def get_stats(db: sqlite3.Connection) -> dict:
    """Get database statistics."""
    total = db.execute("SELECT COUNT(*) as c FROM campaigns").fetchone()["c"]
    delivered = db.execute(
        "SELECT COUNT(*) as c FROM campaigns WHERE is_delivered = 1"
    ).fetchone()["c"]
    by_category = db.execute("""
        SELECT category, COUNT(*) as c 
        FROM campaigns 
        WHERE category IS NOT NULL 
        GROUP BY category
    """).fetchall()
    avg_score = db.execute(
        "SELECT AVG(score) as avg FROM campaigns"
    ).fetchone()["avg"]
    
    return {
        "total_campaigns": total,
        "delivered": delivered,
        "avg_score": round(avg_score, 1) if avg_score else 0,
        "by_category": {row["category"]: row["c"] for row in by_category}
    }


def close(db: sqlite3.Connection):
    """Close database connection."""
    db.close()


if __name__ == "__main__":
    db = get_db()
    stats = get_stats(db)
    print(f"Total campaigns: {stats['total_campaigns']}")
    print(f"Delivered: {stats['delivered']}")
    print(f"Avg score: {stats['avg_score']}")
    print("By category:", stats["by_category"])
    close(db)