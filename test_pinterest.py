import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def scrape_pinterest_ads(query, max_pins=30):
    """Scrape Pinterest for ad examples"""
    print(f"=== Pinterest Ad Scraper: {query} ===")
    
    ads = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        
        try:
            # Build search URL
            encoded_query = query.replace(' ', '%20')
            url = f"https://www.pinterest.com/search/pins/?q={encoded_query}"
            print(f"URL: {url}")
            
            page.goto(url, timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            time.sleep(3)
            
            # Dismiss cookie banner if present
            try:
                accept_btn = page.query_selector('button[title="Accept cookies"], button[data-test-id="cookie-banner-accept"]')
                if accept_btn:
                    accept_btn.click()
                    time.sleep(1)
                    print("Cookie banner dismissed")
            except:
                pass
            
            # Scroll to load more pins
            print("Scrolling to load more content...")
            for i in range(10):
                page.evaluate('window.scrollBy(0, 600)')
                time.sleep(1.2)
            print("Done scrolling")
            
            # Get HTML and parse
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all pin containers (data-test-id="pin")
            pin_containers = soup.find_all('div', attrs={'data-test-id': 'pin'})
            print(f"Found {len(pin_containers)} pin containers")
            
            # Extract pin data
            seen_ids = set()
            
            for i, pin in enumerate(pin_containers):
                pin_data = {}
                
                # Get image
                img = pin.find('img')
                if img:
                    src = img.get('src', '') or img.get('data-original-src', '') or img.get('data-src', '')
                    if 'pinimg' in src:
                        pin_data['image_url'] = src
                        pin_data['alt_text'] = img.get('alt', '') or img.get('aria-label', '') or ''
                
                # Get description/title
                # Pinterest typically has title in the img alt or in a separate element
                text_elements = pin.find_all(['div', 'span', 'p'], class_=lambda x: x and any(k in str(x).lower() for k in ['desc', 'title', 'text', 'content']))
                
                # Get the close button (indicates it's a pin)
                close_btn = pin.find_all('div', attrs={'data-test-id': 'close'})
                
                # Try to get the domain/ advertiser info (sometimes in the pin)
                domain = pin.get('data-domain', '') or pin.find(attrs={'data-test-id': 'pin-domain'})
                if domain:
                    pin_data['domain'] = str(domain)[:100]
                
                # Check if it has "Ad" label (data-test-id="promoted-pin-label")
                ad_label = pin.find(attrs={'data-test-id': 'promoted-pin-label'})
                if ad_label:
                    pin_data['is_promoted'] = True
                
                if pin_data.get('image_url') and pin_data.get('alt_text'):
                    # Create simple ID from image URL
                    img_id = pin_data['image_url'].split('/')[-1][:30]
                    if img_id not in seen_ids:
                        seen_ids.add(img_id)
                        ads.append(pin_data)
            
            print(f"\nExtracted {len(ads)} unique ad pins")
            
            # Show sample
            print("\n=== Sample Ads ===")
            for i, ad in enumerate(ads[:10]):
                print(f"\n[{i+1}]")
                print(f"  Image: {ad.get('image_url', '')[:80]}")
                print(f"  Alt text: {ad.get('alt_text', '')[:100]}")
                if ad.get('is_promoted'):
                    print(f"  PROMOTED")
            
            # Save to file
            output = {
                'query': query,
                'url': url,
                'total_pins_found': len(pin_containers),
                'unique_ads': len(ads),
                'ads': ads
            }
            
            with open('C:/home/node/.openclaw/workspace/skills/ad-radar/pinterest_ads.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            print(f"\nSaved to pinterest_ads.json")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    return ads

# Test with multiple queries
scrape_pinterest_ads('online advertising examples', max_pins=30)
scrape_pinterest_ads('digital ad campaign', max_pins=30)