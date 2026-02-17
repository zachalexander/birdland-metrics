# The 2026 Offseason Through Two Lenses: Historical WAR vs. Marcel Projections

How you measure an offseason depends entirely on which direction you're looking. Backward at what a player did, or forward at what a player is likely to do?

A team that signs a 35-year-old coming off a career year looks brilliant in the rearview mirror. A team that bets on a 25-year-old with a modest track record might look underwhelming by the same standard. Neither view is wrong, but neither tells the whole story.

This analysis runs every 2025-26 offseason transaction through two WAR frameworks and blends them into a single composite. The result is a more honest accounting of which teams actually improved their rosters heading into 2026.

---

## Methodology

### Historical WAR

The baseline: a simple three-year average of FanGraphs fWAR (2023-2025) for every player involved in a roster-changing transaction. This is the same approach the Birdland Metrics ELO model has used in previous seasons. It rewards track record, penalizes decline, and treats every season equally.

### Marcel Projected WAR

The projection layer uses a Marcel-style forecast, the transparent baseline system designed by sabermetrician Tom Tango. Three components:

1. **Recency weighting (5/4/3):** The most recent season counts 42% more than the oldest. A player who broke out in 2025 gets more credit than one who peaked in 2023.

2. **Regression to the mean:** The system pulls every player toward replacement-level based on playing time. A batter with 600 PA of data retains more of his WAR signal than one with 200 PA. Pitchers regress harder (baseline of 400 IP) because pitching performance is inherently more volatile.

3. **Age curve:** Players under 28 get a modest boost (+0.1 WAR per year of youth, capped at +0.5). Players over 28 get a symmetric penalty. This captures the well-documented aging curve without overreacting to any single birthday.

### Prospect and International Player Overrides

Marcel projections require MLB statistical history, which leaves a blind spot for NPB/KBO signings, top prospects, and international free agents. To address this, the pipeline accepts a manual override file with two modes:

- **Direct WAR estimates** for international signings, based on foreign league performance and standard translation factors (roughly 0.5-0.6x for NPB-to-MLB WAR, harsher for KBO)
- **Prospect ranking conversions** using historical prospect-to-MLB production rates (a top-5 prospect averages ~2.0 first-year WAR, top-50 ~0.7, top-100 ~0.4)

This year's overrides include Tatsuya Imai (2.0), Munetaka Murakami (1.9), Kazuma Okamoto (1.8), Alek Manoah (1.0), and 10 other prospects and international signings. Without these adjustments, teams like Houston and Chicago (AL) would be significantly understated.

### The Blend

The final "blended" WAR is a 50/50 mix of historical and projected. This deliberately balances what happened with what's likely to happen, and the differences between the two lenses are often more interesting than the blend itself.

---

## The Big Board

All 30 teams ranked by blended net WAR, with the historical and projected views alongside for comparison.

| Rank | Team | Division   | Net Historical | Net Projected | Net Blended |
|-----:|------|------------|---------------:|--------------:|------------:|
|    1 | BAL  | AL East    |          +8.2  |         +2.6  |       +5.5  |
|    2 | PIT  | NL Central |          +5.3  |         +2.3  |       +3.9  |
|    3 | COL  | NL West    |          +5.3  |         +1.8  |       +3.5  |
|    4 | SF   | NL West    |          +4.8  |         +1.5  |       +3.2  |
|    5 | LAD  | NL West    |          +3.1  |         +1.0  |       +2.0  |
|    6 | DET  | AL Central |          +2.7  |         +1.3  |       +1.9  |
|    7 | ATH  | AL West    |          +2.4  |         +0.7  |       +1.5  |
|    8 | MIA  | NL East    |          +1.5  |         +0.7  |       +1.1  |
|    9 | AZ   | NL West    |          +1.7  |         +0.6  |       +1.1  |
|   10 | CWS  | AL Central |          -0.1  |         +1.8  |       +0.9  |
|   11 | ATL  | NL East    |          +2.5  |         -0.7  |       +0.9  |
|   12 | MIN  | AL Central |          +1.2  |         +0.2  |       +0.7  |
|   13 | BOS  | AL East    |          -0.2  |         +0.3  |       +0.1  |
|   14 | TOR  | AL East    |          -1.1  |         +0.8  |       -0.2  |
|   15 | CIN  | NL Central |          -0.8  |         +0.0  |       -0.3  |
|   16 | TB   | AL East    |          -0.9  |         -0.5  |       -0.7  |
|   17 | KC   | AL Central |          -1.0  |         -0.4  |       -0.7  |
|   18 | LAA  | AL West    |          -1.4  |         +0.0  |       -0.7  |
|   19 | WSH  | NL East    |          -1.8  |         +0.0  |       -0.8  |
|   20 | CLE  | AL Central |          -1.7  |         -0.2  |       -1.0  |
|   21 | NYY  | AL East    |          -2.6  |         -0.3  |       -1.4  |
|   22 | NYM  | NL East    |          -2.2  |         -0.8  |       -1.5  |
|   23 | SEA  | AL West    |          -3.6  |         -1.6  |       -2.6  |
|   24 | MIL  | NL Central |          -6.2  |         -1.4  |       -3.8  |
|   25 | CHC  | NL Central |          -6.0  |         -2.0  |       -4.0  |
|   26 | HOU  | AL West    |          -8.6  |         -0.4  |       -4.6  |
|   27 | TEX  | AL West    |          -7.8  |         -1.3  |       -4.6  |
|   28 | PHI  | NL East    |          -8.2  |         -1.7  |       -4.9  |
|   29 | SD   | NL West    |          -8.7  |         -1.9  |       -5.3  |
|   30 | STL  | NL Central |         -12.7  |         -3.8  |       -8.2  |

Baltimore wins the offseason no matter how you measure it. St. Louis loses it no matter how you measure it. But the interesting action is in the middle, where the two lenses tell meaningfully different stories.

---

## Where the Lenses Disagree

The gap between historical and projected net WAR reveals which teams are being flattered or punished by backward-looking analysis.

### Historical Overstates the Losses

| Team | Net Historical | Net Projected | Gap  |
|------|---------------:|--------------:|-----:|
| STL  |         -12.7  |         -3.8  | -8.9 |
| HOU  |          -8.6  |         -0.4  | -8.2 |
| SD   |          -8.7  |         -1.9  | -6.8 |
| TEX  |          -7.8  |         -1.3  | -6.5 |
| PHI  |          -8.2  |         -1.7  | -6.5 |

St. Louis looks catastrophic through the historical lens: losing Sonny Gray (4.3 historical WAR), Willson Contreras (2.8), Brendan Donovan (2.5), and Nolan Arenado (2.3) adds up to a franchise teardown. But the projection system sees aging players with diminishing returns. Gray's Marcel projection is 1.3 WAR, not 4.3. Arenado projects at 0.7, not 2.3. The Cardinals still had the worst offseason in baseball, but the damage is closer to -3.8 projected WAR than -12.7 historical.

Houston's story is the most dramatic divergence. Historically, the Astros lost -8.6 net WAR. But the projected view sees it as just -0.4 — nearly flat. The difference comes from two directions: the players Houston lost (Framber Valdez, Mauricio Dubon, Victor Caratini) are mostly aging and due for regression, and the players they added — headlined by Tatsuya Imai's projected 2.0 WAR — are invisible to the historical lens but real to the projection system. If Imai pitches to his NPB translation, Houston's offseason looks far less grim than the headlines suggest.

### Historical Overstates the Gains

| Team | Net Historical | Net Projected | Gap  |
|------|---------------:|--------------:|-----:|
| BAL  |          +8.2  |         +2.6  | +5.6 |
| COL  |          +5.3  |         +1.8  | +3.5 |
| SF   |          +4.8  |         +1.5  | +3.3 |
| ATL  |          +2.5  |         -0.7  | +3.2 |

Baltimore's offseason is genuinely strong, but the historical WAR inflates it. Pete Alonso's 2.8 historical average drops to a 1.1 projection. Chris Bassitt goes from 2.4 to 0.7. The Orioles still added real talent, and their +2.6 projected net is the best in baseball. But the headline +8.2 historical number overstates the expected on-field impact.

Atlanta is the most interesting case. The Braves show +2.5 net historical WAR but -0.7 projected — the only team in the top half of the historical rankings that flips negative on projection. They acquired established veterans whose track records look impressive but whose forward outlooks are modest. If the projections are right, Atlanta's offseason was closer to a step backward than a significant upgrade.

### The Murakami Effect

The most dramatic single-player impact on the projection side belongs to the White Sox. Chicago's historical net WAR is -0.1, a rounding error of a loss. But their projected net is +1.8, the fourth-best in baseball. The reason: Munetaka Murakami's 1.9 projected WAR (based on his NPB track record as a former Triple Crown winner and 56-homer slugger) has no historical MLB component. The signing of the 26-year-old first baseman is worth essentially nothing to the backward-looking lens but represents a substantial projected upgrade. Add in Erick Fedde (1.06 blended) and Luisangel Acuna (0.40 blended), and the White Sox quietly assembled a +0.9 blended offseason while most people were writing them off.

---

## Division Breakdown

### AL East

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| BAL  |    +8.2 |     +2.6 |      +5.5 |
| BOS  |    -0.2 |     +0.3 |      +0.1 |
| TOR  |    -1.1 |     +0.8 |      -0.2 |
| NYY  |    -2.6 |     -0.3 |      -1.4 |
| TB   |    -0.9 |     -0.5 |      -0.7 |

**Division average: +0.7 blended WAR**

Baltimore dominated the division's offseason. The Orioles added Pete Alonso (1.95 blended), Taylor Ward (1.60), Chris Bassitt (1.59), and re-signed Zach Eflin (1.55) while losing Grayson Rodriguez (1.20) in trade. Toronto's Kazuma Okamoto signing (1.8 projected) and Dylan Cease acquisition pushed their projection into positive territory even as the historical view stayed negative. The Yankees added Cody Bellinger but lost more than they gained.

### AL Central

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| DET  |    +2.7 |     +1.3 |      +1.9 |
| CWS  |    -0.1 |     +1.8 |      +0.9 |
| MIN  |    +1.2 |     +0.2 |      +0.7 |
| KC   |    -1.0 |     -0.4 |      -0.7 |
| CLE  |    -1.7 |     -0.2 |      -1.0 |

**Division average: +0.4 blended WAR**

The division's story changed dramatically once NPB signings were factored in. Detroit's Framber Valdez signing (2.66 blended WAR) remains the headline, but the White Sox's Munetaka Murakami acquisition (1.90 blended) flipped Chicago from a net loser to the division's second-best offseason. Cleveland quietly slipped, losing modest contributors without replacing them.

### AL West

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| ATH  |    +2.4 |     +0.7 |      +1.5 |
| AZ   |    +1.7 |     +0.6 |      +1.1 |
| LAA  |    -1.4 |     +0.0 |      -0.7 |
| TEX  |    -7.8 |     -1.3 |      -4.6 |
| HOU  |    -8.6 |     -0.4 |      -4.6 |
| SEA  |    -3.6 |     -1.6 |      -2.6 |

**Division average: -2.2 blended WAR**

Still the worst division offseason in baseball, but less catastrophic than the historical numbers alone suggest. Houston's -8.6 historical loss shrinks to -4.6 blended once Tatsuya Imai (2.0 WAR) and Joey Loperfido (0.5) are factored in alongside regression applied to the departed veterans. The Angels' Alek Manoah signing (1.0 WAR override for the former Cy Young contender returning from elbow surgery) moved LA from -1.7 blended to -0.7. The Athletics were the division's clear winners, continuing to add pieces as they settle into Sacramento.

### NL East

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| MIA  |    +1.5 |     +0.7 |      +1.1 |
| ATL  |    +2.5 |     -0.7 |      +0.9 |
| WSH  |    -1.8 |     +0.0 |      -0.8 |
| NYM  |    -2.2 |     -0.8 |      -1.5 |
| PHI  |    -8.2 |     -1.7 |      -4.9 |

**Division average: -1.0 blended WAR**

Philadelphia's offseason churn produced the division's biggest net loss. The Phillies re-signed Kyle Schwarber (2.14 blended) and J.T. Realmuto (1.32) but lost Ranger Suarez (2.09), Harrison Bader (1.15), and Matt Strahm (1.07). The re-signings cancel out in the net calculation since both the gain and loss are counted, making Philly's departures the dominant factor. Miami's Owen Caissie acquisition (0.7 WAR prospect override) and other pieces pushed the Marlins to the division's best offseason, an unusual place for that franchise.

### NL Central

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| PIT  |    +5.3 |     +2.3 |      +3.9 |
| CIN  |    -0.8 |     +0.0 |      -0.3 |
| MIL  |    -6.2 |     -1.4 |      -3.8 |
| CHC  |    -6.0 |     -2.0 |      -4.0 |
| STL  |   -12.7 |     -3.8 |      -8.2 |

**Division average: -2.5 blended WAR**

The NL Central had the second-worst division offseason. St. Louis's fire sale is the story: losing Sonny Gray (2.76 blended), Willson Contreras (1.78), Brendan Donovan (1.67), Nolan Arenado (1.46), and Miles Mikolas (1.09) with only Dustin May (0.62 blended) arriving. Pittsburgh posted the second-best offseason in baseball, boosted by Mason Montgomery's projection (0.5 WAR from his elite stuff) alongside the established players they acquired.

### NL West

| Team | Net Hist | Net Proj | Net Blend |
|------|--------:|---------:|----------:|
| COL  |    +5.3 |     +1.8 |      +3.5 |
| SF   |    +4.8 |     +1.5 |      +3.2 |
| LAD  |    +3.1 |     +1.0 |      +2.0 |
| AZ   |    +1.7 |     +0.6 |      +1.1 |
| SD   |    -8.7 |     -1.9 |      -5.3 |

**Division average: +0.9 blended WAR**

The best division offseason, dragged down only by San Diego's talent drain. The Padres lost Dylan Cease (2.55 blended), Ryan O'Hearn (1.33), and Luis Arraez (1.18) while Sung-Mun Song's KBO-translated 0.8 WAR was the only notable addition. The Dodgers signed Kyle Tucker (the single biggest blended gain in baseball). Colorado's Tomoyuki Sugano (0.5 WAR at Coors, discounted from his Baltimore production) adds a modest piece to their surprisingly productive winter. San Francisco's Daniel Susac acquisition (0.4 WAR prospect conversion) further boosted an already strong offseason.

---

## What This Means for 2026

The blended WAR framework feeds directly into the Birdland Metrics ELO model at a rate of 5.5 ELO points per 1.0 WAR. Baltimore's +5.5 blended net WAR translates to roughly +30 ELO points of preseason adjustment, the largest positive shift in the league. St. Louis absorbs a -45 point penalty.

The projection component matters most for the teams at the extremes. Without it, Baltimore's offseason would add +45 ELO instead of +30. St. Louis would drop -70 instead of -45. The Marcel regression to the mean is doing real work, tempering the most dramatic narratives with a dose of expected-performance reality.

Four things to watch as the season unfolds:

1. **Baltimore's veteran additions.** Pete Alonso, Chris Bassitt, and Zach Eflin are all 30+ with historical WAR well above their projections. If they perform closer to their track records than their Marcel forecasts, the Orioles have a legitimate dynasty-tier roster.

2. **The NPB wave.** Tatsuya Imai (HOU), Munetaka Murakami (CWS), and Kazuma Okamoto (TOR) collectively represent 5.7 projected WAR that didn't exist in the historical lens. Their MLB transitions will be the ultimate test of whether the translation factors hold. If Murakami's power plays in the majors the way it did in NPB, the White Sox rebuild timeline accelerates dramatically.

3. **St. Louis's projected floor.** The Cardinals' losses look apocalyptic historically but merely bad in projection. If the players they lost decline on schedule while the remaining core holds steady, St. Louis's 2026 may be disappointing but not catastrophic.

4. **The AL West vacuum.** Houston and Texas both shed significant WAR, and the division's -2.2 average blended loss is the worst in baseball. But Houston's projected loss is just -0.4 — almost nothing — entirely because the historical view can't see Imai. If Imai pitches like a mid-rotation starter, the Astros' retool looks much smarter than the teardown narrative suggests.

---

*Data sources: MLB Stats API (transactions), FanGraphs (fWAR via pybaseball), Chadwick Register (player ID mapping), NPB/KBO translation factors, MLB Pipeline prospect rankings. Marcel projection methodology per Tom Tango. Analysis generated February 2026.*
