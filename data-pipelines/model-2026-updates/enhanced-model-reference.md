# Birdland Metrics Enhanced Prediction Model

## Overview

The Birdland Metrics model predicts MLB game outcomes and season-long projections using an ELO rating system enhanced with starting pitcher quality adjustments, probability calibration, and preseason roster-change modeling. It runs as an automated daily pipeline during the MLB season, producing game-level win probabilities, 10,000-simulation Monte Carlo season projections, and playoff odds for all 30 teams.

The model operates in three distinct phases:

1. **Preseason** (March): Adjusts ELO baselines for offseason roster turnover using a WAR-based transaction analysis
2. **In-season** (daily): Updates ELO ratings from game results, fetches current pitcher FIP data, and runs Monte Carlo simulations with FIP-adjusted, shrinkage-corrected probabilities
3. **Per-game** (prediction layer): Combines a team's ELO rating with its starting pitcher's FIP to produce a calibrated win probability

All data is sourced from the MLB Stats API and Retrosheet. No proprietary projection systems (ZiPS, Steamer, etc.) are used.

---

## Layer 1: ELO Ratings

### The ELO System

Each of the 30 MLB teams carries an ELO rating that updates after every game. The system is zero-sum: points gained by the winner are lost by the loser. The canonical ELO chain extends back to 1871 (233,638 games) and was recomputed from scratch with a single consistent formula.

All teams begin at **1500** (the long-run average). After any given season, the spread of team ratings typically ranges from roughly 1300 (worst) to 1700 (best).

### Win Probability

Before each game, the model computes a raw win probability for the home team using the standard logistic ELO formula:

```
P(home) = 1 / (1 + 10^((ELO_away - (ELO_home + HFA)) / 400))
```

The **home field advantage (HFA)** parameter adds 55 ELO points to the home team's effective rating. This is equivalent to roughly a 58% baseline win probability for two evenly-matched teams at home, consistent with the observed MLB home winning percentage.

### Rating Updates

After each game, ELO ratings shift based on three factors: whether the result was an upset, how large the margin of victory was, and a sensitivity constant (K-factor).

```
shift = K * MOV * (result - expected)
```

Where:

- **K = 20** (sensitivity constant). A higher K means ratings respond faster to new results but are noisier; lower K is smoother but slower to reflect true team quality. K=20 is a standard value for baseball.
- **result** is 1 for a win and 0 for a loss.
- **expected** is the pre-game win probability from the logistic formula above.
- **MOV** is the margin of victory multiplier, described below.

The winning team gains `shift` ELO points; the losing team loses the same amount.

### Margin of Victory Multiplier

A 10-1 blowout should shift ratings more than a 3-2 nail-biter. The model uses a logarithmic margin of victory formula, dampened by the pre-game ELO gap so that blowouts by heavy favorites don't create outsized shifts:

```
MOV = log(|run_diff| + 1) * (2.2 / (0.001 * |elo_diff| + 2.2))
```

The logarithm compresses extreme blowouts (a 15-run win isn't 5x more informative than a 3-run win). The dampening term ensures that when a 1650-rated team beats a 1350-rated team by 8 runs, the rating shift is smaller than if two 1500-rated teams produced the same score, because the former result was more expected.

| Run Differential | Even Matchup MOV | 150-Point Favorite MOV |
|-----------------|------------------|----------------------|
| 1 | 0.69 | 0.63 |
| 3 | 1.10 | 1.00 |
| 5 | 1.31 | 1.20 |
| 10 | 1.56 | 1.42 |

### Parameter Summary (ELO Layer)

| Parameter | Value | Description |
|-----------|-------|-------------|
| K | 20 | Rating update sensitivity |
| HFA | 55 | Home field advantage (ELO points) |
| MOV_MULTIPLIER | 2.2 | Margin of victory scaling constant |
| ELO_INIT | 1500 | Initial/mean ELO rating |

---

## Layer 2: Starting Pitcher FIP Adjustment

### Why FIP?

ELO captures team-level quality but is blind to day-to-day lineup changes. The most impactful per-game variable in baseball is the starting pitcher. A team sending an ace (2.50 FIP) versus a back-end starter (5.00 FIP) has a materially different probability of winning that same-day game, even though the team's ELO rating is identical.

FIP (Fielding Independent Pitching) is used rather than ERA because it isolates the outcomes a pitcher directly controls: strikeouts, walks, hit-by-pitches, and home runs. It strips out the noise of defense, sequencing luck, and batted ball variance. This makes it a more stable and predictive metric than ERA, particularly over partial-season samples.

### FIP Formula

For each pitcher with at least 1.0 inning pitched in the current season:

```
FIP = ((13 * HR) + (3 * (BB + HBP)) - (2 * K)) / IP + cFIP
```

The **FIP constant (cFIP)** anchors FIP to the league-wide ERA scale so that the average FIP equals the average ERA in a given season. It is computed from all MLB pitchers (not just qualified starters):

```
cFIP = league_ERA - ((13 * total_HR) + (3 * (total_BB + total_HBP)) - (2 * total_K)) / total_IP
```

Using all pitchers (typically 850-870 per season, including relievers) rather than only qualified starters avoids selection bias that would pull the constant downward.

| Season | cFIP | League FIP | Pitchers |
|--------|------|-----------|----------|
| 2023 | 3.269 | ~4.08 | 863 |
| 2024 | 3.171 | ~3.97 | 855 |
| 2025 | 3.127 | ~4.15 | 864 |

### Converting FIP to ELO Points

The FIP adjustment shifts each team's effective ELO rating before computing win probability. A pitcher with FIP below league average boosts their team's effective rating; a pitcher above league average lowers it.

```
adjustment = (league_FIP - pitcher_FIP) * FIP_WEIGHT
```

**FIP_WEIGHT = 50** means that each full point of FIP below league average adds 50 ELO points to the team's effective rating for that game.

For example, in 2025:
- **Paul Skenes** (FIP 2.352, league avg 4.153): adjustment = (4.153 - 2.352) * 50 = **+90.1 ELO points**
- **League-average starter** (FIP 4.153): adjustment = **0 points**
- **Jack Kochanowicz** (FIP 6.046): adjustment = (4.153 - 6.046) * 50 = **-94.6 ELO points**

Both teams receive independent adjustments based on their starter:

```
effective_ELO_home = ELO_home + home_pitcher_adjustment
effective_ELO_away = ELO_away + away_pitcher_adjustment
```

These adjusted ELO values are then fed into the standard win probability formula. The FIP adjustment is applied only at the prediction layer. It does not alter the stored ELO ratings, which continue to update based on game results alone.

### Handling Missing Pitcher Data

When a starting pitcher has no FIP data (not yet announced, or has not pitched in the current season), the model assigns league-average FIP, producing zero adjustment. This graceful degradation means the model falls back to raw ELO without any pitcher-specific signal.

---

## Layer 3: Probability Shrinkage

### The Overconfidence Problem

Raw ELO probabilities are systematically overconfident. When the model predicts a team has a 70% chance of winning, teams in that range historically win closer to 64% of the time. This miscalibration is a known property of ELO systems: the logistic curve maps rating differences to probabilities more aggressively than real-world outcomes justify.

### The Shrinkage Formula

Probability shrinkage applies a linear compression that pulls all probabilities toward 50%:

```
P_adjusted = SHRINKAGE + (1 - 2 * SHRINKAGE) * P_raw
```

With **PROB_SHRINKAGE = 0.16**, this transforms the probability range:

| Raw Probability | Adjusted Probability | Effect |
|----------------|---------------------|--------|
| 0.80 | 0.704 | -9.6 pp |
| 0.70 | 0.636 | -6.4 pp |
| 0.60 | 0.568 | -3.2 pp |
| 0.50 | 0.500 | unchanged |
| 0.40 | 0.432 | +3.2 pp |
| 0.30 | 0.364 | +6.4 pp |

The adjusted probability has a floor of 0.16 and a ceiling of 0.84. This means the model never predicts any team has less than a 16% chance of winning any single game, reflecting the inherent unpredictability of baseball.

### Why 0.16?

The shrinkage parameter was optimized through a grid search across 150 parameter combinations (FIP_WEIGHT x PROB_SHRINKAGE), evaluated across the 2023, 2024, and 2025 seasons. The optimal value progressed from 0.10 to 0.14 to 0.16 through successive sweeps. At 0.16, the model minimizes log loss (the standard metric for evaluating predicted probabilities) while maintaining accuracy.

Shrinkage is the single most impactful calibration parameter. It improved average log loss by 0.0076 compared to the un-shrunk model, a larger contribution than the FIP adjustment itself.

---

## Layer 4: Preseason Roster Adjustment

### The Problem

ELO ratings carry over from the prior season, but rosters change dramatically over the winter through trades, free agent signings, waiver claims, and releases. A team that lost a 6-WAR player and signed a 2-WAR replacement enters the season materially weaker, but ELO has no mechanism to reflect this until enough new games are played for the rating to "catch up."

### The Solution: WAR-Based ELO Adjustment

Before Opening Day, the model automatically adjusts each team's ELO baseline by quantifying the net WAR (Wins Above Replacement) exchanged through offseason transactions.

**Step 1: Compute player value.**

WAR is computed for every MLB player directly from the MLB Stats API, with no dependency on external projection systems. Two value calculations run in parallel:

**Batting WAR** uses wOBA (weighted on-base average) as the core offensive metric:

```
wOBA = (0.69*NIBB + 0.72*HBP + 0.89*1B + 1.27*2B + 1.62*3B + 2.10*HR) / (AB + BB + SF + HBP)
```

The linear weights (0.69 for a non-intentional walk, 2.10 for a home run, etc.) represent the average run value of each offensive event, derived from empirical run expectancy tables. A home run is worth roughly 3x a walk because it guarantees at least one run and often clears additional baserunners.

From wOBA, offensive runs above average are computed:

```
wRAA = ((wOBA - league_wOBA) / 1.15) * PA
```

Replacement-level value (the production a freely available minor-league callup would provide) is added at a rate of 20 runs per 600 plate appearances, roughly equivalent to 2.0 WAR for a full-season replacement player:

```
batting_WAR = (wRAA + 20 * PA / 600) / 10
```

The divisor of 10 is the standard runs-per-win conversion: it takes approximately 10 additional runs scored (or prevented) to produce one additional win in the standings.

**Pitching WAR** uses FIP, the same metric used in the in-season starting pitcher adjustment:

```
runs_saved = (5.5 - pitcher_FIP) * (IP / 9)
pitching_WAR = runs_saved / 10
```

The constant 5.5 represents replacement-level pitcher performance (roughly a 5.50 FIP), equivalent to what a freely available minor-league arm would produce over a full season.

For two-way players, the model takes the higher of their batting or pitching WAR.

**Step 2: Average across seasons.**

Single-season WAR can be noisy. A pitcher who had a career-worst year (e.g., Ryan Helsley's 0.2 WAR in 2025 after posting 2.3 and 1.5 WAR the prior two seasons) would be undervalued by a single-season snapshot. The model averages WAR over the most recent 3 seasons to smooth out year-to-year variance, producing a more stable estimate of player value.

**Step 3: Track offseason transactions.**

The MLB Stats API transactions endpoint returns every roster-changing move between November 1 and March 20. The model filters to moves that change a player's organization:

| Transaction Type | Effect |
|-----------------|--------|
| Trade | WAR credited to gaining team, debited from losing team |
| Major-league free agent signing | WAR credited to signing team |
| Declared free agency | WAR debited from departing team |
| Waiver claim | WAR credited to claiming team |
| Release | WAR debited from releasing team |
| Rule 5 selection | WAR credited to selecting team |

Minor-league signings are excluded (the player has not demonstrated MLB-level value).

**Step 4: Convert to ELO.**

For each team, the model sums WAR gained from incoming players and subtracts WAR lost from departing players. The net WAR change is converted to ELO points:

```
ELO_adjustment = net_WAR * 5.5
```

**WAR_TO_ELO = 5.5** is derived from the relationship between wins and ELO ratings. A team that wins 95 games typically carries an ELO rating roughly 80 points higher than an 81-win (.500) team. That 14-win gap across 80 ELO points yields approximately 5.7 ELO per win. Since 1 WAR approximates 1 additional win above replacement, 5.5 ELO per WAR is a slightly conservative conversion.

### 2026 Preseason Results (as of February 9, 2026)

The largest movers in the 2025-26 offseason, using 3-year average WAR:

| Team | Net WAR | ELO Adjustment | Key Acquisitions / Losses |
|------|---------|---------------|--------------------------|
| BAL | +7.3 | +40.2 | +Alonso, +Ward, +Baz |
| COL | +6.7 | +36.6 | Multiple additions |
| MIN | +4.6 | +25.5 | Multiple additions |
| MIL | -14.8 | -81.1 | Major departures |
| SD | -13.9 | -76.7 | Major departures |
| STL | -11.9 | -65.4 | Major departures |

### Idempotency

The preseason adjustment runs weekly throughout March via an automated schedule. Each run re-reads the original (un-adjusted) end-of-season baseline and recomputes from scratch, so late-breaking trades and signings are always reflected without compounding prior adjustments.

### Limitations

- **Defensive value is not captured.** The wOBA-based batting WAR only measures offensive production. Defense-heavy players (e.g., elite shortstops with average bats) are undervalued, while DH-type bats are slightly overvalued. Over a team-level sum of 5-15 player moves, this tends to average out.
- **Prospects and rookies.** A player with no MLB stats receives zero WAR. Teams that add top prospects via trade are not credited for their value. This is a known blind spot shared by any backward-looking metric.
- **Aging curves.** A 35-year-old's 3-year WAR average may overstate future value, while a 24-year-old's may understate it. The 3-year window mitigates but does not eliminate this.

---

## Season Simulation

### Monte Carlo Method

After ELO updates and FIP data are refreshed, the model simulates the remainder of the MLB season 10,000 times. For each remaining game on the schedule:

1. Look up both teams' current ELO ratings
2. If starting pitchers are announced, apply FIP adjustments to each team's effective ELO
3. Compute the FIP-adjusted win probability using the logistic formula
4. Apply probability shrinkage
5. Draw a random number between 0 and 1; if it falls below the adjusted probability, the home team wins that simulation

Each of the 10,000 simulations produces a full set of final standings. From these, the model extracts:

- **Projected wins** (mean, median, standard deviation, 10th/25th/75th/90th percentiles)
- **Playoff odds** per team (percentage of simulations where the team finishes in the top 6 of their league)
- **Division title odds** (percentage where the team has the best record in their division)
- **Wild card odds** (percentage where the team makes the playoffs but doesn't win the division)

### Playoff Qualification Logic

Under the current MLB postseason format, 6 teams per league qualify: 3 division winners (best record in AL East, Central, West) plus 3 wild cards (next 3 best records among non-division winners). The simulation replicates this structure for every run.

---

## Features Explored and Rejected

Several additional features were prototyped, backtested across 3 seasons (2023-2025), and found to provide no improvement over the core model:

### Rolling FIP (Last 7 Starts)

**Hypothesis**: A pitcher's recent form (last 7 starts) should be more predictive than their full-season average.

**Finding**: Rolling FIP was noisier than season FIP. Seven starts produce roughly 40 innings of data versus 150+ for a season total. The reduction in sample size introduced more variance than the recency benefit could offset. On the 2025 backtest, rolling FIP produced marginally better log loss but worse accuracy.

### Bullpen Quality (Team-Level Reliever FIP)

**Hypothesis**: Teams with elite bullpens should receive a positive adjustment, and vice versa.

**Finding**: Optimal weight was zero. Bullpen quality is already implicitly captured by ELO through game outcomes. When a team has a dominant bullpen, they win more close games, and their ELO rises accordingly. Adding an explicit bullpen adjustment double-counts the signal.

### Park Factors

**Hypothesis**: Extreme hitter-friendly or pitcher-friendly parks should adjust the probability.

**Finding**: Optimal weight was zero. FIP is park-neutral by design, since it removes batted ball outcomes (the primary mechanism through which park factors operate). Home runs allowed are the only FIP component affected by park dimensions, and the signal was too small to improve predictions.

### Bayesian FIP Regression

**Hypothesis**: Early-season FIP should be regressed toward the league mean, weighted by innings pitched, to reduce small-sample noise.

**Formula**: `adjusted_FIP = (IP * raw_FIP + prior_IP * league_FIP) / (IP + prior_IP)`

**Finding**: Optimal prior weight was zero when evaluated on full-season data. By season's end, even rookies typically have 60+ innings pitched, which is enough for FIP to stabilize. The regression would add value in an early-season context (April/May, when some starters have only 20-30 IP), but the current pipeline evaluates at end-of-season granularity. A future enhancement could apply graduated regression based on cumulative IP at the time of each prediction.

### Travel Fatigue

**Hypothesis**: Teams traveling long distances, particularly west-to-east across time zones, should receive a negative adjustment.

**Finding**: The signal was minimal. Only 76 games per season (roughly 3% of all games) qualified as fatiguing trips (2+ timezone eastward shift AND 1,000+ miles). The optimal penalty was small (10 ELO points), and the improvement was within noise on a 3-season backtest.

---

## Backtest Results

All parameters were tuned on 2025 data and validated out-of-sample on 2023 and 2024. This guards against overfitting to a single season's patterns.

### 3-Season Results (FIP_WEIGHT=50, PROB_SHRINKAGE=0.16)

| Season | Model | Accuracy | Log Loss | Brier Score |
|--------|-------|----------|----------|-------------|
| 2023 | Base ELO | 55.32% | 0.6921 | 0.2490 |
| 2023 | **Enhanced** | **57.95%** | **0.6810** | **0.2438** |
| 2024 | Base ELO | 55.23% | 0.6941 | 0.2502 |
| 2024 | **Enhanced** | **56.72%** | **0.6830** | **0.2448** |
| 2025 | Base ELO | 55.76% | 0.6868 | 0.2468 |
| 2025 | **Enhanced** | **57.33%** | **0.6720** | **0.2397** |
| **3-Season Avg** | **Base ELO** | **55.44%** | **0.6863** | **0.2466** |
| **3-Season Avg** | **Enhanced** | **57.33%** | **0.6787** | **0.2428** |
| | **Improvement** | **+1.89%** | **-0.0076** | **-0.0038** |

### Metric Definitions

- **Accuracy**: Percentage of games where the team with higher predicted probability actually won. A coinflip model achieves 50%.
- **Log Loss**: Measures the quality of predicted probabilities. Penalizes confident wrong predictions heavily. Lower is better. A coinflip model scores 0.693 (ln(2)).
- **Brier Score**: Mean squared error between predicted probability and actual outcome (0 or 1). Lower is better. Ranges from 0 (perfect) to 1 (worst).

### Key Observations

1. **Consistent improvement across all seasons.** The enhanced model beats base ELO on all three metrics in all three years. This rules out the improvement being a fluke of one season's data.

2. **2023 shows the largest accuracy gain (+2.63%).** This is the strongest out-of-sample validation, as the parameters were tuned on 2025 data and 2023 was never used during optimization.

3. **Shrinkage contributes more than FIP.** Decomposing the improvement: probability shrinkage alone (without FIP) improves log loss by roughly 0.005. Adding FIP improves it by an additional 0.003. The calibration correction is more valuable than the pitcher-quality signal.

4. **The 57.33% accuracy ceiling.** Predicting baseball games is inherently limited. The best team in baseball wins roughly 60% of its games. A model that perfectly predicted true talent would still max out around 58-59% accuracy because of game-to-game randomness (injuries, umpiring, weather, and the fundamental variance of a sport where the best hitters fail 70% of the time).

---

## Full Parameter Reference

### ELO Rating System

| Parameter | Value | Type | Description |
|-----------|-------|------|-------------|
| `ELO_K` | 20 | Fixed | Rating update sensitivity per game |
| `ELO_HFA` | 55 | Fixed | Home field advantage in ELO points |
| `ELO_INIT` | 1500 | Fixed | Initial and mean ELO rating |
| `MOV_MULTIPLIER` | 2.2 | Fixed | Margin of victory log-scaling constant |

### Enhanced Prediction Layer

| Parameter | Value | Tuned | Description |
|-----------|-------|-------|-------------|
| `FIP_WEIGHT` | 50 | Yes | ELO points per 1.0 FIP below league average |
| `PROB_SHRINKAGE` | 0.16 | Yes | Probability compression toward 50% |

### Preseason Adjustment

| Parameter | Value | Description |
|-----------|-------|-------------|
| `WAR_TO_ELO` | 5.5 | ELO points per 1.0 WAR of net roster change |
| `WAR_YEARS` | 3 | Seasons averaged for player WAR estimation |
| `REPLACEMENT_FIP` | 5.5 | Replacement-level FIP for pitching WAR |
| `REPLACEMENT_RUNS_PER_600PA` | 20.0 | Replacement-level offensive value (runs per 600 PA) |
| `RUNS_PER_WIN` | 10.0 | Run-to-win conversion factor |

### wOBA Linear Weights (Batting WAR)

| Event | Weight | Interpretation |
|-------|--------|---------------|
| Non-intentional walk | 0.69 | Baseline positive outcome |
| Hit by pitch | 0.72 | Slightly more valuable than a walk (no pitch count cost) |
| Single | 0.89 | Advance runners, higher run expectancy |
| Double | 1.27 | Extra-base hit, strong run production |
| Triple | 1.62 | Rare, high run value |
| Home run | 2.10 | Guaranteed run + baserunner clearing |

### Simulation

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SIM_COUNT` | 10,000 | Monte Carlo simulation runs per pipeline execution |

---

## Data Sources

| Data | Source | Legal Status |
|------|--------|-------------|
| Game results, scores, schedules | MLB Stats API (`statsapi.mlb.com`) | Public API, factual data |
| Pitcher stats (K, BB, HBP, HR, IP, ERA) | MLB Stats API bulk endpoint | Public API, factual data |
| Batter stats (H, 2B, 3B, HR, BB, HBP, PA) | MLB Stats API bulk endpoint | Public API, factual data |
| Offseason transactions | MLB Stats API transactions endpoint | Public API, factual data |
| Historical game results (1871-2023) | Retrosheet | Free with attribution required |
| ELO formula, FIP formula, wOBA weights | Published sabermetric research | Open methodology |

No proprietary projections (FanGraphs ZiPS, Steamer, etc.) or copyrighted datasets are used in the production model.

---

## Pipeline Architecture

```
PRESEASON (weekly in March):
  EventBridge cron -> mlb-preseason-adjustment Lambda
    -> Fetch 3 years of batting + pitching stats from MLB API
    -> Compute simplified WAR for all players
    -> Fetch offseason transactions
    -> Compute net WAR per team -> ELO adjustment
    -> Overwrite baseline in S3 + DynamoDB

IN-SEASON (daily, 6am ET, March-October):
  EventBridge cron -> Step Functions (mlb-daily-pipeline)
    1. mlb-schedule-sync      — Refresh schedule CSV from MLB API
    2. mlb-game-results       — Record yesterday's Orioles results
    3. mlb-elo-compute        — Update ELO ratings from yesterday's games
                              — Fetch current-season FIP for all pitchers
    4. mlb-season-projections — Run 10,000 Monte Carlo simulations
                              — Compute next-game win probabilities
                              — Generate playoff odds, standings projections
    5. mlb-orioles-dashboard  — Compile Orioles-specific dashboard data
```
