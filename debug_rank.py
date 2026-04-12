import sys, json
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/skills/ad-radar')
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/web-scraper')
from ad_radar_pipeline import AdRadarPipeline, generate_campaign_id

pipeline = AdRadarPipeline(max_per_category=3, min_score=0, limit=5)
urls = [
    ('ads_of_the_world', 'https://www.adsoftheworld.com/campaigns/helmet-has-always-been-a-good-idea-1676'),
    ('ads_of_the_world', 'https://www.adsoftheworld.com/campaigns/nothing-stops-women-s-rugby'),
]
campaigns = pipeline.scrape_and_analyze(urls)
print(f'Campaigns scraped: {len(campaigns)}')
for c in campaigns:
    cid = generate_campaign_id(c.url, c.brand, c.title)
    print(f'  - url={c.url}')
    print(f'    title={repr(c.title[:40])}')
    print(f'    brand={repr(c.brand[:30])}')
    print(f'    score={c.score}, cat={c.category}, id={cid}')

# Manually check deduplication logic
from datetime import datetime, timedelta
cutoff = (datetime.now() - timedelta(days=30)).isoformat()
seen_ids = {row["id"] for row in pipeline.db.execute(
    "SELECT id FROM campaigns WHERE is_delivered = 1 AND delivered_at >= ?",
    (cutoff,)
).fetchall()}
print(f'\nseen_ids count: {len(seen_ids)}')
for cid in seen_ids:
    print(f'  seen: {cid}')

print(f'\nChecking each campaign:')
for c in campaigns:
    cid = generate_campaign_id(c.url, c.brand, c.title)
    in_seen = cid in seen_ids
    meets_min = c.score >= pipeline.min_score
    print(f'  {cid}: in_seen={in_seen}, meets_min={meets_min}')
    if in_seen:
        print(f'    -> SKIPPED (duplicate)')

ranked = pipeline.deduplicate_and_rank(campaigns)
print(f'\nRanked: {json.dumps({k: len(v) for k,v in ranked.items()}, indent=2)}')
pipeline.scraper.close()
pipeline.db.close()
