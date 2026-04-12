import sqlite3
db = sqlite3.connect('C:/home/node/.openclaw/workspace/skills/ad-radar/ad_radar.db')
db.row_factory = sqlite3.Row
r = db.execute("SELECT id, url, brand, title FROM campaigns WHERE is_delivered = 1 LIMIT 1").fetchone()
print('DB id col:', r['id'])
print('URL col:', r['url'])
print('Brand:', repr(r['brand'][:50]))
print('Title:', repr(r['title'][:50]))

import hashlib
new_cid = hashlib.md5(f"{r['url']}|{r['brand']}|{r['title']}".encode()).hexdigest()[:16]
print('New calc ID:', new_cid)
print('Match?', new_cid == r['id'])
