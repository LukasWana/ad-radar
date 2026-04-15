# AD RADAR — Daily Advertising Banners Dashboard

## Purpose
Daily monitoring of the best online advertising banners. Collects 4 fresh banners every day and sends a morning summary to Telegram at 08:00.

## Banner Sources
| Source | URL | Focus |
|--------|-----|-------|
| Ads of the World | adsoftheworld.com | Global ads, banners |
| Adsumz | adsumz.com | Award-winning campaigns |
| Bannerflow | bannerflow.com | Display advertising |
| SmartyAds | smartyads.com | Ad design inspiration |
| The Drum | thedrum.com | Creative advertising |
| Campaign Brief | campaignbrief.com | Industry news |
| Adspert | adspert.me | Advertising optimization |

## Architecture
```
┌─────────────────────────────────────────────────┐
│              BANNER PIPELINE                     │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐           │
│  │   SOURCES    │───▶│   SCRAPE     │           │
│  │  (7 sites)   │    │  banners     │           │
│  └──────────────┘    └──────────────┘           │
│          │                    │                   │
│          ▼                    ▼                   │
│  ┌──────────────┐    ┌──────────────┐           │
│  │  URL Pool    │    │   DAILY      │           │
│  │  10/source   │    │   4 BANNERS  │           │
│  └──────────────┘    └──────────────┘           │
│                              │                   │
│                              ▼                   │
│                    ┌──────────────┐              │
│                    │  DASHBOARD   │              │
│                    │  + TELEGRAM  │              │
│                    └──────────────┘              │
└─────────────────────────────────────────────────┘
```

## Files
- `banners_dashboard.html` — Banner showcase dashboard
- `banner_pipeline.py` — Daily banner collection script
- `daily_banner.json` — Latest 4 banners with metadata

## Usage
```bash
# Run daily banner collection
python banner_pipeline.py

# Open dashboard
start skills/ad-radar/banners_dashboard.html
```

## Cron Setup
Daily at 08:00 (Europe/Prague):
```bash
openclaw cron add \
  --name "Ad Radar Banners" \
  --cron "0 8 * * *" \
  --tz "Europe/Prague" \
  --session isolated \
  --message "python /path/to/banner_pipeline.py" \
  --announce --channel telegram --to 5370808247
```

## Banner JSON Format
```json
{
  "date": "2026-04-14",
  "banners": [
    {
      "id": "banner_001",
      "title": "Campaign Title",
      "brand": "Brand Name",
      "source": "adsoftheworld.com",
      "imageUrl": "https://...",
      "targetUrl": "https://...",
      "dimensions": "300x250",
      "format": "display"
    }
  ]
}
```
