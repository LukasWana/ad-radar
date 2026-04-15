#!/usr/bin/env python3
"""Find banner image sources"""
from playwright.sync_api import sync_playwright

SOURCES = [
    {"name": "Google Display Network Examples", "url": "https://www.google.com/search?q=display+banner+advertising+examples&tbm=isch"},
    {"name": "Banners Library", "url": "https://www.bannersnack.com"},
    {"name": "Ad formats Google", "url": "https://support.google.com/displayvideo/answer/6093851"},
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for source in SOURCES:
        print(f"\n=== {source['name']} ===")
        try:
            page.goto(source["url"], timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            imgs = page.query_selector_all("img")
            for i, img in enumerate(imgs[:20]):
                src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                alt = img.get_attribute("alt") or ""
                w = img.get_attribute("width") or ""
                h = img.get_attribute("height") or ""
                
                if src and len(src) > 30:
                    print(f"[{w}x{h}] {alt[:50]}: {src[:120]}")
        except Exception as e:
            print(f"Error: {e}")
    
    browser.close()
