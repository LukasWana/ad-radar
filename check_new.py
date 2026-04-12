import sys
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/skills/ad-radar')
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/scripts')
sys.path.insert(0, 'C:/home/node/.openclaw/workspace/web-scraper')
from ad_radar_pipeline import AdRadarPipeline, generate_campaign_id
import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'C:/home/node/.openclaw/workspace/skills/ad-radar/ad_radar.db'
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row

# Show first 10 delivered campaigns with their IDs
print('First 10 delivered campaigns:')
rows = db.execute('SELECT id, url, title, delivered_at FROM campaigns WHERE is_delivered = 1 ORDER BY delivered_at DESC LIMIT 10').fetchall()
for r in rows:
    print(f'  ID={r[0]}, URL={r[1]}')
    print(f'    Title: {r[2][:50]}')
    print(f'    Delivered: {r[3]}')

# Now show all distinct URLs from campaigns table
print('\n\nAll URLs in campaigns table (first 20):')
rows = db.execute('SELECT DISTINCT url FROM campaigns LIMIT 20').fetchall()
for r in rows:
    print(f'  {r[0]}')

db.close()
