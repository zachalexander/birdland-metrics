# Why Our ELO Model Disagrees with FanGraphs Projections

## Article Idea / Explainer Draft

---

## The Observation

Birdland Metrics projects the 2026 Yankees at 97 wins and the Orioles at 85 — a 12-game gap. FanGraphs has these teams much closer together. Why?

## The Numbers

### End-of-2025 ELO Baseline (before preseason adjustments)

| Team | Raw ELO | Diff from 1500 |
|------|---------|----------------|
| NYY  | 1675.6  | +175.6         |
| BOS  | 1622.4  | +122.4         |
| TOR  | 1615.4  | +115.4         |
| BAL  | 1510.3  | +10.3          |
| TB   | 1493.9  | -6.1           |

The raw 2025 season results left a **165-point** ELO gap between NYY and BAL.

### After Preseason WAR Adjustments

The model adjusts ELO for offseason roster changes using a WAR-based system (3-year weighted WAR, 5.5 ELO per 1 WAR of roster change):

| Team | WAR Adj | ELO Adj | New ELO | Proj W |
|------|---------|---------|---------|--------|
| NYY  | -7.6    | -41.9   | 1633.7  | 97     |
| BOS  | -3.9    | -21.5   | 1600.9  | 92     |
| TOR  | -4.1    | -22.5   | 1592.9  | 91     |
| BAL  | +7.3    | +40.2   | 1550.5  | 85     |
| TB   | -4.7    | -25.7   | 1468.2  | 71     |

The adjustment cut the NYY-BAL gap from 165 to 83 points, but an 83-point gap still drives a ~12-win projected difference.

---

## How Our Model Works

Birdland Metrics uses an **ELO rating system** enhanced with:

1. **Base ELO** (K=20, HFA=55, log margin-of-victory): Team-level ratings updated after every game, carrying forward season to season with offseason reversion to the mean.
2. **Starting pitcher FIP adjustment** (+50 ELO per 1.0 FIP below league average): Shifts game-level win probability based on starting pitching matchup.
3. **Probability shrinkage** (0.16): Pulls all predictions toward 50/50, reflecting the inherent unpredictability of individual baseball games.
4. **Preseason WAR adjustment**: Uses MLB Stats API transaction data to compute net WAR gained/lost per team during the offseason, translating roster changes into ELO shifts before Opening Day.
5. **Monte Carlo simulation**: 10,000 season simulations using the adjusted ELO + FIP model to produce win distributions and playoff odds.

### Key characteristic: **The model is fundamentally backward-looking.**

ELO ratings are a rolling summary of how teams have actually performed. A team's 2026 projection is anchored to their 2025 results, modified only by:
- Offseason roster changes (WAR adjustment)
- Starting pitcher quality (FIP, once the season starts)
- Game-by-game results updating ELO during the season

---

## How FanGraphs Works

FanGraphs projections (ZiPS and Steamer) are **player-level, forward-looking** systems:

1. **Individual player projections**: Each player gets a projected stat line based on their historical performance, aging curves, and regression to the mean.
2. **Playing time estimates**: Projected plate appearances and innings pitched per player, accounting for depth charts, platoon splits, and injury history.
3. **Aging curves**: Young players are projected to improve; older players to decline. This is baked into each individual projection.
4. **Regression to the mean**: Both extreme good and bad performances are regressed. A player who hit .340 is projected lower; a player who hit .220 with strong underlying metrics is projected higher.
5. **Team-level aggregation**: Individual projections are summed to produce team WAR totals, which are converted to projected win totals.

### Key characteristic: **The model is fundamentally forward-looking.**

FanGraphs doesn't care (as much) about a team's 2025 win-loss record. It cares about the projected talent on the 2026 roster.

---

## Why They Diverge: The Orioles Case Study

### Scenario: BAL had a disappointing 2025

If the Orioles finished 2025 with, say, 78 wins despite having a talented young roster, here's how each system reacts:

**Our ELO model:**
- BAL's ELO drops to 1510 based on actual 2025 results
- Preseason adjustment adds +40 ELO for offseason acquisitions
- But the 78-win season is still the dominant signal — ELO doesn't distinguish between "bad luck" and "bad team"
- Projected for ~85 wins in 2026

**FanGraphs:**
- Individual players projected based on talent, not team record
- Gunnar Henderson projected for 6+ WAR regardless of 2025 team record
- Young arms projected to improve along aging curves
- Playing time estimates based on depth chart, not 2025 usage
- Could project 88-92 wins based purely on roster talent

### The gap comes from:

| Factor | Our Model | FanGraphs |
|--------|-----------|-----------|
| Unit of analysis | Team | Individual player |
| Primary signal | 2025 W-L record | Player skill projections |
| Luck adjustment | None (outcomes = signal) | Regression to the mean |
| Aging/development | Not captured | Explicit aging curves |
| Injury recovery | Not captured | Playing time projections |
| Internal prospects | Not captured | Projected based on minor league stats |
| Roster depth | Not captured | Full depth chart modeled |
| Offseason moves | WAR-based ELO shift | Player-level additions/subtractions |

---

## The Blue Jays Case Study: A World Series Team Stuck in Third

Toronto made the 2025 World Series, yet our model projects them third in the AL East at 91 wins — behind the Yankees (97) and Red Sox (92). How can a team that just played in October's biggest stage be projected behind teams that didn't?

The answer is **ELO's multi-year memory**. A single season — no matter how good — can't fully erase the prior baseline:

| Team | End of 2024 ELO | 2025 Change | End of 2025 ELO | WAR Adj | Current ELO |
|------|-----------------|-------------|-----------------|---------|-------------|
| NYY  | 1553.4          | +122.2      | 1675.6          | -41.9   | 1633.7      |
| BOS  | 1499.3          | +123.2      | 1622.4          | -21.5   | 1600.9      |
| TOR  | 1466.1          | +149.3      | 1615.4          | -22.5   | 1592.9      |
| BAL  | 1536.3          | -26.0       | 1510.3          | +40.2   | 1550.5      |
| TB   | 1559.2          | -65.4       | 1493.9          | -25.7   | 1468.2      |

Toronto's 2025 gain of **+149.3 ELO points** was the biggest jump in the division — the kind of surge you'd expect from a World Series run. But they started 2025 from a deep hole: an end-of-2024 ELO of just 1466.1, the **lowest in the AL East** after a disappointing 2024 season.

Meanwhile, the Yankees entered 2025 already at 1553 and still gained +122 points on top of that. They were compounding from a higher base. The gap between NYY and TOR narrowed across 2025, but it didn't close:

- **End of 2024**: NYY 87 points ahead of TOR
- **End of 2025**: NYY 60 points ahead (gap narrowed by 27)
- **After WAR adjustments**: NYY 41 points ahead (gap narrowed further)

That remaining 41-point gap translates to roughly 6 projected wins — which is the difference between 97 and 91 in our projections.

### Why FanGraphs would see it differently

FanGraphs doesn't penalize Toronto for 2024. A player-level system would:
- Project each Blue Jay based on individual talent and aging curves
- Give full credit for the roster that made the World Series run
- Not discount their projections because of a season that's now two years in the past

ELO, by contrast, carries the scar of 2024 forward. With K=20, it takes sustained winning over multiple seasons to fully rebuild a rating. One great year significantly improves the rating (TOR gained more than anyone), but it can't fully compensate for starting from the bottom of the division.

### The broader lesson

This is ELO's **recency bias paradox**: the system is designed to weight recent results heavily (that's why K=20 makes it responsive), but "recent" still means the cumulative history, not just the last season. A team needs **consecutive strong seasons** to reach the top of the ratings. One breakout year moves the needle dramatically — Toronto's +149 gain proves that — but it doesn't erase history entirely.

---

## The Yankees Case Study

The flip side: if NYY had a dominant 2025 (95+ wins), our model gives them a very high baseline ELO. But FanGraphs might see:

- Aging stars projected to decline (aging curves pulling WAR down)
- Bullpen regression toward the mean after a historically good season
- Key players whose 2025 stats exceeded their true talent level
- Less prospect depth compared to younger rosters

The result: FanGraphs pulls NYY down while our model keeps them high.

---

## Which Is More Accurate?

Neither is definitively "better" — they capture different information:

**ELO strengths:**
- Captures intangibles: clubhouse chemistry, managerial strategy, park effects, and other factors that are hard to quantify at the player level
- Self-correcting during the season: game results update ELO in real-time
- Simple and transparent: one number per team, easy to understand
- No individual player data needed — fully automated

**ELO weaknesses:**
- Can't distinguish luck from skill in team records
- Slow to react to roster overhauls (WAR adjustment helps but is coarse)
- No player development/aging model
- Preseason projections heavily anchored to prior year's results

**FanGraphs strengths:**
- Forward-looking: projects what teams *should* do, not what they *did*
- Captures player-level nuance (aging, regression, injury)
- Better preseason projections (less anchored to prior year's record)

**FanGraphs weaknesses:**
- Playing time projections are inherently uncertain
- Doesn't capture team-level synergies or chemistry
- Projection systems disagree with each other (ZiPS vs Steamer)
- More complex, less transparent

---

## What This Means for Birdland Metrics

Our model is at its **weakest** in the preseason, when ELO is entirely backward-looking and hasn't had a chance to update from 2026 game results. As the season progresses:

- ELO adjusts game-by-game, gradually incorporating 2026 performance
- Starting pitcher FIP captures pitching matchup quality
- By mid-season, the model's ELO reflects a blend of 2025 baseline + 2026 results
- By September, 2026 performance dominates the signal

**The model will naturally converge toward reality as the season unfolds.** The preseason projections should be viewed as a starting point, not a prediction with high confidence.

---

## Possible Article Angles

1. **"Why Our Model Loves the Yankees (And You Shouldn't Worry)"** — Explainer about ELO's backward-looking nature, with the promise that the model self-corrects during the season.

2. **"ELO vs. ZiPS: Two Ways to See the Same Division"** — Side-by-side comparison of AL East projections with detailed explanation of methodology differences.

3. **"The Preseason Problem"** — Broader piece about why all preseason projections are noisy, how ELO handles the offseason differently than player-level systems, and what to watch for as confidence intervals narrow.

4. **"How to Read Our Projections"** — Transparency piece explaining the model, its strengths/limitations, and why the confidence intervals (p10-p90) matter more than median wins in February.

---

## Data Points to Include in Article

- BAL 2025 actual record vs projected talent level
- NYY 2025 actual record and key contributors
- TOR 2024-2025 ELO trajectory: worst in division to World Series, still projected 3rd
- AL East ELO ratings across 2024 and 2025 (raw and adjusted) as a table/visualization
- Side-by-side: our projections vs FanGraphs projections for all 30 teams
- Historical backtest: how accurate was our model's preseason vs mid-season vs September projections?
- Interactive: ELO trajectory visualization showing how team ratings evolve from preseason through October

## Potential Visualizations

- **ELO waterfall chart**: Show raw end-of-2025 ELO → preseason WAR adjustment → current ELO for each AL East team
- **Multi-year ELO trajectory**: Line chart showing end-of-2024 → end-of-2025 → post-WAR-adjustment for each AL East team, highlighting how TOR climbed the most but started the lowest
- **Projection comparison scatter**: Our median wins (x-axis) vs FanGraphs projected wins (y-axis) for all 30 teams, with diagonal line showing agreement
- **Confidence interval comparison**: Side-by-side distribution curves for BAL and NYY showing p10-p90 ranges
- **Historical accuracy timeline**: Line chart showing model Brier score by month (April through October) demonstrating how accuracy improves as the season progresses
