# Birdland Metrics Model vs FanGraphs — Comparison & Changelog

This document tracks how the Birdland Metrics prediction model compares to FanGraphs projections, and how each enhancement changes model behavior. Updated as features are added.

---

## Current Model: ELO + Starting Pitcher FIP

### Base ELO System

| Parameter | Birdland Metrics | FanGraphs |
|-----------|-----------------|-----------|
| **Model type** | ELO rating system | ZiPS/Steamer projections + depth charts |
| **Core metric** | Team ELO rating (updated after each game) | Player-level projections aggregated to team WAR |
| **K-factor** | 20 (fixed) | N/A (not ELO-based) |
| **Home field advantage** | +55 ELO points | Park-adjusted, varies by team/park |
| **Margin of victory** | log(|diff|+1) * (2.2 / (0.001*|elo_diff| + 2.2)) | N/A (not game-result-based) |
| **Season regression** | End-of-prior-season ELO as baseline | Full preseason projections |
| **History** | 1871–present (233,638 games, canonical formula) | ~20 years of projection data |

**Key difference**: Birdland Metrics uses a reactive model — ELO updates based on game outcomes and trends toward true team strength over time. FanGraphs uses a predictive model — projecting individual player performance and aggregating to team-level.

### Starting Pitcher FIP

| Parameter | Birdland Metrics | FanGraphs |
|-----------|-----------------|-----------|
| **Formula** | ((13*HR) + (3*(BB+HBP)) - (2*K)) / IP + cFIP | Same standard FIP formula |
| **FIP constant** | Calculated from all MLB pitchers with >0 IP in the season | Calculated from all MLB pitching |
| **Data source** | MLB Stats API (official) | Official MLB data |
| **Stat type** | Season stats (current year) or yearByYear (historical) | Projected stats (ZiPS/Steamer blend) |

**Key difference**: Birdland Metrics FIP is descriptive (what has happened this season). FanGraphs FIP in projections is forward-looking (what the model expects going forward). Early-season Birdland FIP will be noisy with small sample sizes; FanGraphs blends priors.

#### FIP Constant Validation (2024)

| Metric | Birdland Metrics | FanGraphs |
|--------|-----------------|-----------|
| **cFIP** | 3.171 | ~3.17 |
| **Skenes FIP** | 2.45 | 2.44 |
| **Skubal FIP** | 2.50 | 2.51 |
| **Sale FIP** | 2.09 | 2.08 |

After correcting the FIP constant to use all pitchers (not just 50+ IP), values align closely with FanGraphs. Small differences (~0.01) come from rounding and minor data timing differences.

#### FIP Constant Validation (2025)

| Metric | Birdland Metrics | FanGraphs |
|--------|-----------------|-----------|
| **cFIP** | 3.103 | TBD |
| **Skenes FIP** | 2.33 | TBD |
| **Skubal FIP** | 2.42 | TBD |

---

## Planned Enhancements

### Travel/Fatigue Features (prototype complete)

| Parameter | Birdland Metrics | FanGraphs |
|-----------|-----------------|-----------|
| **Distance data** | Haversine great-circle distance between 30 parks | Not modeled |
| **Timezone tracking** | UTC offset per park, directional shift per trip | Not modeled |
| **Fatigue threshold** | 2+ timezone east shift AND 1,000+ miles (83 qualifying trips) | N/A |
| **Travel burden** | Per-team average distance (SEA highest at 1,780 mi, CWS lowest at 841 mi) | N/A |

**Key difference**: FanGraphs does not explicitly model travel fatigue. This is a differentiating feature for Birdland Metrics — research suggests west-to-east travel across multiple time zones negatively impacts performance.

### Injury/IL Impact (prototype complete)

| Parameter | Birdland Metrics | FanGraphs |
|-----------|-----------------|-----------|
| **IL data source** | MLB Stats API 40-man roster, date-specific snapshots | FanGraphs depth charts |
| **Impact metric** | WAR lost (sum of positive WAR for IL players) | Automatic via depth chart projection swap |
| **WAR source** | FanGraphs WAR via pybaseball (current year + prior-year fallback) | Internal projections |
| **ID cross-reference** | MLB API ID → FanGraphs ID via pybaseball `playerid_reverse_lookup` | Internal |
| **Pitcher vs position** | Tracked separately (pitcher WAR lost vs position WAR lost) | Not separated |
| **Negative WAR players** | Not counted as WAR "lost" (team isn't weakened by losing them) | Replacement-level player swapped in |

**Key difference**: FanGraphs adjusts projections by swapping in the replacement player's projected stats. Birdland Metrics quantifies the WAR gap — how much value is missing from the roster. This is simpler but captures the magnitude of injury impact well.

**Validation (July 15, 2025)**: 238 players on IL across MLB, 100.9 total WAR lost. Most impacted: HOU (10.4 WAR, 16 players). BAL had 4.9 WAR lost (15 IL players including Grayson Rodriguez at 2.0 prior-year WAR, Rutschman at 1.2, Bradish at 1.1).

### Backtest Results (2023–2025)

Parameters tuned on 2025, validated out-of-sample on 2023 and 2024. Updated after v2 feature exploration.

**Current best model**: ELO + Season FIP + Travel, PROB_SHRINKAGE=0.14

| Season | Model | Accuracy | Log Loss | Brier Score |
|--------|-------|----------|----------|-------------|
| 2023 | Base ELO | 55.32% | 0.6921 | 0.2490 |
| 2023 | **Enhanced** | **57.71%** | **0.6802** | **0.2435** |
| 2024 | Base ELO | 55.23% | 0.6941 | 0.2502 |
| 2024 | **Enhanced** | **56.51%** | **0.6848** | **0.2456** |
| 2025 | Base ELO | 55.76% | 0.6868 | 0.2468 |
| 2025 | **Enhanced** | **56.83%** | **0.6768** | **0.2421** |
| **Avg** | **Delta** | **+1.58%** | **-0.0104** | **-0.0049** |

The enhanced model improves all three metrics consistently across all three seasons. The 2023 out-of-sample improvement (+2.39% accuracy) is the strongest, confirming parameters are not overfit to 2025.

**Calibration**: Probability shrinkage (0.14) corrects ELO overconfidence. Upgraded from 0.10 after v2 feature sweep revealed higher shrinkage improves log loss and Brier without hurting accuracy.

**FIP coverage**: ~4,700-4,850 pitcher-games matched per season (out of ~4,860 total). Name-based matching achieved 99.5%+ coverage when pitcher IDs were unavailable (2023, 2024 schedules).

### V2 Feature Exploration (2026-02-09)

Tested 4 additional features against the season FIP baseline. None improved on the core model:

| Feature | Finding | Optimal Weight |
|---------|---------|---------------|
| **Rolling FIP** (last 7 starts) | Noisier than season FIP (7 starts vs 30+). Slightly better log loss but worse accuracy. | Not used |
| **Bullpen quality** (team BP FIP) | No improvement. Already captured by ELO through game outcomes. | 0 |
| **Park factors** (FanGraphs 5yr) | No improvement. FIP is already park-neutral by design (removes batted ball outcomes). | 0 |
| **Higher shrinkage** | Real win from v2 sweep. Corrects remaining overconfidence. | **0.14** (upgraded from 0.10) |

**Net effect**: Avg log loss improved from 0.6844 to 0.6806 (delta -0.0038) and avg Brier from 0.2453 to 0.2437 (delta -0.0016) solely from the shrinkage upgrade. Accuracy unchanged at 57.02%.

---

## Philosophical Differences

| Aspect | Birdland Metrics | FanGraphs |
|--------|-----------------|-----------|
| **Approach** | Results-based (how teams have performed) | Talent-based (what players are projected to do) |
| **Strength** | Captures momentum, team chemistry, managerial effects | Captures true talent, regression to mean |
| **Weakness** | Slow to react to roster changes, injuries | Can be slow to incorporate "hot" or "cold" streaks |
| **SP adjustment** | Actual season FIP of today's starter | Projected rest-of-season FIP |
| **Update frequency** | After every game | Daily depth chart updates |

---

## Changelog

### 2026-02-09: V2 Feature Exploration + Shrinkage Upgrade
- **Change**: Built and tested 4 features: rolling FIP (last 7 starts), team bullpen FIP, park factors, higher probability shrinkage
- **Tools built**: `precompute_features.py` (rolling FIP + bullpen FIP), `park_factors.py` (static FanGraphs data)
- **540-combination parameter sweep** on 2025: FIP_WEIGHT x BULLPEN_WEIGHT x PARK_SCALE x PROB_SHRINKAGE
- **Finding**: Rolling FIP, bullpen, and park factors all optimal at 0 weight. Higher shrinkage (0.14 vs 0.10) was the sole improvement.
- **Shrinkage upgrade**: PROB_SHRINKAGE 0.10 -> 0.14. Average log loss improved -0.0038, Brier -0.0016, accuracy unchanged at 57.02%
- **Why rolling FIP didn't help**: Season FIP averages 30+ starts (lower variance) vs rolling FIP's 7. The noise outweighs the recency benefit.
- **Why bullpen/park didn't help**: ELO already implicitly captures bullpen quality through game outcomes. FIP removes batted ball outcomes, making it park-neutral by design.

### 2026-02-08: FIP Constant Fix
- **Change**: FIP constant calculation updated to use ALL pitchers (>0 IP) instead of only 50+ IP
- **Impact**: All FIP values shifted up by ~0.03 (2025) to ~0.06 (2024)
- **Reason**: 50+ IP filter biased toward better pitchers with lower ERA, pulling the constant down
- **Validation**: After fix, 2024 values match FanGraphs within 0.01 (Skenes 2.45 vs 2.44, Skubal 2.50 vs 2.51)

### 2026-02-09: Backtest on 2023 and 2024
- **Change**: Generated schedule CSVs and FIP data for 2023 and 2024, extracted ELO baselines from full history, ran enhanced model on all 3 seasons
- **2023 FIP**: 797 pitchers, cFIP=3.269 (via roster mode + yearByYear stats)
- **Name-based FIP matching**: Added `normalize_name()` for accent/suffix-insensitive matching when pitcher IDs aren't in schedule CSV. 99.5%+ match rate.
- **Out-of-sample validation**: 2023 showed +2.39% accuracy improvement (strongest of all 3 seasons), confirming parameters are not overfit
- **3-season average improvement**: +1.58% accuracy, -0.0066 log loss, -0.0034 Brier score

### 2026-02-08: Enhanced Win Probability Model
- **Change**: Built `enhanced_model.py` — combines ELO + SP FIP + travel into per-game win probabilities
- **Architecture**: All adjustments converted to ELO-equivalent points, then fed through logistic win probability formula with probability shrinkage
- **Parameter sweep** (240 combinations on 2025 data):
  - FIP_WEIGHT=40 (ELO points per 1 FIP below league avg; higher than initial 25)
  - TRAVEL_PENALTY=10 (minimal signal on 1 season; 76 games affected)
  - PROB_SHRINKAGE=0.10 (critical for calibration — raw ELO is overconfident)
- **2025 results** (vs base ELO): Accuracy 55.76% → 56.83% (+1.07%), Log Loss 0.6868 → 0.6799 (-0.0069), Brier 0.2468 → 0.2434 (-0.0033)
- **Calibration fix**: 0.7-0.8 bucket overconfidence cut from -0.13 to -0.06; 0.8-0.9 bucket nearly perfect (-0.009)
- **FIP is the main driver** — isolated FIP-only run showed most of the improvement; travel alone was marginal

### 2026-02-08: Injury/IL Impact Prototype
- **Change**: Built `injury_impact.py` — pulls IL rosters from MLB API, maps to FanGraphs WAR, quantifies per-team impact
- **Bug found & fixed**: FanGraphs includes all pitchers in batting stats with 0.0 WAR. Initial `lookup_war` checked batting first, returning 0.0 for pitchers instead of their real pitching WAR. Fixed by taking max of batting and pitching WAR.
- **Prior-year fallback**: Players injured before accumulating current-year stats (e.g., Grayson Rodriguez) fall back to prior-year WAR
- **Outputs**: `injury_impact_teams_{date}.csv` (per-team summary) + `injury_impact_players_{date}.csv` (per-player detail)

### 2026-02-08: Ballpark Distance Table
- **Change**: Built `ballpark_distances.py` — static lat/lon for 30 parks, Haversine pairwise distances, timezone shift tracking
- **Athletics**: Using Sutter Health Park (Sacramento) for 2025+ after relocation
- **Outputs**: `ballpark_info.csv` (30 parks) + `ballpark_distances.csv` (435 pairs with distance, tz shift, direction)

### 2026-02-07: ELO Audit
- **Change**: Recomputed all ELO from scratch (1871-2025, 233,638 games) with canonical formula
- **Impact**: Fixed broken chain where historical ELO used different formula than Lambda pipeline
- **Correction**: Average |diff| = 62.39 ELO points across 30 teams from old values
