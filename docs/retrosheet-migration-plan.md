# Plan: Migrate Data Pipeline from MLB Stats API to Open Data Sources

## Goal

Remove all MLB Stats API calls from the Lambda pipeline to eliminate legal risk for commercial use. Replace with **Retrosheet + Lahman** (historical/preseason) and **pybaseball** (in-season bridge). Remove live game scores from the Angular frontend.

## Key Constraint

Retrosheet updates semi-annually, NOT daily — it cannot power the in-season pipeline alone. **pybaseball** (MIT-licensed, accesses FanGraphs/Baseball Reference public data) bridges this gap for current-season game results and pitcher stats.

## Legal Basis

Game scores and statistics are facts, not copyrightable (Feist v. Rural Telephone). The risk is with MLB's API Terms of Service, not the data itself. Retrosheet and Lahman are explicitly open for commercial use. pybaseball accesses publicly available factual data. Our model outputs (ELO, projections, odds) are original work.

---

## Phase 0: Shared Lambda Layer

### `config.py` — Remove MLB API constants
- Delete lines 45-52: `ORIOLES_TEAM_ID`, `AL_LEAGUE_ID`, all four `MLB_*_URL` constants
- Add: `ORIOLES_ABBR = 'BAL'`

### `fip.py` — Replace MLB API with pybaseball
- Replace `fetch_pitcher_fip()`: use `pybaseball.pitching_stats(season, qual=0)` instead of `requests.get(MLB_PITCHING_STATS_URL, ...)`
- Same return signature: `(fip_dict, lg_fip)` — but key the dict by **normalized pitcher name** instead of MLB numeric ID
- FIP computation formulas stay identical (cFIP, individual FIP)
- Update `fip_adjustment()`: accept pitcher names instead of IDs for lookup keys

### `team_codes.py` — Add pybaseball team code mapping
- pybaseball uses Baseball Reference codes (e.g., `KCR`, `SFG`, `TBR`, `CHW`, `SDP`, `WSN`, `ARI`, `OAK`)
- The existing `SCHEDULE_TO_ELO_MAP` already maps these exact codes to our canonical format — reuse it
- Add helper: `normalize_name(name)` for fuzzy pitcher name matching (strip accents, lowercase, remove suffixes)

### Layer dependencies
- **Remove:** `MLB-StatsAPI` package, direct `requests` import in `fip.py`
- **Add:** `pybaseball` (MIT license; brings pandas/requests as transitive deps, pandas already in layer)

---

## Phase 1: `mlb-schedule-sync` — Replace MLB Schedule API

**Current:** Single bulk call to `statsapi.mlb.com/api/v1/schedule` for all ~2,430 games.
**New:** `pybaseball.schedule_and_record(season, team)` for each of 30 teams, then deduplicate.

### Key changes
- Remove: `requests`, `MLB_SCHEDULE_URL`, `MLB_GAME_FEED_URL`, `fetch_full_schedule()`, `backfill_score()`, `extract_game_row()`
- Add: `from pybaseball import schedule_and_record`
- New `fetch_schedule_pybaseball(season)`: loops 30 teams, deduplicates by date+home+away
- **gamePk replacement:** Generate synthetic IDs (`{YYYYMMDD}_{home}_{away}_{gamenum}`) since MLB's numeric IDs are gone
- **Starting pitchers:** pybaseball's `schedule_and_record()` does NOT reliably provide starter IDs/names. Leave pitcher columns blank — the FIP lookup (Phase 3) falls back to league-average FIP gracefully when pitchers are unknown. Pitcher names will be populated post-game from the Win/Loss/Save columns that pybaseball does provide.

### CSV schema (unchanged columns, new ID format)
`date, gamePk, status, homeTeam, awayTeam, homeScore, awayScore, venueName, homeStartingPitcherName, awayStartingPitcherName`

Remove `homeStartingPitcherId` and `awayStartingPitcherId` columns (no longer available).

---

## Phase 2: `mlb-game-results` — Replace statsapi library

**Current:** `statsapi.schedule(start_date, end_date, team=110)` for Orioles daily games.
**New:** `pybaseball.schedule_and_record(season, 'BAL')` filtered to yesterday/today.

### Key changes
- Remove: `import statsapi`, `ORIOLES_TEAM_ID`
- Add: `from pybaseball import schedule_and_record`
- Rewrite `build_game_item()`: map pybaseball columns (`Date`, `Opp`, `R`, `RA`, `W/L`, `Win`, `Loss`, `Save`) to existing DynamoDB schema
- Use synthetic game IDs matching Phase 1 format
- Normalize team codes via existing `SCHEDULE_TO_ELO_MAP`

---

## Phase 3: `mlb-elo-compute` — Replace FIP API call

**Current:** Calls `fetch_pitcher_fip()` from shared `fip.py` which hits MLB Stats API.
**New:** `fip.py` already rewritten in Phase 0 — this Lambda just consumes the new return format.

### Key changes (minimal)
- FIP CSV schema: replace `pitcher_id` column with `pitcher_name` as primary key
- FIP dict already keyed by name from Phase 0
- ELO computation loop: **zero changes** (reads schedule CSV + prior ELO baselines, no API calls)

---

## Phase 4: `mlb-season-projections` — Update FIP lookup only

**Current:** No API calls. Reads FIP CSV keyed by `pitcher_id` (MLB numeric).
**New:** Read FIP CSV keyed by `pitcher_name`.

### Key changes
- `load_fip_data()` (line 56): change `int(row['pitcher_id'])` to `normalize_name(row['pitcher_name'])` as dict key
- `enhanced_probability()` (line 77): accept pitcher names instead of IDs; look up via `normalize_name()`
- `generate_next_game_predictions()` (line 91): use `homeStartingPitcherName`/`awayStartingPitcherName` instead of `homeStartingPitcherId`/`awayStartingPitcherId`
- `simulate_season()` (line 146): same change for pitcher lookups in remaining game simulation

All computation logic (Monte Carlo, playoff odds, standings) stays **identical**.

---

## Phase 5: `mlb-orioles-dashboard` — Replace Standings API + Remove Spring Training

**Current:** Two MLB API calls — standings API for actual GB, spring training schedule.
**New:** `pybaseball.standings()` for actual standings; remove spring training entirely.

### Key changes
- `fetch_actual_games_back()`: replace MLB standings API with `pybaseball.standings(year)` — returns division DataFrames with W/L/GB. Compute wildcard GB by sorting all AL teams by wins and finding the WC3 cutoff.
- `fetch_spring_training_games()`: **delete entirely**. Spring training data not available from open sources, and live scores being removed from frontend.
- `build_recent_games_json()`: remove spring training fallback (lines 113-117). Return empty list when no regular season games exist.

---

## Phase 6: `mlb-preseason-adjustment` — Replace All 3 API Calls

This Lambda has the **most** API dependencies but is the cleanest to migrate — it only needs historical data, which Retrosheet + Lahman have completely.

### 6a: Batting WAR — Lahman `Batting.csv` (replaces MLB batting stats API)
- Download Lahman CSVs to S3 (`mlb-pipeline-artifacts` bucket) as one-time setup
- `fetch_batting_war()`: read `Batting.csv` from S3, compute wOBA → wRAA → WAR using same formulas
- Player IDs switch from MLB numeric to Lahman string IDs (`troutmi01`)

### 6b: Pitching WAR — Lahman `Pitching.csv` (replaces MLB pitching stats API)
- Same approach: read from S3, compute FIP → runs saved → WAR
- `IPouts` field in Lahman = innings pitched × 3 (convert: `IP = IPouts / 3`)

### 6c: Transactions — Retrosheet transaction files OR hand-curated CSV
- Retrosheet publishes `.TRN` files with all player movements
- **Timing concern:** Retrosheet files for current offseason may not be available by March
- **Practical approach:** Use pybaseball `batting_stats()`/`pitching_stats()` for WAR (same as existing prototype at `model-2026-updates/preseason_adjustment.py` line 25), and maintain a hand-curated transactions CSV in S3 for the first season
- The prototype already demonstrates pybaseball WAR lookup + MLB transactions API. We keep the pybaseball WAR approach and replace only the transactions source.

### Alternative (simpler first pass)
The existing prototype at `model-2026-updates/preseason_adjustment.py` already uses `pybaseball.batting_stats()` and `pybaseball.pitching_stats()` for WAR. Port this directly into the Lambda, replacing only `fetch_offseason_transactions()` with an S3-based CSV reader. This is faster to implement and can be migrated to pure Lahman+Retrosheet later.

---

## Phase 7: Angular Frontend — Remove Game Scores

### `home.component.html`
- Remove the `<app-recent-games>` block and its surrounding `@if` / `<hr>` divider
- Remove the `recentGames()` and `gamesType()` references

### `home.component.ts`
- Remove: `recentGames` signal, `gamesType` signal, the games portion of `loadDashboard()`, the `RecentGamesComponent` import
- Keep: all model/projection data loading (unchanged)

### Optionally delete entirely
- `src/app/features/home/components/recent-games/` (entire directory — component no longer used)

---

## Files Modified Summary

| File | Severity | Change |
|------|----------|--------|
| `layers/.../config.py` | Minor | Remove MLB API URLs + numeric IDs |
| `layers/.../fip.py` | Major | Rewrite to use pybaseball, key by name |
| `layers/.../team_codes.py` | Minor | Add `normalize_name()` helper |
| `functions/mlb-schedule-sync/lambda_function.py` | Major | Replace MLB schedule API with pybaseball |
| `functions/mlb-game-results/lambda_function.py` | Major | Replace statsapi lib with pybaseball |
| `functions/mlb-elo-compute/lambda_function.py` | Minor | FIP dict key change (ID → name) |
| `functions/mlb-season-projections/lambda_function.py` | Moderate | FIP lookup by name, pitcher name columns |
| `functions/mlb-orioles-dashboard/lambda_function.py` | Major | pybaseball standings, remove spring training |
| `functions/mlb-preseason-adjustment/lambda_function.py` | Major | Lahman/pybaseball for WAR, CSV for transactions |
| `src/app/features/home/home.component.html` | Minor | Remove recent-games block |
| `src/app/features/home/home.component.ts` | Minor | Remove games signals + loading |

## One-Time Setup (not code changes)

1. Upload Lahman CSVs (`Batting.csv`, `Pitching.csv`, `People.csv`) to `mlb-pipeline-artifacts` S3 bucket
2. Prepare offseason transactions CSV for 2025-2026 offseason, upload to S3
3. Update Lambda layer `requirements.txt`: remove `MLB-StatsAPI`, add `pybaseball`
4. Rebuild and deploy Lambda layer

---

## Verification

1. **Unit test each Lambda locally** with pybaseball calls — ensure same output schema
2. **Shared layer test:** `fetch_pitcher_fip(2025)` returns dict keyed by name with valid FIP values
3. **Schedule sync test:** output CSV matches column schema, synthetic game IDs are unique, team codes are canonical
4. **Season projections test:** Monte Carlo runs correctly with name-based FIP lookups, playoff-odds-latest.json schema unchanged
5. **Preseason test:** WAR values from Lahman/pybaseball comparable to prior MLB API values (within ~0.5 WAR per team)
6. **Frontend test:** Home page loads without recent-games component, sidebar projections display normally
7. **End-to-end:** Run full Step Function pipeline, verify S3 JSON outputs match expected schema for Angular consumption
8. **Grep verification:** `grep -r "statsapi" data-pipelines/` and `grep -r "statsapi.mlb.com" data-pipelines/` return zero results
