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

def is_good_image(img_src, alt):
    """Filter out logos, icons, small images"""
    if not img_src:
        return False
    bad_patterns = ["logo", "icon", "avatar", "nav-", "thumb", "button", "badge"]
    if any(p in alt.lower() for p in bad_patterns):
        return False
    if any(p in img_src.lower() for p in bad_patterns):
        return False
    # Need larger images
    if "/236x/" in img_src or "/150x/" in img_src:
        return False
    return len(img_src) > 80

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Sources focusing on actual advertising campaigns and banners
    sources = [
        ("https://www.adsoftheworld.com/films", "Ads of the World Films"),
        ("https://www.adsoftheworld.com/print", "Ads of the World Print"),
        ("https://www.thedrum.com/creative-work", "The Drum"),
        ("https://www.canneslions.com/winners", "Cannes Lions Winners"),
        ("https://www.pinterest.com/search/pins/?q=advertising+campaign+print", "Pinterest"),
    ]
    
    all_banners = []
    
    for url, name in sources:
        if len(all_banners) >= 4:
            break
        try:
            print(f"Trying {name}...")
            page.goto(url, timeout=25000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)  # Wait for JS
            
            # Scroll to load more
            for _ in range(5):
                page.evaluate("window.scrollTo(0, window.scrollY + 1000)")
                page.wait_for_timeout(300)
            
            imgs = page.query_selector_all("img")
            print(f"  Found {len(imgs)} images on page")
            
            for img in imgs:
                src = img.get_attribute("src") or ""
                data_src = img.get_attribute("data-src") or ""
                alt = img.get_attribute("alt") or ""
                width = img.get_attribute("width") or "0"
                
                img_src = data_src if data_src else src
                
                if img_src:
                    img_src = normalize_url(img_src, url)
                    
                    if img_src and is_good_image(img_src, alt):
                        # Prefer larger images
                        w = int(width) if width.isdigit() else 0
                        if w > 300 or "/236x/" not in img_src:
                            all_banners.append({
                                "id": len(all_banners) + 1,
                                "title": alt[:60] if alt else f"Campaign from {name}",
                                "brand": "Creative Work",
                                "source": name,
                                "imageUrl": img_src,
                                "dimensions": f"{w}x{w}" if w > 0 else "800x450",
                                "format": "banner"
                            })
                            print(f"  Added: {alt[:40]}...")
                            
                            if len(all_banners) >= 4:
                                break
                                
        except Exception as e:
            print(f"Error with {name}: {e}")
    
    browser.close()
    
    # Final fallback - use Unsplash advertising/marketing photos
    if len(all_banners) < 4:
        print("Using Unsplash advertising photos...")
        fallbacks = [
            {"title": "Advertising Creative", "url": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800&q=80"},
            {"title": "Marketing Campaign", "url": "https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=800&q=80"},
            {"title": "Social Media Strategy", "url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80"},
            {"title": "Digital Marketing", "url": "https://images.unsplash.com/photo-1557838923-2985c318be48?w=800&q=80"},
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
    
    print(f"\nFinal: {len(all_banners[:4])} banners saved")
    for b in all_banners[:4]:
        print(f"  - {b['title']}: {b['source']}")
