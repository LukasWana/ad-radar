import json

with open('C:/home/node/.openclaw/workspace/skills/ad-radar/pinterest_ads.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

ads = d.get('ads', [])
print(f'Pinterest ads: {len(ads)}')
for a in ads[:5]:
    desc = a.get('description', '') or a.get('alt_text', '')
    print(f'  - {desc[:80]}')