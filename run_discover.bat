@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
python discover_ads.py --query "posilani reklamnich emailu" --max 15 --output html
