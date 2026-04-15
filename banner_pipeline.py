#!/usr/bin/env python3
"""
Ad Radar Banner Pipeline
Collects 4 fresh banners daily from top advertising sources
"""

import json
import httpx
from datetime import datetime
from pathlib import Path

# Configuration
OUTPUT_FILE = Path(__file__).parent / "daily_banners.json"
TELEGRAM_BOT_TOKEN = "8620718858:AAHQfTXZSyzlEUQpHVUKjdD4a7vvUJdRoWA"
TELEGRAM_CHAT_ID = "5370808247"

# Banner sources with selectors
SOURCES = {
    "awwwards": {
        "url": "https://www.awwwards.com/websites/awards/",
        "selector": ".website-item .visual img",
        "name": "Awwwards"
    },
    "behance": {
        "url": "https://www.behance.net/featured",
        "selector": ".project-card img",
        "name": "Behance"
    },
    "dribbble": {
        "url": "https://dribbble.com/shots/popular",
        "selector": ".shot-thumbnail img",
        "name": "Dribbble"
    },
    "cssdesignawards": {
        "url": "https://www.cssdesignawards.com/",
        "selector": ".project-image img",
        "name": "CSS Design Awards"
    }
}

def fetch_banners():
    """Fetch banners from sources"""
    banners = []
    
    with httpx.Client(timeout=30) as client:
        for source_id, source in SOURCES.items():
            try:
                response = client.get(source["url"])
                # In production, use BeautifulSoup to extract images
                # For now, use placeholder logic
                banners.append({
                    "id": len(banners) + 1,
                    "title": f"Banner from {source['name']}",
                    "brand": "Various",
                    "source": f"{source_id}.com",
                    "imageUrl": f"https://picsum.photos/seed/banner_{source_id}_{datetime.now().strftime('%Y%m%d')}/800/450",
                    "dimensions": "728x90",
                    "format": "leaderboard"
                })
            except Exception as e:
                print(f"Error fetching {source['name']}: {e}")
    
    return banners[:4]

def save_banners(banners):
    """Save banners to JSON file"""
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(),
        "banners": banners
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(banners)} banners to {OUTPUT_FILE}")
    return data

def send_telegram(data):
    """Send daily summary to Telegram"""
    if not data["banners"]:
        return
    
    # Build message
    date_str = datetime.now().strftime("%d.%m.%Y")
    message = f"🎯 *Ad Radar — Denní bannery*\n"
    message += f"📅 {date_str}\n\n"
    
    for i, banner in enumerate(data["banners"], 1):
        message += f"{i}. *{banner['title']}*\n"
        message += f"   🏷️ {banner['brand']} | {banner['dimensions']}\n"
        message += f"   📍 {banner['source']}\n\n"
    
    message += f"📊 Zdroj: https://ad-radar-banners.surge.sh"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"Telegram message sent successfully")
        else:
            print(f"Telegram error: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram: {e}")

def main():
    print(f"Starting Ad Radar Banner Pipeline at {datetime.now()}")
    
    banners = fetch_banners()
    data = save_banners(banners)
    send_telegram(data)
    
    print("Pipeline completed!")

if __name__ == "__main__":
    main()
