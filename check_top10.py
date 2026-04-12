import sqlite3

db = sqlite3.connect('C:/home/node/.openclaw/workspace/skills/ad-radar/ad_radar.db')
db.row_factory = sqlite3.Row

print("=== Sources ===")
rows = db.execute('SELECT source, COUNT(*) as c FROM campaigns GROUP BY source').fetchall()
for r in rows:
    print(f'{r["source"]}: {r["c"]}')

print()
print("=== TOP 10 ===")
rows = db.execute('SELECT id, title, brand, source, score, url FROM campaigns ORDER BY score DESC LIMIT 10').fetchall()
for r in rows:
    print(f'{r["source"]}: [{r["score"]}] {r["brand"]} - {r["title"]}')

db.close()