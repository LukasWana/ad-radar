@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
python discover_ads.py --query "sportovni boty" --max 10 --output json
