# MLB Data Pipeline

Daily-updating baseball data infrastructure for [Birdland Metrics](https://birdlandmetrics.com). Runs 5 Lambda functions in sequence via AWS Step Functions to compute ELO ratings, season projections, and Orioles dashboard data.

## Architecture

```
EventBridge (daily 6am ET, Mar–Oct)
  └─► Step Functions: mlb-daily-pipeline
       ├─► mlb-schedule-sync        — Fetch full season schedule from MLB Stats API → S3 CSV
       ├─► mlb-game-results         — Fetch daily Orioles game results → DynamoDB
       ├─► mlb-elo-compute          — Recompute ELO ratings (K=20, HFA=55, log MOV) → S3 + DynamoDB
       ├─► mlb-season-projections   — 10,000 Monte Carlo sims + standings/GB predictions → S3
       └─► mlb-orioles-dashboard    — Combine actuals + projections → DynamoDB + latest.json files
```

Each step runs sequentially with 2 automatic retries and exponential backoff.

## Shared Lambda Layer

All 5 functions share a single Lambda Layer (`mlb-pipeline-common`) containing:

- **Dependencies**: pandas, pyarrow, requests, MLB-StatsAPI
- **`mlb_common/config.py`** — All constants from env vars (season year, bucket names, ELO params, API URLs)
- **`mlb_common/team_codes.py`** — Single canonical team code mapping with league/division maps
- **`mlb_common/aws_helpers.py`** — S3 read/write (CSV, JSON, Parquet) + DynamoDB helpers
- **`mlb_common/elo.py`** — ELO math (expected score with HFA, margin of victory, rating update)

### Building the Layer

```bash
cd layers/mlb-pipeline-common
./build_layer.sh
aws lambda publish-layer-version \
  --layer-name mlb-pipeline-common \
  --content S3Bucket=mlb-elo-ratings-output,S3Key=lambda-layers/mlb-pipeline-common.zip \
  --compatible-runtimes python3.13
```

## AWS Resources

### Lambda Functions

| Function | Timeout | Memory | Purpose |
|---|---|---|---|
| `mlb-schedule-sync` | 10 min | 256 MB | Bulk schedule fetch from MLB Stats API → S3 CSV |
| `mlb-game-results` | 2 min | 128 MB | Daily Orioles game results → DynamoDB `Orioles-Games` |
| `mlb-elo-compute` | 10 min | 256 MB | ELO ratings → S3 CSV + DynamoDB + `elo-latest.json` |
| `mlb-season-projections` | 15 min | 512 MB | Monte Carlo sims → S3 Parquet/CSV + `standings-latest.json` + `projections-latest.json` |
| `mlb-orioles-dashboard` | 5 min | 256 MB | Orioles GB → DynamoDB + `games-back-latest.json` + `recent-games-latest.json` |

### S3 Buckets

| Bucket | Content |
|---|---|
| `mlb-schedule-{YEAR}` | Full season schedule CSV |
| `mlb-predictions-{YEAR}` | Daily projections CSVs, simulation parquet, `latest.json` files for Angular frontend |
| `mlb-elo-ratings-output` | ELO CSVs (historical + current season), end-of-season baselines, `elo-latest.json` |

### DynamoDB Tables

| Table | Key | Content |
|---|---|---|
| `Orioles-Games` | `id` (game_id) | Game results (scores, pitchers, venue) |
| `Orioles-Games_Back` | `id` (mlb-day-{date}) | Daily wildcard/division GB + projections |
| `mlb-elo-team-ratings` | `team` | Current ELO per team |

### IAM Roles

| Role | Used By |
|---|---|
| `mlb-pipeline-lambda-role` | All 5 Lambda functions (S3 Full + DynamoDB Full + CloudWatch Logs) |
| `mlb-pipeline-stepfunctions-role` | Step Functions state machine (invoke 5 Lambdas) |
| `mlb-pipeline-scheduler-role` | EventBridge Scheduler (start Step Functions execution) |

### Step Functions

- **State Machine**: `mlb-daily-pipeline`
- **ARN**: `arn:aws:states:us-east-1:953354210097:stateMachine:mlb-daily-pipeline`

### EventBridge Schedule

- **Schedule**: `mlb-daily-pipeline` — `cron(0 10 * 3-10 ? *)` (6am ET, Mar–Oct)
- **Status**: DISABLED (enable when season starts)

## ELO Formula

Canonical formula (from `mlb-daily-elo-compute`):

- **K-factor**: 20
- **Home Field Advantage**: 55 ELO points
- **Margin of Victory**: `log(|score_diff| + 1) * (2.2 / (0.001 * |elo_diff| + 2.2))`
- **Win Probability**: `1 / (1 + 10^((elo_b - (elo_a + HFA)) / 400))`

## Angular Frontend Integration

Each pipeline run produces `latest.json` files in S3 with CORS enabled for the Angular frontend:

| File | Bucket | Content |
|---|---|---|
| `elo-latest.json` | `mlb-elo-ratings-output` | All 30 teams sorted by ELO |
| `standings-latest.json` | `mlb-predictions-{YEAR}` | Projected AL standings |
| `projections-latest.json` | `mlb-predictions-{YEAR}` | Full 30-team projection summary |
| `games-back-latest.json` | `mlb-predictions-{YEAR}` | Orioles wildcard/division GB + projections |
| `recent-games-latest.json` | `mlb-predictions-{YEAR}` | Last 10 Orioles game results |

## Season Transition

To switch to a new season:

1. Create end-of-season ELO baseline: extract final ratings from `elo-ratings-{YEAR}.csv` → `elo_rating_end_of_{YEAR}.csv`
2. Create new S3 buckets: `mlb-schedule-{YEAR+1}`, `mlb-predictions-{YEAR+1}`
3. Update `SEASON_YEAR` env var on all 5 Lambdas
4. Enable the EventBridge schedule

## Manual Execution

```bash
# Trigger a single pipeline run
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:953354210097:stateMachine:mlb-daily-pipeline

# Enable the daily schedule for the season
aws scheduler update-schedule \
  --name mlb-daily-pipeline \
  --state ENABLED \
  --schedule-expression "cron(0 10 * 3-10 ? *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{
    "Arn": "arn:aws:states:us-east-1:953354210097:stateMachine:mlb-daily-pipeline",
    "RoleArn": "arn:aws:iam::953354210097:role/mlb-pipeline-scheduler-role",
    "Input": "{}"
  }'
```

## Legacy Pipeline

The old Lambda functions and EventBridge schedules from the 2025 season are still intact. Delete them once the new pipeline is verified:

- `mlb-stats-api-game-data`, `mlb-daily-elo-compute`, `mlb-elo-ratings-calculator`, `mlb-season-simulations`, `mlb-stats-api-games-back-wc`, `mlb-daily-orioles-games-back`, `mlb-remaining-2025-schedule`, `mlb-stats-api-logos`
