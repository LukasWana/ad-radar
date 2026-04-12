import sys
sys.path.insert(0, 'C:\\home\\node\\.openclaw\\workspace\\scripts')
from scraper_manager import scrape
from bs4 import BeautifulSoup
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "ad_radar.db"

CATEGORIES = {
    "tv": ["tv", "commercial", "spot", "video", "super bowl", "youtube"],
    "print": ["print", "outdoor", "ooh", "billboard", "magazine"],
    "online": ["digital", "online", "social", "display", "pre-roll"],
    "brand": ["brand", "logo", "identity", "rebrand", "typography"]
}

def categorize(text):
    text_lower = text.lower()
    scores = {
        cat: sum(1 for kw in keywords if kw in text_lower)
        for cat, keywords in CATEGORIES.items()
    }
    return max(scores, key=scores.get) if scores else "online"

def calculate_score(text):
    score = 5
    text_lower = text.lower()
    if any(w in text_lower for w in ["award", "grand prix", "gold"]):
        score += 2
    if any(w in text_lower for w in ["viral", "trending", "most shared"]):
        score += 1
    if len(text) > 500:
        score += 1
    return max(0, min(10, score))

def generate_campaign_id(url, brand, title):
    import hashlib
    raw = f"{url}|{brand}|{title}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

# Simulate what pipeline does
urls = [
    "https://www.adsoftheworld.com/campaigns/helmet-has-always-been-a-good-idea-1676",
    "https://www.adsoftheworld.com/campaigns/nothing-stops-women-s-rugby",
    "https://www.adsoftheworld.com/campaigns/mr-softie",
    "https://www.adsoftheworld.com/campaigns/midlife-back-in-session",
    "https://www.adsoftheworld.com/campaigns/drink-in-america",
]

campaigns = []
for url in urls:
    result = scrape(url)
    if result and result.get("success"):
        soup = BeautifulSoup(result["data"], "html.parser")
        text = soup.get_text(" ", strip=True)
        score = calculate_score(text)
        cat = categorize(text)
        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        brand = title.split(":")[0].strip() if ":" in title else ""
        cid = generate_campaign_id(url, brand, title)
        print(f"Campaign: {cid}")
        print(f"  Title: {title[:50]}")
        print(f"  Brand: {brand[:30]}")
        print(f"  Score: {score}, Category: {cat}")
        print(f"  ID: {cid}")
        campaigns.append({"url": url, "title": title, "brand": brand, "score": score, "category": cat, "id": cid})

# Now check DB
db = sqlite3.connect(str(DB_PATH))
db.row_factory = sqlite3.Row

# Check if any of these IDs are already delivered
print("\n\n=== Checking DB for these campaigns ===")
for c in campaigns:
    row = db.execute("SELECT is_delivered, delivered_at FROM campaigns WHERE id = ?", (c["id"],)).fetchone()
    if row:
        print(f"  {c['id']}: delivered={row['is_delivered']}, at={row['delivered_at']}")
    else:
        print(f"  {c['id']}: NOT IN DB")

# Check get_delivered_ids
cutoff = (datetime.now() - timedelta(days=30)).isoformat()
delivered_ids = {row["id"] for row in db.execute(
    "SELECT id FROM campaigns WHERE is_delivered = 1 AND delivered_at >= ?",
    (cutoff,)
).fetchall()}
print(f"\nDelivered IDs (last 30 days): {len(delivered_ids)}")
for cid in list(delivered_ids)[:5]:
    print(f"  {cid}")

db.close()
