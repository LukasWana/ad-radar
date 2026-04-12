import sys
import io
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
from playwright.sync_api import sync_playwright
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_advertiser_creatives_full(advertiser_name, region='CZ', max_creatives=5):
    """Get full ad data for an advertiser from Google Ad Transparency"""
    print(f"=== Google Ad Transparency: {advertiser_name} ({region}) ===")
    
    ads_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        try:
            # Step 1: Search for advertiser
            page.goto(f'https://adstransparency.google.com/?region={region}', timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(2)
            
            inp = page.query_selector('input[type="text"]')
            if not inp:
                print("No input found")
                return ads_data
            
            inp.click()
            inp.type(advertiser_name, delay=100)
            time.sleep(2)
            
            # Click verified option
            options = page.query_selector_all('[role="option"]')
            if not options:
                print("No options found")
                return ads_data
            
            target_opt = None
            for opt in options:
                text = opt.inner_text()
                if 'Ověřeno' in text and any(x in text for x in ['tisíc', 'tis.', 'reklam']):
                    target_opt = opt
                    break
            
            if not target_opt and len(options) > 1:
                target_opt = options[1]
            if not target_opt:
                target_opt = options[0]
            
            target_opt.click()
            time.sleep(4)
            
            # Get advertiser ID
            url = page.url
            if '/advertiser/' not in url:
                print(f"Did not navigate. URL: {url}")
                return ads_data
            
            advertiser_id = url.split('/advertiser/')[-1].split('?')[0]
            print(f"Advertiser: {advertiser_name} | ID: {advertiser_id}")
            
            # Collect creative IDs from current page
            creative_ids = []
            all_links = page.query_selector_all(f'a[href*="/advertiser/{advertiser_id}/creative/"]')
            for link in all_links:
                href = link.get_attribute('href')
                if href and '/creative/' in href:
                    cid = href.split('/creative/')[-1].split('?')[0]
                    if cid not in creative_ids:
                        creative_ids.append(cid)
            
            print(f"Found {len(creative_ids)} creatives, processing first {max_creatives}")
            
            # Process each creative - navigate directly
            for i, cid in enumerate(creative_ids[:max_creatives]):
                print(f"\n--- Creative {i+1}/{min(max_creatives, len(creative_ids))} ---")
                
                page.goto(f'https://adstransparency.google.com/advertiser/{advertiser_id}/creative/{cid}?region={region}', timeout=20000)
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(3)
                
                # Get inner text
                text = page.inner_text('body')
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 2]
                
                print(f"Text lines: {len(lines)}")
                
                # Extract ad data
                ad_entry = {
                    'advertiser_id': advertiser_id,
                    'advertiser_name': advertiser_name,
                    'creative_id': cid,
                    'region': region,
                }
                
                # Parse structured fields
                for line in lines:
                    if 'Oblast zobrazování' in line:
                        ad_entry['region_display'] = line.split('Oblast zobrazování:')[-1].strip()
                    if 'Poprvé zobrazeno' in line:
                        ad_entry['first_shown'] = line.split('Poprvé zobrazeno:')[-1].strip()
                    if 'Naposledy zobrazeno' in line:
                        ad_entry['last_shown'] = line.split('Naposledy zobrazeno:')[-1].strip()
                    if 'Téma (označené Googlem)' in line:
                        ad_entry['topic'] = line.split('Téma (označené Googlem):')[-1].strip()
                    if 'Formát:' in line:
                        ad_entry['format'] = line.split('Formát:')[-1].strip()
                    if 'Počet zobrazení' in line:
                        ad_entry['impressions'] = line.split('Počet zobrazení')[-1].strip()
                
                # Print all meaningful content
                for line in lines:
                    if len(line) < 120 and len(line) > 4:
                        print(f"  {line[:100]}")
                
                ads_data.append(ad_entry)
                
                # Navigate back to advertiser page
                page.goto(f'https://adstransparency.google.com/advertiser/{advertiser_id}?region={region}', timeout=20000)
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(1)
            
            print(f"\n=== SUMMARY ===")
            print(f"Advertiser: {advertiser_name}")
            print(f"Total creatives found: {len(creative_ids)}")
            print(f"Processed: {len(ads_data)}")
            for ad in ads_data:
                print(f"  - {ad.get('format', '?')} | {ad.get('first_shown', '?')} | {ad.get('topic', '?')[:40] if ad.get('topic') else '?'}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    return ads_data

# Test with Alza
results = get_advertiser_creatives_full('Alza', 'CZ', max_creatives=5)