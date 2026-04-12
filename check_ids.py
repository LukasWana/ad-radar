import sqlite3, hashlib
db = sqlite3.connect('C:/home/node/.openclaw/workspace/skills/ad-radar/ad_radar.db')
db.row_factory = sqlite3.Row
row = db.execute("SELECT id, url, title, brand FROM campaigns WHERE is_delivered = 1 LIMIT 1").fetchone()
print('DB row:')
print(f'  ID: {row[0]}')
print(f'  URL: {row[1]}')
print(f'  Title: {row[2][:60]}')
print(f'  Brand: {row[3]}')
cid = hashlib.md5(f"{row[1]}|{row[3]}|{row[2]}".encode()).hexdigest()[:16]
print(f'  Recalculated ID: {cid}')
print()
print('Same?', cid == row[0])
