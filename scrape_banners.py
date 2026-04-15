#!/usr/bin/env python3
"""Scrape real banner images from Google Images"""
from playwright.sync_api import sync_playwright
import json
from datetime import datetime
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "daily_banners.json"

def scrape_google_banners():
    banners = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Search queries for different banner types
        queries = [
            ("display advertising banner examples", "display"),
            ("social media advertisement banner", "social"),
            ("google ads banner examples", "google"),
            ("facebook ads creative banner", "facebook"),
        ]
        
        for query, banner_type in queries:
            try:
                print(f"Searching: {query}")
                search_url = f"https://www.google.com/search?tbm=isch&q={query.replace(' ', '+')}+banner&udm=2"
                page.goto(search_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
                
                # Get image results
                imgs = page.query_selector_all("img")
                for img in imgs[:5]:
                    src = img.get_attribute("src")
                    if src and src.startswith("http") and "encrypted" not in src:
                        banners.append({
                            "id": len(banners) + 1,
                            "title": f"{banner_type.title()} Banner",
                            "brand": "Various",
                            "source": f"Google Images - {query[:30]}",
                            "imageUrl": src,
                            "dimensions": "800x450",
                            "format": banner_type
                        })
                        if len(banners) >= 4:
                            break
                            
            except Exception as e:
                print(f"Error with {query}: {e}")
                
            if len(banners) >= 4:
                break
        
        browser.close()
    
    return banners[:4]

def save_banners(banners):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(),
        "banners": banners
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(banners)} banners")
    return data

if __name__ == "__main__":
    banners = scrape_google_banners()
    if banners:
        save_banners(banners)
    else:
        print("No banners found")
