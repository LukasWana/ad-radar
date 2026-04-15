from playwright.sync_api import sync_playwright
import json
from datetime import datetime

OUTPUT_FILE = "daily_banners.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    url = "https://www.google.com/search?newwindow=1&sca_esv=9735f8b237bb4fc8&sxsrf=ANbL-n4QO3QRJGMHkHgoS63udevtL5Bdfg&udm=2&fbs=ADc_l-aN0CWEZBOHjofHoaMMDiKpaEWjvZ2Py1XXV8d8KvlI3lB6BRmAv9Tdx4SvL4ZREsvDPG_QM7jWFgSsxS7TA_zUbtlW0a8OZ6OHXoP4m5uLlG86sHu6sl0Cb0J-JsVhNWvEUX421ivJSTdYIts9vdXswWbK75xhCZCl71NiWVBvvVYPO7JDk4qQRn8UYVU_w15UgZCV&q=real+advertisment+online+banners&sa=X&ved=2ahUKEwjcnrrcvu6TAxXGAxAIHWpTIGsQtKgLegQIFBAB&biw=1418&bih=734&dpr=1.25"
    
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=15000)
    
    banners = []
    imgs = page.query_selector_all("img")
    for img in imgs[:20]:
        src = img.get_attribute("src")
        alt = img.get_attribute("alt") or ""
        if src and src.startswith("http") and "encrypted" not in src and "gstatic" not in src:
            banners.append({
                "id": len(banners) + 1,
                "title": alt[:50] or "Advertisement Banner",
                "brand": "Various",
                "source": "Google Images",
                "imageUrl": src,
                "dimensions": "800x450",
                "format": "banner"
            })
    
    browser.close()
    
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat(),
        "banners": banners[:4]
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(banners[:4])} banners")
    for b in banners[:4]:
        print(f"  - {b['title']}: {b['imageUrl'][:80]}...")
