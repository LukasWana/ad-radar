import sqlite3
db = sqlite3.connect('C:/home/node/.openclaw/workspace/skills/ad-radar/ad_radar.db')
db.execute('UPDATE campaigns SET is_delivered = 0, delivered_at = NULL')
db.commit()
print('Undelivered all campaigns')
