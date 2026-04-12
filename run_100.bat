@echo off
cd /d C:\home\node\.openclaw\workspace\skills\ad-radar
python ad_radar_pipeline.py --limit 100 --min-score 5
