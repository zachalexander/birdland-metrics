# Birdland Metrics: AWS & Repository Audit

**Date:** February 16, 2026
**Account:** 953354210097 (IAM user: Zach)
**Region:** us-east-1

---

## 1. AWS Services — Active (Birdland Metrics)

These resources power the live site at **birdlandmetrics.com**.

### App Runner

| Service | Status | URL |
|---------|--------|-----|
| birdland-metrics | RUNNING | gmzjz8m6pc.us-east-1.awsapprunner.com |

**Purpose:** Hosts the Angular 21 SSR application (Docker, Node 20, port 4000). Auto-deploys from GitHub on push to `main`.

### S3 Buckets — Active Pipeline

| Bucket | Objects | Size | Purpose |
|--------|---------|------|---------|
| `mlb-elo-ratings-output` | 12 | 14.3 MB | ELO ratings history, elo-latest.json, FIP data, ballpark info, injury data |
| `mlb-predictions-2026` | 15 | 316 KB | Standings, projections, playoff odds, recent games (all `-latest.json` files the frontend reads) |
| `mlb-schedule-2026` | 1 | 133 KB | Full 2026 season schedule CSV |
| `mlb-player-stats-retrosheet` | 46 | 1.8 MB | Per-game + season batting/pitching CSVs (2015-2025), player-stats-latest.json |
| `mlb-logos-for-visuals` | 32 | 38 KB | Team logo PNGs for visualizations |
| `mlb-pipeline-artifacts` | 6 | 161 MB | Lambda layer zip (mlb-pipeline-common.zip) + archived old ELO formulas |

**Key files the Angular frontend reads:**
- `mlb-elo-ratings-output/elo-latest.json` — Current ELO ratings
- `mlb-elo-ratings-output/elo-ratings-full-history.csv` — ELO trend chart data (14.8 MB)
- `mlb-predictions-2026/playoff-odds-latest.json` — Playoff odds
- `mlb-predictions-2026/projections-latest.json` — Win projections
- `mlb-predictions-2026/standings-latest.json` — Standings
- `mlb-predictions-2026/recent-games-latest.json` — Recent Orioles games
- `mlb-player-stats-retrosheet/player-stats-latest.json` — Player stats (new)

### Lambda Functions — Active Pipeline

| Function | Runtime | Memory | Last Modified | Purpose |
|----------|---------|--------|---------------|---------|
| `mlb-schedule-sync` | python3.13 | 256 MB | Feb 7, 2026 | Fetches full season schedule from MLB Stats API -> S3 CSV |
| `mlb-elo-compute` | python3.13 | 256 MB | Feb 10, 2026 | Updates ELO ratings from game results (K=20, HFA=55, FIP-adjusted) |
| `mlb-game-results` | python3.13 | 128 MB | Feb 7, 2026 | Fetches daily Orioles game results -> DynamoDB |
| `mlb-season-projections` | python3.13 | 512 MB | Feb 10, 2026 | 10,000 Monte Carlo season sims -> standings/projections/playoff odds JSONs |
| `mlb-orioles-dashboard` | python3.13 | 256 MB | Feb 10, 2026 | Compiles Orioles dashboard: games back, recent games -> S3 JSONs |
| `mlb-preseason-adjustment` | python3.13 | 256 MB | Feb 10, 2026 | WAR-based preseason ELO adjustment (runs weekly in March via EventBridge) |

### Lambda Layer

| Layer | Version | Purpose |
|-------|---------|---------|
| `mlb-pipeline-common` | v2 | Shared Python: config, ELO math, FIP, AWS helpers, team codes, stats |
| `mlb-statsapi` | v4 | MLB Stats API Python wrapper |

### Step Functions

| State Machine | Purpose |
|---------------|---------|
| `mlb-daily-pipeline` | Orchestrates daily in-season run: schedule-sync -> elo-compute -> game-results -> season-projections -> orioles-dashboard |

### EventBridge Rules

| Rule | Schedule | State | Purpose |
|------|----------|-------|---------|
| `mlb-preseason-adjustment` | `cron(0 12 ? 3 MON *)` | ENABLED | Triggers preseason ELO adjustment every Monday in March at noon UTC |

### DynamoDB Tables — Active

| Table | Items | Size | Purpose |
|-------|-------|------|---------|
| `mlb-elo-team-ratings` | 30 | 2.3 KB | Current ELO rating for all 30 MLB teams |
| `Orioles-Games` | 162 | 47 KB | 2026 Orioles game results (scores, pitchers, venue) |
| `Orioles-Games_Back` | 186 | 16.5 KB | Games-back projections history |

### CloudWatch Log Groups — Active Pipeline

| Log Group | Stored |
|-----------|--------|
| `/aws/lambda/mlb-elo-compute` | 4 KB |
| `/aws/lambda/mlb-game-results` | 3 KB |
| `/aws/lambda/mlb-orioles-dashboard` | 6.5 KB |
| `/aws/lambda/mlb-preseason-adjustment` | 7 KB |
| `/aws/lambda/mlb-schedule-sync` | 3 KB |
| `/aws/lambda/mlb-season-projections` | 8.5 KB |
| `/aws/apprunner/birdland-metrics/.../application` | 541 KB |
| `/aws/apprunner/birdland-metrics/.../service` | 234 KB |

### IAM Roles — Active Pipeline

| Role | Purpose |
|------|---------|
| `mlb-pipeline-lambda-role` | Execution role for all 6 Lambda functions |
| `mlb-pipeline-stepfunctions-role` | Step Functions execution role |
| `mlb-pipeline-scheduler-role` | EventBridge scheduler role |

---

## 2. AWS Resources — Prior Season (Can Archive)

These were used for the 2025 season and are no longer actively written to.

### S3 Buckets

| Bucket | Objects | Size | Purpose | Recommendation |
|--------|---------|------|---------|----------------|
| `mlb-predictions-2025` | 5 | 235 KB | 2025 season predictions (ended) | **Delete** or archive — superseded by 2026 bucket |
| `mlb-schedule-2025` | 1 | 223 KB | 2025 full schedule CSV | **Delete** — season complete |

### CloudWatch Log Groups — Old Lambda Names

These are logs from older Lambda function names that were replaced by the current pipeline:

| Log Group | Stored | Recommendation |
|-----------|--------|----------------|
| `/aws/lambda/mlb-daily-elo-compute` | 64 KB | **Delete** — replaced by `mlb-elo-compute` |
| `/aws/lambda/mlb-daily-orioles-games-back` | 53 KB | **Delete** — replaced by `mlb-orioles-dashboard` |
| `/aws/lambda/mlb-remaining-2025-schedule` | 153 KB | **Delete** — 2025 schedule function |
| `/aws/lambda/mlb-season-simulations` | 110 KB | **Delete** — replaced by `mlb-season-projections` |
| `/aws/lambda/mlb-elo-ratings-calculator` | 1.3 MB | **Delete** — old ELO calculator |
| `/aws/lambda/mlb-elo-ratings-fivethirtyeight` | 36 KB | **Delete** — old 538-based model |
| `/aws/lambda/mlb-elo-ratings-kaggle` | 10 KB | **Delete** — old Kaggle approach |
| `/aws/lambda/mlb-stats-api-game-data` | 268 KB | **Delete** — old stats API Lambda |
| `/aws/lambda/mlb-stats-api-games-back-wc` | 149 KB | **Delete** — old games-back Lambda |
| `/aws/lambda/mlb-stats-api-logos` | 4 KB | **Delete** — logo upload (one-time) |
| `/aws/lambda/mlb-statsapi` | 84 KB | **Delete** — old stats wrapper |
| `/aws/lambda/mlbstatsapi-playevents` | 25 KB | **Delete** — old play events |
| `/aws/lambda/mlbstatsapi-standings` | 212 KB | **Delete** — old standings Lambda |
| `/aws/lambda/mlbstatsapinodeaddgame-dev` | 11 KB | **Delete** — old Node.js version |
| `/aws/lambda/mlbstatsapinode-dev` | 156 MB | **Delete** — massive old Node Lambda log |
| `/aws/lambda/mlboriolesaddgame-dev` | 658 KB | **Delete** — old game adder |
| `/aws/lambda/mlbstatsapilambda-dev` | 4 KB | **Delete** — old dev Lambda |
| `/aws/lambda/mlb-stats` | 577 B | **Delete** — early prototype |
| `/aws/lambda/triggerAtBatAddition` | 4.5 KB | **Delete** — old at-bat trigger |

### IAM Roles — Old/Orphaned MLB Roles

| Role | Created | Recommendation |
|------|---------|----------------|
| `mlb-daily-elo-compute-role-gcg0eg7b` | Jul 2025 | **Delete** — old function |
| `mlb-daily-orioles-games-back-role-spmod0wg` | Jul 2025 | **Delete** — old function |
| `mlb-elo-ratings-calculator-role-7mai5t6z` | Jun 2025 | **Delete** — old function |
| `mlb-elo-ratings-fivethirtyeight-role-3ihoa48y` | Jun 2025 | **Delete** — old function |
| `mlb-elo-ratings-fivethirtyeight-role-8fbne644` | Jun 2025 | **Delete** — duplicate |
| `mlb-elo-ratings-fivethirtyeight-role-aabim8p0` | Jun 2025 | **Delete** — duplicate |
| `mlb-elo-ratings-fivethirtyeight-role-gjvu511j` | Jun 2025 | **Delete** — duplicate |
| `mlb-elo-ratings-kaggle-role-pcsqmb26` | Jun 2025 | **Delete** — old function |
| `mlb-remaining-2025-schedule-role-ldbx8zrv` | Jul 2025 | **Delete** — 2025 schedule |
| `mlb-season-simulations-role-hzcg69we` | Jun 2025 | **Delete** — old function |
| `mlb-stats-api-game-data-role-qpexw4rv` | Apr 2025 | **Delete** — old function |
| `mlb-stats-api-games-back-wc-role-3gyqqsmy` | May 2025 | **Delete** — old function |
| `mlb-stats-api-logos-role-ij1efqqr` | Jun 2025 | **Delete** — old function |
| `mlb-stats-role-c3ca6c05` | Sep 2023 | **Delete** — very old |
| `mlb-statsapi-role-5697pnsv` | Sep 2023 | **Delete** — very old |
| `mlb-statsapi-role-autt5wg8` | Sep 2023 | **Delete** — very old |
| `mlb-statsapi-role-j9pxxxkc` | Sep 2023 | **Delete** — very old |
| `mlbstatsapi-playevents-role-58rcxoxi` | Feb 2024 | **Delete** — old function |
| `mlbstatsapi-playevents-role-oo8fey3o` | Feb 2024 | **Delete** — duplicate |
| `mlbstatsapi-standings-role-eqxvj652` | Apr 2024 | **Delete** — old function |

### Lambda Layer — Duplicate

| Layer | Version | Recommendation |
|-------|---------|----------------|
| `mlb_statsapi_layer` | v2 | **Delete** — duplicate of `mlb-statsapi` (note underscore naming) |

---

## 3. AWS Resources — Non-MLB (Other Projects)

These are from other projects unrelated to birdland-metrics.

### S3 Buckets

| Bucket | Objects | Size | Origin | Recommendation |
|--------|---------|------|--------|----------------|
| `friedmanalexander135453-dev` | 1,059 | 3.4 GB | Amplify media/video project | Review — largest bucket by far |
| `friedman-alexander-video-outputs-dev` | 126 | 77.5 MB | Video conversion outputs | Review if still needed |
| `datajournalismbackend-dev-databuckete3889a50-pizsk1kudqef` | 0 | 0 | Data journalism CDK stack (dev) | **Delete** — empty |
| `datajournalismbackend-prod-databuckete3889a50-oycvbhtw96tf` | 0 | 0 | Data journalism CDK stack (prod) | **Delete** — empty |
| `launch-angle05725-dev` | 0 | 0 | Launch Angle app (abandoned) | **Delete** — empty |
| `launch-angledd3d9-dev` | 0 | 0 | Launch Angle app (abandoned) | **Delete** — empty |
| `launchangle5526b3f2ca0041dbb4e8ca13c58b1760dd3d9-dev` | 0 | 0 | Launch Angle app (abandoned) | **Delete** — empty |
| `launchangle9e2d4-dev` | 0 | 0 | Launch Angle app (abandoned) | **Delete** — empty |

### Lambda Functions — Non-MLB

| Function | Runtime | Last Modified | Purpose | Recommendation |
|----------|---------|---------------|---------|----------------|
| `friedmanalexander-vod-convert` | python3.11 | Jul 2024 | Video on-demand conversion | Review if still used |
| `video-compression` | python3.8 | Jan 2023 | Video compression | **Delete** — 3 years old, Python 3.8 |
| `ffmpeg-conversion` | python3.8 | Jan 2023 | FFmpeg video conversion | **Delete** — 3 years old, Python 3.8 |

### Lambda Layer — Non-MLB

| Layer | Version | Recommendation |
|-------|---------|----------------|
| `ffmpeg` | v1 | Review — only needed if `friedmanalexander-vod-convert` is kept |

### DynamoDB Tables — Non-MLB

| Table | Items | Size | Origin | Recommendation |
|-------|-------|------|--------|----------------|
| `Audience-dev` | 0 | 0 | Newsletter/CRM project | **Delete** — empty |
| `Audience-prod` | 0 | 0 | Newsletter/CRM project | **Delete** — empty |
| `Campaigns-dev` | 0 | 0 | Newsletter/CRM project | **Delete** — empty |
| `Campaigns-prod` | 0 | 0 | Newsletter/CRM project | **Delete** — empty |
| `Entitlements-dev` | 0 | 0 | Feta/family app | **Delete** — empty |
| `Entitlements-prod` | 0 | 0 | Feta/family app | **Delete** — empty |
| `Comments-nsn5aua3trfczcqhooxdkpzkam-dev` | 42 | 16 KB | Social/family app | Review — has data |
| `Likes-nsn5aua3trfczcqhooxdkpzkam-dev` | 71 | 18 KB | Social/family app | Review — has data |
| `Profile-nsn5aua3trfczcqhooxdkpzkam-dev` | 5 | 1.9 KB | Social/family app | Review — has data |
| `ProfilePicture-nsn5aua3trfczcqhooxdkpzkam-dev` | 5 | 1.4 KB | Social/family app | Review — has data |
| `TimelinePost-nsn5aua3trfczcqhooxdkpzkam-dev` | 50 | 24 KB | Social/family app | Review — has data |
| `Username-nsn5aua3trfczcqhooxdkpzkam-dev` | 5 | 913 B | Social/family app | Review — has data |

### SQS Queues

| Queue | Recommendation |
|-------|----------------|
| `newsletter-send-dev` | Review if newsletter project is active |
| `newsletter-send-dlq-dev` | Review (dead letter queue) |
| `newsletter-send-dlq-prod` | Review |
| `newsletter-send-prod` | Review |

### SNS Topics

| Topic | Recommendation |
|-------|----------------|
| `amplify_codecommit_topic` | Review — may be orphaned from old Amplify setup |

### CloudWatch Log Groups — Non-MLB

| Log Group | Stored | Recommendation |
|-----------|--------|----------------|
| `/aws/apprunner/launch-angle/*/service` (x2) | 39 KB | **Delete** — abandoned Launch Angle app |
| `/aws/apprunner/launch-angle/*/application` | 375 B | **Delete** |
| `/aws/lambda/DataJournalismBackend-*` | 1 KB | **Delete** — empty project |
| `/aws/lambda/RequestUnicorn` | 3 KB | **Delete** — AWS tutorial leftover |
| `/aws/lambda/RequestUser` | 43 KB | **Delete** — AWS tutorial leftover |
| `/aws/lambda/S3Triggerfa0aa04c-*` (x2) | 48 KB | **Delete** — old S3 trigger |
| `/aws/lambda/amplify-*` (20+ groups) | ~35 KB total | **Delete** — orphaned Amplify Lambda logs |
| `/aws/lambda/fetadevvodservice-*` (x3) | 3.7 MB | Review — video service logs |
| `/aws/lambda/ffmpeg-conversion` | 81 KB | **Delete** — old video function |
| `/aws/lambda/friedmanalexander-vod-convert` | 680 KB | Review — goes with vod-convert Lambda |
| `/aws/lambda/friedman-alexander-vod-lambda` | 4 KB | **Delete** — old version |
| `/aws/lambda/video-compression` | 2.9 MB | **Delete** — old video function |
| `/aws/amplify/d5xxpaz8nz18n` | 1 KB | **Delete** — old Amplify app |

### IAM Roles — Non-MLB

| Role | Created | Recommendation |
|------|---------|----------------|
| `amplify-login-lambda-*` (8 roles) | 2021-2025 | Review — many may be orphaned |
| `friedmanalexander-vod-lambda-role` | May 2024 | Review — goes with vod-convert |
| `upClientLambdaRole05ec2c55135453-dev` | Apr 2024 | **Delete** — orphaned Amplify role |

---

## 4. S3 Bucket Detail — What's Inside Each Active Bucket

### `mlb-elo-ratings-output` (14.3 MB)
```
ballpark_distances.csv          9.8 KB   Ballpark GPS data for travel adjustments
ballpark_info.csv               2.3 KB   Ballpark metadata
elo-latest.json                 1.0 KB   Current 30-team ELO snapshot (frontend reads)
elo-ratings-full-history.csv   14.8 MB   Every game's ELO since 1871 (frontend ELO trend chart)
elo_rating_end_of_2024.csv      389 B    2024 end-of-season baseline
elo_rating_end_of_2025.csv      361 B    2025 end-of-season baseline
elo_rating_end_of_2025_raw.csv  361 B    Raw (pre-adjustment) 2025 baseline
injury_impact_players_2025.csv 16.5 KB   Player-level injury WAR impact
injury_impact_teams_2025.csv    867 B    Team-level injury ELO adjustment
pitcher_fip_2024.csv           52.6 KB   2024 pitcher FIP data
pitcher_fip_2025.csv           24.7 KB   2025 pitcher FIP data
preseason-adjustment-latest.json 2.7 KB  Preseason ELO adjustment details
```

### `mlb-predictions-2026` (316 KB)
```
playoff-odds-latest.json         1.3 KB  30-team playoff/division/WC probabilities
projections-latest.json          3.5 KB  Win projection distributions (median, p10-p90)
standings-latest.json            1.5 KB  Current standings snapshot
recent-games-latest.json         3.5 KB  Last ~10 Orioles games with scores/pitchers
next_game_win_expectancy.csv     2.6 KB  Next game prediction
season_win_simulations.parquet 306 KB    Raw simulation output (10K sims x 30 teams)
end-of-year-standings-predictions_*.csv  Historical prediction snapshots (3 dates)
season_win_projection_summary_*.csv      Summary snapshots (3 dates)
orioles_games_back_prediction_*.csv      GB prediction snapshots (3 dates)
```

### `mlb-player-stats-retrosheet` (1.8 MB)
```
batting-daily/                  11 CSVs  Per-game BAL batting lines (2015-2025)
pitching-daily/                 11 CSVs  Per-game BAL pitching lines (2015-2025)
season-totals/                  22 CSVs  Aggregated season batting + pitching stats
player-id-map.json             254 KB    4,020 Retrosheet player ID -> name mappings
player-stats-latest.json        26 KB    2025 BAL season: 35 batters, 41 pitchers
```

### `mlb-game-log-data-retrosheet` (32 MB)
```
gamelogs/gl1871.zip ... gl2024.zip     154 zip files — full Retrosheet game logs 1871-2024
gamelogs/glas.zip, gldv.zip, etc.      All-Star, division series, etc.
gamelogs/glfields.txt                  Field definitions
```

### `mlb-pipeline-artifacts` (161 MB)
```
mlb-pipeline-common.zip         73 MB   Lambda layer (pandas, pyarrow, requests, etc.)
lambda-layers/mlb-pipeline-common.zip   73 MB   Duplicate of above
archive/elo-ratings-*_old_formula.csv   23 MB   Archived old-formula ELO data
archive/elo-ratings-2025_old_pipeline.csv  298 KB  Old pipeline 2025 ELO
archive/elo_rating_end_of_2024_old_formula.csv  1 KB  Old formula baseline
```

---

## 5. Local Files — Cleanup Recommendations

### Inside `birdland-metrics/` — Safe to Delete

| Path | Type | Recommendation |
|------|------|----------------|
| `data-pipelines/output/` | Generated CSVs/JSONs | **Delete** — already uploaded to S3, regenerable via `bootstrap-retrosheet.py` |
| `data-pipelines/layers/mlb-pipeline-common/python/mlb_common/__pycache__/` | Compiled .pyc | **Delete** — auto-regenerated |
| `data-pipelines/functions/mlb-preseason-adjustment/__pycache__/` | Compiled .pyc | **Delete** — auto-regenerated |
| `player-stats-plan.md` | Dev planning doc | **Delete** — implementation is complete |
| `status.txt` | Status notes | Review — delete if no longer referenced |
| `.DS_Store` | macOS metadata | **Delete** — add to .gitignore |

### Inside `birdland-metrics/` — Keep but Consider Archiving

| Path | Notes |
|------|-------|
| `data-pipelines/model-2026-updates/` | 51 files of research scripts + CSVs. Valuable reference but large. Consider moving data files to S3 and keeping only the Python scripts + docs in git. |
| `data-pipelines/layers/mlb-pipeline-common/mlb-pipeline-common.zip` | 5 MB compiled layer zip. Regenerable via `build_layer.sh`. Could gitignore. |
| `data-pipelines/pipeline-artifacts/` (in S3) | `lambda-layers/mlb-pipeline-common.zip` is a duplicate of root-level zip — one copy is enough |

### Desktop — Other MLB Directories

| Path | Size | Recommendation |
|------|------|----------------|
| `~/Desktop/orioles-magic/` | Large (has node_modules) | **Delete** — old Angular 13 predecessor to birdland-metrics. Over 2 years old. |
| `~/Desktop/mlb-elo/` | Small | **Delete** — legacy Python ELO scripts, all functionality migrated into birdland-metrics Lambda pipeline |
| `~/Desktop/orioles-analytics-blog/` | Large | **Review** — separate full-stack project (Jan 2026). May be an earlier iteration of birdland-metrics or a parallel experiment. |
| `~/Desktop/chadwick/` | Medium | **Keep** — Chadwick source code. Needed if you ever need to rebuild `cwdaily`/`cwgame` tools. Alternatively, delete if you installed via Homebrew. |
| `~/Desktop/elo_ratings_by_game.csv` | 16 MB | **Delete** — research artifact, this data is now in `mlb-elo-ratings-output/elo-ratings-full-history.csv` on S3 |
| `~/Desktop/game_data_syntax.R` | 684 B | **Delete** — old R syntax reference, no longer using R |

---

## 6. AWS Cleanup Recommendations — Summary

### Immediate Deletes (Empty / Abandoned)

**S3 buckets (6 empty):**
```bash
aws s3 rb s3://datajournalismbackend-dev-databuckete3889a50-pizsk1kudqef
aws s3 rb s3://datajournalismbackend-prod-databuckete3889a50-oycvbhtw96tf
aws s3 rb s3://launch-angle05725-dev
aws s3 rb s3://launch-angledd3d9-dev
aws s3 rb s3://launchangle5526b3f2ca0041dbb4e8ca13c58b1760dd3d9-dev
aws s3 rb s3://launchangle9e2d4-dev
```

**DynamoDB tables (6 empty):**
```bash
aws dynamodb delete-table --table-name Audience-dev
aws dynamodb delete-table --table-name Audience-prod
aws dynamodb delete-table --table-name Campaigns-dev
aws dynamodb delete-table --table-name Campaigns-prod
aws dynamodb delete-table --table-name Entitlements-dev
aws dynamodb delete-table --table-name Entitlements-prod
```

**Old Lambda functions (Python 3.8, 3+ years old):**
```bash
aws lambda delete-function --function-name video-compression
aws lambda delete-function --function-name ffmpeg-conversion
```

### Prior Season Cleanup

**S3 buckets:**
```bash
aws s3 rm s3://mlb-predictions-2025 --recursive && aws s3 rb s3://mlb-predictions-2025
aws s3 rm s3://mlb-schedule-2025 --recursive && aws s3 rb s3://mlb-schedule-2025
```

**Duplicate in pipeline-artifacts:**
```bash
aws s3 rm s3://mlb-pipeline-artifacts/lambda-layers/mlb-pipeline-common.zip
```

### Bulk CloudWatch Log Cleanup

The old MLB Lambda log groups alone total ~158 MB. Delete them all:
```bash
for lg in \
  /aws/lambda/mlb-daily-elo-compute \
  /aws/lambda/mlb-daily-orioles-games-back \
  /aws/lambda/mlb-remaining-2025-schedule \
  /aws/lambda/mlb-season-simulations \
  /aws/lambda/mlb-elo-ratings-calculator \
  /aws/lambda/mlb-elo-ratings-fivethirtyeight \
  /aws/lambda/mlb-elo-ratings-kaggle \
  /aws/lambda/mlb-stats-api-game-data \
  /aws/lambda/mlb-stats-api-games-back-wc \
  /aws/lambda/mlb-stats-api-logos \
  /aws/lambda/mlb-statsapi \
  /aws/lambda/mlbstatsapi-playevents \
  /aws/lambda/mlbstatsapi-standings \
  /aws/lambda/mlbstatsapinodeaddgame-dev \
  /aws/lambda/mlbstatsapinode-dev \
  /aws/lambda/mlboriolesaddgame-dev \
  /aws/lambda/mlbstatsapilambda-dev \
  /aws/lambda/mlb-stats \
  /aws/lambda/triggerAtBatAddition \
  /aws/lambda/RequestUnicorn \
  /aws/lambda/RequestUser \
  /aws/lambda/ffmpeg-conversion \
  /aws/lambda/video-compression \
  /aws/lambda/friedman-alexander-vod-lambda \
  /aws/lambda/DataJournalismBackend-dev-CustomS3AutoDeleteObject-qkReYbrkvDcc \
  /aws/lambda/S3Triggerfa0aa04c-production \
  /aws/lambda/S3Triggerfa0aa04c-staging \
  /aws/apprunner/launch-angle/0ea8bc512456492d9819c8496da4bad5/service \
  /aws/apprunner/launch-angle/65f17703adf14f69a2a3a5978b0f3cae/application \
  /aws/apprunner/launch-angle/65f17703adf14f69a2a3a5978b0f3cae/service \
  /aws/amplify/d5xxpaz8nz18n; do
  aws logs delete-log-group --log-group-name "$lg"
done
```

Orphaned Amplify log groups (20+) — delete any `/aws/lambda/amplify-*` groups not tied to an active Amplify app.

### Old IAM Roles

Delete the 20 orphaned MLB IAM roles listed in Section 2 after confirming no Lambda functions reference them:
```bash
# Example for one:
aws iam delete-role --role-name mlb-daily-elo-compute-role-gcg0eg7b
# (May need to detach policies first)
```

### Duplicate Lambda Layer

```bash
aws lambda delete-layer-version --layer-name mlb_statsapi_layer --version-number 1
aws lambda delete-layer-version --layer-name mlb_statsapi_layer --version-number 2
```

---

## 7. Cost Impact Estimate

Most of the stale resources have minimal ongoing cost (S3 storage for empty buckets, DynamoDB on-demand with 0 items). The biggest savings come from:

| Resource | Monthly Cost | Notes |
|----------|-------------|-------|
| `friedmanalexander135453-dev` S3 | ~$0.08/mo | 3.4 GB storage |
| CloudWatch log storage | ~$0.02/mo | ~160 MB retained |
| Empty DynamoDB tables | $0 | On-demand, no reads/writes |
| Empty S3 buckets | $0 | No storage cost |

The cleanup is more about hygiene than cost savings — keeping the account organized and reducing confusion about what's active.
