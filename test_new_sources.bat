@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
python ad_radar_pipeline.py --dry-run --limit 30 --min-score 3
