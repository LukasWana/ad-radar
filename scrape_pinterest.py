from playwright.sync_api import sync_playwright
import json
from datetime import datetime
from urllib.parse import urlparse

OUTPUT_FILE = "daily_banners.json"

def normalize_url(img_src, base_url):
    if not img_src:
        return None
    if img_src.startswith("//"):
        return "https:" + img_src
    elif img_src.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{img_src}"
    return img_src

def get_high_res_pinterest(url):
    """Convert Pinterest image URLs to higher resolution"""
    if "i.pinimg.com" in url:
        # 236x -> 736x, 564x -> 736x
        url = url.replace("/236x/", "/736x/")
        url = url.replace("/564x/", "/736x/")
        url = url.replace("/600x/", "/736x/")
        url = url.replace("/474x/", "/736x/")
    return url

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Pinterest search queries for advertising
    queries = [
        "advertising banner design inspiration",
        "marketing campaign visual",
        "brand advertising photo",
        "digital marketing banner"
    ]
    
    all_banners = []
    
    for q in queries:
        if len(all_banners) >= 4:
            break
        try:
            url = f"https://www.pinterest.com/search/pins/?q={q.replace(' ', '%20')}"
            print(f"Searching Pinterest: {q}...")
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            
            # Scroll multiple times to load images
            for i in range(4):
                page.evaluate("window.scrollTo(0, window.scrollY + 800)")
                page.wait_for_timeout(400)
            
            imgs = page.query_selector_all("img")
            print(f"  Found {len(imgs)} images")
            
            for img in imgs:
                src = img.get_attribute("src") or ""
                alt = img.get_attribute("alt") or ""
                
                # Filter: skip logos, icons, small pins
                if "logo" in alt.lower() or "avatar" in alt.lower():
                    continue
                if "/236x/" in src or "/150x/" in src:
                    continue
                if len(src) < 100:
                    continue
                    
                high_res = get_high_res_pinterest(src)
                
                if high_res and high_res.startswith("http"):
                    all_banners.append({
                        "id": len(all_banners) + 1,
                        "title": alt[:50] if alt else f"Banner - {q}",
                        "brand": "Pinterest",
                        "source": "Pinterest",
                        "imageUrl": high_res,
                        "dimensions": "800x450",
                        "format": "banner"
                    })
                    print(f"  Added: {alt[:40]}...")
                    break  # One good image per query
                    
        except Exception as e:
            print(f"Error: {e}")
    
    browser.close()
    
    # Fallback
    if len(all_banners) < 4:
        print("Adding Unsplash fallbacks...")
        fallbacks = [
            {"title": "Business Meeting", "url": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800&q=80"},
            {"title": "Marketing Strategy", "url": "https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=800&q=80"},
            {"title": "Digital Analytics", "url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80"},
            {"title": "Team Collaboration", "url": "https://images.unsplash.com/photo-1557838923-2985c318be48?w=800&q=80"},
        ]
        for fb in fallbacks:
            if len(all_banners) >= 4:
                break
            all_banners.append({
                "id": len(all_banners) + 1,
                "title": fb["title"],
                "brand": "Unsplash",
                "source": "Unsplash",
                "imageUrl": fb["url"],
                "dimensions": "800x450",
                "format": "banner"
            })
    
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(),
        "banners": all_banners[:4]
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(all_banners[:4])} banners")
