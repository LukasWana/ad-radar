@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
python discover_ads.py --query "email marketing newsletter design" --max 15 --output html
