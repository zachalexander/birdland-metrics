# Plan: Retrosheet Historical Player Stats Pipeline

Build a pipeline that downloads Retrosheet event files, processes them with locally-installed Chadwick CLI tools, and uploads structured player stats to S3 — enabling year-over-year Orioles player performance analysis on the Angular frontend.

## Architecture Overview

```
[1. Local Bootstrap Script]
    Download Retrosheet event files (2015–2025)
    → cwdaily → per-game batting/pitching CSV
    → cwgame  → game-level summaries
    → Merge + filter Orioles players
    → Upload CSVs + player-stats-latest.json to S3

[2. In-Season Lambda] (optional, Phase 2)
    Triggered by Step Functions after mlb-orioles-dashboard
    → MLB Stats API for current-season daily stats
    → Append to S3
    → Rewrite player-stats-latest.json

[3. Angular Frontend]
    MlbDataService → fetch player-stats-latest.json
    → Player stats page with d3 visualizations
```

## Data Model

### Per-Game Batting (from `cwdaily`)

| Column | Type | Description |
|--------|------|-------------|
| player_id | str | Retrosheet ID (e.g. `hendd001`) |
| name | str | Display name |
| team | str | 3-letter code (BAL) |
| date | str | YYYY-MM-DD |
| season | int | Year |
| g | int | Games (1) |
| pa | int | Plate appearances |
| ab | int | At bats |
| r | int | Runs |
| h | int | Hits |
| 2b | int | Doubles |
| 3b | int | Triples |
| hr | int | Home runs |
| rbi | int | RBI |
| bb | int | Walks |
| so | int | Strikeouts |
| hbp | int | Hit by pitch |
| sf | int | Sac flies |
| sb | int | Stolen bases |
| cs | int | Caught stealing |

### Per-Game Pitching (from `cwdaily`)

| Column | Type | Description |
|--------|------|-------------|
| player_id | str | Retrosheet ID |
| name | str | Display name |
| team | str | 3-letter code |
| date | str | YYYY-MM-DD |
| season | int | Year |
| ip_outs | int | Outs recorded (IP × 3) |
| h | int | Hits allowed |
| r | int | Runs allowed |
| er | int | Earned runs |
| bb | int | Walks |
| so | int | Strikeouts |
| hr | int | Home runs allowed |
| bf | int | Batters faced |
| w | int | Wins |
| l | int | Losses |
| sv | int | Saves |

### Aggregated Season Stats (computed from per-game)

Batting: G, PA, AB, R, H, 2B, 3B, HR, RBI, BB, SO, HBP, SF, SB, CS + calculated AVG, OBP, SLG, OPS, wOBA
Pitching: G, GS, IP, H, R, ER, BB, SO, HR, BF, W, L, SV + calculated ERA, WHIP, K/9, BB/9, FIP

### Player ID Map

| Column | Type | Description |
|--------|------|-------------|
| retro_id | str | Retrosheet ID |
| mlb_id | int | MLB Stats API ID |
| name | str | Full display name |

This allows joining Retrosheet historical data with current-season Stats API data.

## S3 Storage

**Bucket:** `mlb-player-stats` (new)

```
batting-daily/
  batting_daily_2015.csv
  batting_daily_2016.csv
  ...
  batting_daily_2025.csv

pitching-daily/
  pitching_daily_2015.csv
  ...

season-totals/
  batting_season_2015.csv
  ...
  pitching_season_2015.csv
  ...

player-id-map.json
player-stats-latest.json       ← Angular frontend reads this
batting-leaders-latest.json    ← Precomputed leaderboards
pitching-leaders-latest.json
```

### `player-stats-latest.json` shape

```json
{
  "updated": "2026-06-15T02:30:00",
  "season": 2026,
  "batting": [
    {
      "player_id": "hendd001",
      "mlb_id": 669742,
      "name": "Gunnar Henderson",
      "team": "BAL",
      "g": 65, "pa": 290, "ab": 255, "h": 78,
      "2b": 18, "3b": 2, "hr": 15, "rbi": 45,
      "bb": 30, "so": 58, "sb": 12,
      "avg": 0.306, "obp": 0.379, "slg": 0.569, "ops": 0.948
    }
  ],
  "pitching": [
    {
      "player_id": "burnd001",
      "mlb_id": 669203,
      "name": "Corbin Burnes",
      "team": "BAL",
      "g": 17, "gs": 17, "ip": 108.1,
      "h": 88, "er": 34, "bb": 25, "so": 112, "hr": 10,
      "w": 9, "l": 4,
      "era": 2.82, "whip": 1.04, "k_per_9": 9.31, "fip": 3.12
    }
  ]
}
```

## Files to Create / Modify

| # | File | Action |
|---|------|--------|
| 1 | `data-pipelines/scripts/bootstrap-retrosheet.py` | **New** — local script: download, process, upload |
| 2 | `data-pipelines/layers/mlb-pipeline-common/python/mlb_common/config.py` | Add `PLAYER_STATS_BUCKET` |
| 3 | `data-pipelines/layers/mlb-pipeline-common/python/mlb_common/stats.py` | **New** — stat calculation helpers (AVG, OBP, SLG, OPS, wOBA, ERA, FIP, WHIP) |
| 4 | `src/app/shared/models/mlb.models.ts` | Add `PlayerBatting`, `PlayerPitching`, `PlayerStatsResponse` interfaces |
| 5 | `src/app/core/services/mlb-data.service.ts` | Add `getPlayerStats()` method |
| 6 | `src/environments/environment.ts` | Add `s3.playerStats` URL |
| 7 | `src/environments/environment.prod.ts` | Add `s3.playerStats` URL |

## Step-by-Step

### Step 1: Shared stat helpers (`stats.py`)

Add to the `mlb_common` layer:

```python
def batting_avg(h, ab): ...
def obp(h, bb, hbp, ab, sf): ...
def slg(h, _2b, _3b, hr, ab): ...
def ops(obp_val, slg_val): ...
def era(er, ip_outs): ...
def whip(h, bb, ip_outs): ...
def fip(hr, bb, hbp, so, ip_outs, lg_fip_constant): ...
def k_per_9(so, ip_outs): ...
def bb_per_9(bb, ip_outs): ...
def ip_from_outs(ip_outs): ...   # 10 outs → 3.1 IP
```

### Step 2: Config update

Add to `config.py`:
```python
PLAYER_STATS_BUCKET = os.getenv('PLAYER_STATS_BUCKET', 'mlb-player-stats')
```

### Step 3: Bootstrap script (`bootstrap-retrosheet.py`)

This runs locally (not on Lambda) since it needs Chadwick CLI tools installed.

```
Usage: python bootstrap-retrosheet.py [--years 2015-2025] [--team BAL] [--upload]
```

Pipeline:
1. Download Retrosheet event files from `https://www.retrosheet.org/events/{year}eve.zip`
2. Unzip to temp directory
3. Run `cwdaily -y {year} {year}*.EV*` to get per-game player stats
4. Parse CSV output, filter to `--team` (default BAL)
5. Split into batting + pitching DataFrames
6. Compute season aggregates with calculated stats (using `stats.py`)
7. Build player ID map: parse Retrosheet `.ROS` roster files for name → retro_id, cross-reference with MLB Stats API `https://statsapi.mlb.com/api/v1/people?personIds=...` for mlb_id
8. Upload to S3 (if `--upload` flag)

### Step 4: TypeScript models

Add to `mlb.models.ts`:

```typescript
export interface PlayerBatting {
  player_id: string;
  mlb_id?: number;
  name: string;
  team: string;
  g: number; pa: number; ab: number; h: number;
  doubles: number; triples: number; hr: number; rbi: number;
  bb: number; so: number; sb: number; cs: number;
  avg: number; obp: number; slg: number; ops: number;
}

export interface PlayerPitching {
  player_id: string;
  mlb_id?: number;
  name: string;
  team: string;
  g: number; gs: number; ip: number;
  h: number; er: number; bb: number; so: number; hr: number;
  w: number; l: number; sv: number;
  era: number; whip: number; k_per_9: number; fip: number;
}

export interface PlayerStatsResponse {
  updated: string;
  season: number;
  batting: PlayerBatting[];
  pitching: PlayerPitching[];
}
```

### Step 5: MlbDataService update

```typescript
async getPlayerStats(season?: number): Promise<PlayerStatsResponse> {
  const url = `${this.statsBase}/player-stats-latest.json`;
  return firstValueFrom(this.http.get<PlayerStatsResponse>(url));
}
```

### Step 6: Environment config

```typescript
s3: {
  eloRatings: '...',
  predictions: '...',
  playerStats: 'https://mlb-player-stats.s3.amazonaws.com',   // new
}
```

## Retrosheet Data Notes

- Event files available: 1919–2024 (2025 available after season ends, ~Dec 2025)
- For 2025/2026 current-season data: use MLB Stats API (separate Lambda, Phase 2)
- Retrosheet requires attribution: "The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at www.retrosheet.org."
- `cwdaily` output columns map cleanly to standard baseball stat categories
- Roster files (`.ROS`) contain: `retro_id, last_name, first_name, bats, throws, team, position`
- Chadwick tools v0.10.0 installed at `/usr/local/bin/` (`cwdaily`, `cwgame`, `cwevent`)
- Chadwick source at `/Users/zdalexander/Desktop/chadwick/`

## Verification

1. Run `python bootstrap-retrosheet.py --years 2024 --team BAL` locally → produces CSV files
2. Inspect output CSVs: BAL players only, correct stat columns, reasonable values
3. Run with `--upload` → files appear in S3 bucket
4. `ng build` compiles with new TypeScript models
5. Frontend can fetch `player-stats-latest.json` from S3

## Phase 2 (Future)

- Lambda function `mlb-player-stats-sync` for in-season daily updates via MLB Stats API
- Add to Step Functions after `OriolesDashboard`
- Player stats page with d3 visualizations (rolling averages, season trends, YoY comparison)
- Player comparison tool
