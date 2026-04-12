# Ad Radar — Complete Monitoring Pipeline

## Overview
Automated daily monitoring of the best advertising across TV, Print, Online, and Brand categories. Uses layered scraping with SQLite-backed deduplication.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      AD RADAR PIPELINE                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   DISCOVER   │───▶│   SCRAPE     │───▶│   ANALYZE    │   │
│  │   (5 sources)│    │ (web_scraper)│    │  & Score     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│          │                                       │            │
│          ▼                                       ▼            │
│  ┌──────────────┐                        ┌──────────────┐   │
│  │   URL Pool   │                        │  CANDIDATE   │   │
│  │  (20/source) │                        │    POOL      │   │
│  └──────────────┘                        └──────────────┘   │
│                                                │             │
│          ┌─────────────────────────────────────┘             │
│          ▼                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   HISTORY    │◀───│  DEDUP &     │───▶│  DASHBOARD   │   │
│  │   (SQLite)   │    │   RANK       │    │   GENERATE   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│          ▲                                       │             │
│          │                                       ▼             │
│          │                              ┌──────────────┐       │
│          └──────────────────────────────│   DELIVER    │       │
│                                         │  (Telegram)  │       │
│                                         └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

## Components

### ad_radar_pipeline.py — Main Pipeline
- Source discovery (5 curated sources)
- Batch scraping with rate limiting
- AI-powered scoring (rules-based fallback)
- Category classification
- Deduplication via SHA256(url+brand+title)
- Dashboard generation

### ad_db.py — Database Layer
- SQLite persistence
- Campaign history tracking
- Dedup logging
- Source monitoring
- Stats aggregation

### web_scraper.py — Scraping Layer
- httpx + BeautifulSoup
- Multiple extract modes
- Graceful degradation

## Sources Monitored

| Source | URL | Priority |
|--------|-----|----------|
| Ads of the World | adsoftheworld.com | 3 |
| Campaign Brief | campaignbrief.com | 2 |
| Famous Campaigns | famouscampaigns.com | 3 |
| Creative Review | creativereview.co.uk | 2 |
| The Drum | thedrum.com | 2 |

## Categories

- **TV/Cinema** — Best commercials, viral video ads
- **Print/OOH** — Billboards, outdoor, magazine ads
- **Online/Digital** — Social media, display, pre-roll
- **Brand/Logo** — Logo redesigns, brand identity
- **Grand Prix** — Best of the best overall

## Usage

```bash
# Run full pipeline
python ad_radar_pipeline.py

# Dry run (no DB changes)
python ad_radar_pipeline.py --dry-run

# Limit processing
python ad_radar_pipeline.py --limit 10

# With custom config
python ad_radar_pipeline.py --config config.json
```

## Config Options

```json
{
  "max_per_category": 3,
  "min_score": 5,
  "fresh_days": 7,
  "max_candidates": 50,
  "rate_limit_delay": 0.5,
  "enable_ai_scoring": false
}
```

## Database Schema

```sql
-- campaigns: main campaign storage
-- sources: tracked source metadata  
-- dashboard_history: generated dashboards
-- dedup_log: deduplication events

-- Key queries:
SELECT * FROM campaigns WHERE is_delivered = 0 ORDER BY score DESC;
SELECT COUNT(*) FROM campaigns GROUP BY category;
SELECT * FROM dashboard_history ORDER BY generated_at DESC LIMIT 7;
```

## Cron Integration

Schedule: Daily at 08:00 (Europe/Prague)
```bash
openclaw cron add \
  --name "Ad Radar Daily" \
  --cron "0 8 * * *" \
  --tz "Europe/Prague" \
  --session isolated \
  --message "Run Ad Radar pipeline: python /path/to/ad_radar_pipeline.py" \
  --announce --channel telegram --to 5370808247
```

## Scoring Algorithm

Base score: 5
- +2: Contains "award", "Grand Prix", "Gold"
- +1: "viral", "trending", "most shared"
- +1: Celebrity/brand mention
- +1: Detailed description (>500 chars)
- +1: Known agency
- -1: Sponsored/advertisement context

Final score: clamped 0-10

## Output Format

Markdown dashboard with:
- Grand Prix section (top 3)
- Category sections (top 3 each)
- Source attribution
- Links to campaigns