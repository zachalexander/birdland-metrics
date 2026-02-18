# Behind the Numbers: How Birdland Metrics Projects the Orioles' Season

Every number on this site — the playoff odds, the projected standings, the win totals — comes from a single model that we built from scratch. No black boxes, no proprietary datasets, no borrowed projections. This article explains exactly how it works, what it does well, and where its blind spots are.

---

## The Short Version

Birdland Metrics uses an **ELO rating system** — the same type of system used to rank chess players — adapted for baseball and enhanced with several additional layers:

1. **ELO ratings** track team strength based on game results, updated daily
2. **Starting pitcher adjustments** shift each game's probability based on who's on the mound, with early-season Bayesian regression and a separate bullpen adjustment
3. **Probability calibration** corrects for ELO's tendency to be overconfident
4. **Preseason projections** blend mean-reverted ELO with team WAR forecasts, fading into in-season performance over the first 100 games
5. **In-season injury adjustments** penalize teams for WAR lost to the injured list
6. **Contextual game adjustments** account for park factors and cross-country travel

These layers feed into a **Monte Carlo simulation** that plays out the rest of the season 10,000 times, producing the playoff odds and win projections you see on the home page.

---

## Layer 1: ELO Ratings

### Every Team Gets a Number

Each of the 30 MLB teams carries an ELO rating — a single number that represents its current strength. The league average is 1500. A dominant team might sit around 1650-1700; a rebuilding team might drop to 1300-1350.

After every game, the winner gains ELO points and the loser drops by the same amount. The system is zero-sum: points don't appear out of thin air. Our ratings chain extends all the way back to 1871 — over 230,000 games — recomputed from scratch with one consistent formula.

### How ELO Predicts Games

Before each game, the model computes a win probability using the rating gap between the two teams, plus a home field advantage of **55 ELO points** (roughly equivalent to a 58% win probability for two evenly-matched teams at home, consistent with MLB's historical home winning percentage).

The formula is the standard logistic ELO equation:

> **P(home wins) = 1 / (1 + 10^((ELO_away - (ELO_home + 55)) / 400))**

In plain English: the bigger the ELO gap, the more confident the prediction. A 100-point advantage translates to roughly a 64% win probability.

### Blowouts Matter More

Not all wins are created equal. A 10-1 rout tells us more about team quality than a 3-2 walk-off. After each game, the rating shift is scaled by a **margin of victory multiplier** that uses a logarithmic formula:

> **MOV = log(|run_diff| + 1) x (2.2 / (0.001 x |elo_diff| + 2.2))**

The logarithm compresses extreme blowouts — a 15-run win isn't five times more informative than a 3-run win. The dampening term ensures that when a heavy favorite blows out a weak opponent, the ratings don't overreact (that result was expected).

| Run Differential | Rating Shift Multiplier (even matchup) |
|-----------------|---------------------------------------|
| 1 run | 0.69x |
| 3 runs | 1.10x |
| 5 runs | 1.31x |
| 10 runs | 1.56x |

---

## Layer 2: Starting Pitcher Adjustment

### The Problem ELO Can't Solve Alone

ELO captures how good a team is overall, but it's blind to who's pitching today. The Orioles send Corbin Burnes to the mound in one game and a back-end starter the next — their ELO is the same in both cases, even though their actual chances of winning are very different.

### FIP: The Pitching Metric That Matters

We use **FIP (Fielding Independent Pitching)** rather than ERA to evaluate starters. FIP strips out the noise of defense, sequencing luck, and batted ball variance, isolating the outcomes a pitcher directly controls: strikeouts, walks, hit-by-pitches, and home runs.

> **FIP = ((13 x HR) + (3 x (BB + HBP)) - (2 x K)) / IP + cFIP**

The **cFIP constant** anchors FIP to the league-wide ERA scale so that the average FIP equals the average ERA in any given season.

### Converting FIP to a Win Probability Shift

Before each game, we compare each starting pitcher's FIP to the league average. The difference is converted into an ELO adjustment at a rate of **50 ELO points per 1.0 FIP**:

> **adjustment = (league_FIP - pitcher_FIP) x 50**

A pitcher with a FIP one full point below league average (an ace) adds 50 ELO points to their team's effective rating for that game. A pitcher one point above average (a struggling starter) subtracts 50 points.

To put this in context with real pitchers:

| Pitcher | FIP | Adjustment |
|---------|-----|------------|
| Elite ace (2.35 FIP) | 2.35 | +90 ELO pts |
| League average | ~4.15 | 0 |
| Back-end starter (6.05 FIP) | 6.05 | -95 ELO pts |

That's a swing of nearly 185 ELO points — or roughly the gap between a 95-win team and a 75-win team — based solely on who's pitching. The starting pitcher is the single most impactful per-game variable in baseball, and FIP captures it cleanly.

When a starting pitcher hasn't been announced or has no FIP data yet, the model simply assigns league-average FIP (zero adjustment), falling back to the raw ELO prediction.

### Early-Season Regression: Bayesian FIP

A pitcher who has thrown 8 innings in April with a 1.50 FIP isn't suddenly an all-time great — we just don't have enough data yet. To guard against small-sample noise, the model applies **Bayesian regression** that blends a pitcher's observed FIP with the league average, weighted by innings pitched:

> **regressed_FIP = (pitcher_IP x raw_FIP + 50 x league_FIP) / (pitcher_IP + 50)**

The **50-inning prior** acts as a stabilizer. Early in the season, when a pitcher has only 10-15 IP, the regressed FIP leans heavily toward the league average. By mid-season, with 100+ IP, the prior is overwhelmed by the pitcher's actual performance.

| Innings Pitched | Weight on Observed FIP | Weight on League Average |
|----------------|----------------------|------------------------|
| 10 IP | 17% | 83% |
| 30 IP | 38% | 62% |
| 50 IP | 50% | 50% |
| 100 IP | 67% | 33% |
| 180 IP | 78% | 22% |

This prevents the model from making wild bets on pitchers with tiny sample sizes, while still rewarding sustained performance as the season progresses.

### Bullpen Adjustment

Starting pitchers throw roughly 5-6 innings per game. The bullpen handles the rest — and in modern baseball, that's often 3-4 innings of high-leverage work. Ignoring the bullpen leaves a meaningful gap in the model.

We compute a team-level bullpen FIP from the collective performance of each team's relief corps and apply a separate adjustment at a rate of **15 ELO points per 1.0 FIP** difference from the league bullpen average:

> **bullpen_adjustment = (league_bullpen_FIP - team_bullpen_FIP) x 15**

The weight is deliberately lower than the starter adjustment (15 vs. 50) for two reasons: bullpen usage is less predictable game-to-game, and team bullpen FIP is an aggregate of many arms rather than a single identifiable pitcher. Still, a team with an elite bullpen (1.0 FIP below average) gets a meaningful +15 ELO point boost, while a team running out a shaky pen absorbs a corresponding penalty.

---

## Layer 3: Probability Calibration

### ELO Has an Overconfidence Problem

Raw ELO probabilities are systematically too extreme. When the model says a team has a 70% chance of winning, they historically win closer to 64% of the time. This is a known property of ELO systems — the math maps rating differences to probabilities more aggressively than real-world outcomes justify.

### The Fix: Shrinkage

We apply a simple linear compression that pulls all probabilities toward 50%:

> **P_adjusted = 0.16 + (1 - 2 x 0.16) x P_raw**

This means the model never predicts any team has less than a 16% chance — or more than an 84% chance — of winning any individual game. That floor reflects the inherent unpredictability of baseball: even the worst team in the league beats the best team roughly one in six times.

| Raw Prediction | After Calibration | Change |
|---------------|------------------|--------|
| 80% | 70.4% | -9.6 points |
| 70% | 63.6% | -6.4 points |
| 60% | 56.8% | -3.2 points |
| 50% | 50.0% | unchanged |

### Why 0.16?

The shrinkage parameter was optimized through a grid search across 150 parameter combinations, evaluated across three full MLB seasons (2023-2025). Surprisingly, this simple calibration is the single most impactful enhancement in the entire model — it improved prediction quality more than the starting pitcher adjustment.

---

## Layer 4: Preseason Projection

### The Offseason Changes Everything

ELO ratings carry over from the prior season, but rosters can transform over the winter. A team that loses star players in free agency and replaces them with a mix of veterans and prospects enters the season measurably different — but ELO has no way to know this until enough new games are played for the rating to "catch up."

### Two Signals, One Preseason Rating

Before Opening Day, the model constructs a preseason ELO for each team by blending two independent signals:

**Signal 1: Mean-Reverted ELO.** End-of-season ELO ratings overstate the gap between the best and worst teams because some of that gap is luck. Before carrying ratings into the new season, the model regresses every team **40% toward the league average** of 1500:

> **mean_reverted = 0.6 × end_of_season_elo + 0.4 × 1500**

A team that finished at 1650 starts the new season anchored at 1590. A team at 1350 moves up to 1410. This compression reflects the historical tendency for teams to regress toward the middle — last year's best team rarely stays the best, and last year's worst team rarely stays the worst. An additional spread compression factor of **0.75** further tightens the ratings, preventing any single dominant team from distorting the preseason landscape.

**Signal 2: Team WAR.** WAR (Wins Above Replacement) measures total roster talent on a single scale. A team with 48 WAR has a roster roughly 9 wins better than a 39-WAR team, all else equal.

For the current season, we use **FanGraphs projected WAR** from their depth chart projections — pre-season forecasts that account for aging curves, injury risk, and expected playing time. Each team's WAR is converted to an ELO-scale rating centered on 1500:

> **war_elo = 1500 + (team_war - league_average_war) × 5.0**

A team with WAR 8 points above the league average gets a WAR-based ELO of 1540. A team 8 points below gets 1460.

**Blending the signals.** The final preseason ELO is a **50/50 blend** of the two signals:

> **preseason_elo = 0.5 × war_elo + 0.5 × mean_reverted_elo**

This blending is deliberate. Mean-reverted ELO carries information about organizational quality, coaching, and intangibles that WAR doesn't capture. WAR captures roster talent that end-of-season ELO hasn't yet processed — particularly offseason moves. Neither signal is sufficient on its own; the blend outperforms either individually in backtesting.

### 2026 Example

Using FanGraphs projected WAR for the 2026 season:

| Team | Projected WAR | Mean-Reverted ELO | WAR ELO | Preseason ELO |
|------|--------------|-------------------|---------|---------------|
| LAD | 56.6 | 1611 | 1586 | 1577 |
| NYY | 47.5 | 1605 | 1540 | 1558 |
| TOR | 48.0 | 1569 | 1543 | 1545 |
| BAL | 45.4 | 1506 | 1530 | 1516 |
| DET | 44.3 | 1486 | 1524 | 1507 |
| COL | 23.1 | 1376 | 1418 | 1426 |

Notice how the blend works in practice: The Dodgers start highest because they combine a strong 2025 ELO with the league's best projected roster. Detroit's projected WAR (44.3, 10th in MLB) pulls their preseason rating *up* from a below-average 2025 ELO, reflecting their improved roster. Colorado's combination of weak prior results and the league's lowest projected WAR puts them at the bottom.

### Fading Into the Season

The preseason ELO doesn't persist all year. As games are played, the model gradually shifts from the preseason anchor toward each team's in-season ELO:

> **effective_elo = (games_played / 100) × current_elo + (1 - games_played / 100) × preseason_elo**

For the first game of the season, the effective rating is almost entirely the preseason ELO. By game 50 (late May), it's a 50/50 mix. By game 100 (early July), the preseason signal has fully faded and the model relies entirely on current performance.

The fade rate of **100 games** was determined through backtesting across the 2024 and 2025 seasons, testing fade values from 0 (no preseason influence) to 300 (preseason persists deep into September). A 100-game fade produced the best early-season prediction accuracy while allowing the model to fully adapt by the second half.

### Limitations We're Transparent About

- **Historical seasons use prior-year WAR**, not projected WAR (which doesn't exist for past seasons). The backfill for 2024 and 2025 uses actual WAR totals from the prior year plus offseason transaction adjustments as a proxy.
- **Projected WAR isn't perfect.** FanGraphs projections are the best publicly available forecast, but they still miss on players who break out or collapse unexpectedly.
- **Prospects and minor leaguers** with no MLB track record receive no WAR credit. Teams adding top prospects via trade get no preseason boost until those players accumulate MLB stats.

---

## Layer 5: In-Season Injury Adjustment

### Injuries Change the Math

A team's ELO rating reflects its results with a full roster. But when a key player lands on the injured list, the team that takes the field is measurably weaker than the one that earned those wins. The model accounts for this by applying a **WAR-based penalty** for every player currently on the IL.

### How It Works

Each day, the model pulls the current injured list for every team. For each IL player, it looks up that player's WAR — using current-season data when available, falling back to the prior season for players injured early in the year. The total WAR on the IL is converted to an ELO penalty:

> **injury_penalty = -1 x total_IL_WAR x 5.5**

This penalty is applied to the team's effective ELO rating at projection time — it doesn't permanently alter the base rating. When a player returns from the IL, the penalty automatically disappears from the next day's projections.

| IL WAR Lost | ELO Penalty | Rough Win Impact |
|-------------|-------------|-----------------|
| 1.0 WAR | -5.5 pts | ~1 projected win |
| 3.0 WAR | -16.5 pts | ~3 projected wins |
| 5.0 WAR | -27.5 pts | ~5 projected wins |
| 10.0 WAR | -55 pts | ~10 projected wins |

A team that loses its ace and a star position player to the IL at the same time could easily be down 30-40 ELO points — enough to meaningfully shift their playoff odds.

### Only Positive WAR Counts

Players with zero or negative WAR don't generate a penalty when injured. Losing a replacement-level player to the IL doesn't weaken the team — the replacement's replacement performs about the same.

---

## Layer 6: Contextual Game Adjustments

Two smaller factors fine-tune individual game predictions:

### Park Factors

Not all ballparks are created equal. Coors Field inflates offense; Oracle Park suppresses it. The model scales FIP adjustments by each venue's park factor, so a pitcher's FIP at Coors is interpreted differently than the same FIP at Petco Park.

### Travel Penalty

Teams crossing two or more time zones eastward on road trips of 1,000+ miles receive a **10 ELO point penalty** for that game. Eastward travel disrupts circadian rhythms more than westward travel — a well-documented effect in sports science. The penalty is small but reflects a real, measurable disadvantage.

---

## Putting It All Together: Monte Carlo Simulation

### 10,000 Seasons, One Pipeline

Every day during the season, the model simulates the rest of the MLB schedule 10,000 times. For each remaining game in each simulation:

1. Look up both teams' current ELO ratings, adjusted for injuries
2. If starting pitchers are announced, apply their regressed FIP and bullpen adjustments
3. Apply park factors and travel penalties where applicable
4. Compute the calibrated win probability
5. Flip a (weighted) coin — if the random number falls below the probability, the home team wins that simulation

Each simulation produces a complete set of final standings. From 10,000 sets of standings, we extract:

- **Projected wins** — the median and distribution (including the 10th-to-90th percentile range you see on the site)
- **Playoff odds** — the percentage of simulations where a team finishes in the top 6 of their league
- **Division title odds** — how often they win their division outright
- **Wild card odds** — how often they make the playoffs as a wild card

### Why Monte Carlo?

A simple projection might say the Orioles will win 85 games. But what's the range? In how many of those 10,000 simulations do they win 90+? Or fall below 80? The distribution matters more than the point estimate, especially for a team sitting on the playoff bubble. A team projected for 85 wins with a wide range (78-92) has very different playoff odds than a team projected for 85 wins with a narrow range (82-88).

---

## Does It Actually Work?

We backtested the model across three full MLB seasons (2023-2025), with parameters tuned on 2025 and validated out-of-sample on 2023 and 2024.

| Season | Model | Accuracy | Log Loss |
|--------|-------|----------|----------|
| 2023 | Base ELO | 55.32% | 0.6921 |
| 2023 | **Enhanced** | **57.95%** | **0.6810** |
| 2024 | Base ELO | 55.23% | 0.6941 |
| 2024 | **Enhanced** | **56.72%** | **0.6830** |
| 2025 | Base ELO | 55.76% | 0.6868 |
| 2025 | **Enhanced** | **57.33%** | **0.6720** |
| **3-Season Average** | **Enhanced** | **57.33%** | **0.6787** |

The enhanced model picks the winner correctly about 57% of the time — nearly 2 percentage points better than raw ELO alone. That improvement held consistently across all three seasons, including the two that were never used during parameter tuning.

### The 57% Ceiling

If 57% sounds low, consider this: the best team in baseball wins about 60% of its games. A model that perfectly predicted true talent would still max out around 58-59% accuracy because of the irreducible randomness in baseball — injuries, umpiring, weather, and the fundamental reality that the best hitters in the world fail 70% of the time. At 57.33%, we're operating close to the theoretical ceiling for a pre-game prediction model.

For reference, a pure coinflip achieves 50% accuracy and a log loss of 0.693 (that's ln(2)). Our model's log loss of 0.679 may look like a small improvement in absolute terms, but in the world of probabilistic prediction, it represents meaningful and consistent edge.

---

## What to Know as a Reader

**The model is at its weakest in the preseason.** Before any 2026 games are played, the projections blend last season's ELO (regressed toward average) with FanGraphs projected WAR. The confidence intervals are widest in March and April.

**It self-corrects as the season unfolds.** Every game updates the ELO ratings, and the preseason anchor fades over the first 100 games (~early July). By mid-season, the model reflects current performance more than preseason projections. By September, current-season results are all that matter.

**The range matters more than the median.** A projection of "85 wins" with a 10th-to-90th percentile range of 78-92 means the model sees roughly an 80% chance the Orioles land somewhere in that 14-game window. The median is the most likely outcome, but the distribution tells you how confident the model is.

**Everything is transparent.** Every parameter, formula, and data source is documented. There are no hidden inputs or proprietary black boxes. If our model is wrong, you can trace exactly why.

---

## Parameter Quick Reference

| Parameter | Value | What It Does |
|-----------|-------|-------------|
| K-factor | 20 | How fast ELO reacts to each game result |
| Home field advantage | 55 pts | ELO boost for the home team |
| Margin of victory constant | 2.2 | Scales blowout impact on rating shifts |
| Starter FIP weight | 50 pts | ELO shift per 1.0 starter FIP below league average |
| Bullpen FIP weight | 15 pts | ELO shift per 1.0 bullpen FIP below league average |
| FIP regression prior | 50 IP | Innings of league-average prior for Bayesian FIP regression |
| Probability shrinkage | 0.16 | Compresses predictions toward 50/50 |
| Mean reversion | 40% | Fraction of end-of-season ELO regressed toward 1500 |
| Spread compression | 0.75 | Post-reversion tightening of ratings toward league average |
| WAR ELO factor | 5.0 pts | Preseason ELO points per 1.0 WAR above league average |
| WAR blend weight | 0.50 | Weight of WAR signal in preseason ELO (vs. mean-reverted ELO) |
| Preseason fade | 100 games | Games until preseason ELO fully gives way to in-season ELO |
| Injury WAR-to-ELO | 5.5 pts | ELO penalty per 1.0 WAR on the injured list |
| Travel penalty | 10 pts | ELO deduction for eastward cross-country travel |
| Simulations | 10,000 | Monte Carlo season simulations per daily run |
