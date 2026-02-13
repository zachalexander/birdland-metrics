# BAL Playoff-Odds Diagnostic

## Team Distribution
| Team | Mean Wins | Median | Std Dev | P10 | P90 | Unconditional Playoff% |
|---|---:|---:|---:|---:|---:|---:|
| BAL | 84.40 | 84 | 6.24 | 76 | 92 | 38.9% |

## Conversion Around Target Wins
| Scenario | Playoff% | Samples |
|---|---:|---:|
| Exactly 84 wins | 18.7% | 691 |
| Wins in [83, 85] | 20.8% | 1983 |
| Wins >= 84 | 67.5% | 5593 |

## AL East Context
| Team | Mean Wins | P10 | P90 | Playoff% |
|---|---:|---:|---:|---:|
| NYY | 97.21 | 89 | 105 | 95.5% |
| BOS | 91.98 | 84 | 100 | 83.4% |
| TOR | 90.46 | 82 | 99 | 73.7% |
| BAL | 84.40 | 76 | 92 | 38.9% |
| TB | 70.92 | 63 | 79 | 0.7% |

## Closest AL Wildcard Rivals (By Median Wins)
| Team | Median | P25 | P75 | Playoff% |
|---|---:|---:|---:|---:|
| ATH | 84 | 79 | 88 | 35.4% |
| KC | 90 | 86 | 94 | 73.8% |
| TOR | 90 | 86 | 95 | 73.7% |
| HOU | 77 | 73 | 81 | 7.5% |
| BOS | 92 | 88 | 96 | 83.4% |
| CLE | 92 | 88 | 97 | 85.3% |

## Around-Target Conversion Across AL
| Team | Playoff% when wins in [83, 85] | Samples |
|---|---:|---:|
| CLE | 35.8% | 755 |
| SEA | 35.5% | 304 |
| BOS | 30.9% | 812 |
| NYY | 28.9% | 211 |
| KC | 28.3% | 1177 |
| ATH | 22.8% | 1861 |
| TOR | 21.3% | 1122 |
| BAL | 20.8% | 1983 |
| CWS | 15.4% | 214 |
| TB | 12.9% | 202 |
| DET | 12.9% | 163 |
| HOU | 12.8% | 1075 |
| MIN | 10.7% | 898 |
| TEX | 9.3% | 854 |
| LAA | n/a | 0 |

## Interpretation
- If BAL has similar mean/median wins to another source but lower playoff odds, the gap usually comes from lower conversion at the target-win band because rival teams also cluster in that same win range.
- Inference: playoff odds are a joint race outcome, not a one-team win-total mapping.

## Reader-Friendly Takeaway (Article-Ready)
At first glance, "84 wins" sounds like a single number that should map cleanly to one playoff probability. But it does not work that way.

In this model, Baltimore lands on exactly 84 wins often (691 simulations), yet only makes the playoffs in 18.7% of those exact-84 seasons. The reason is traffic: too many AL teams are bunched in the same range, so 84 is often not enough to clearly separate from the wildcard crowd.

Think of it this way: wins are your ticket total, but playoff odds are your place in line. If several contenders end up with similar totals, the tiebreak and distribution of everyone else's outcomes matter as much as your own number.

That is why two models can agree on roughly 84 wins for Baltimore but still disagree on playoff odds. One model may produce a cleaner path around that win band; this one shows a more crowded AL race around the Orioles' median outcome.

Suggested short version:
"Our model and FanGraphs can both project ~84 wins, but playoff odds depend on the full AL traffic pattern. In our sims, the 83-85 win band is crowded, so Baltimore's conversion to a playoff spot is only about 21% in that range."

## Who Is Directly Competing With BAL?
Based on this simulation set, the biggest pressure on Baltimore's playoff odds comes from:

- AL East leaders: `NYY`, `BOS`, `TOR`
- Wild card overlap teams: `ATH`, `KC`, `CLE`, `SEA` (with `TOR` and `BOS` also affecting the wild card path when they do not win the division)

Why this lowers BAL's odds:
- Baltimore frequently lands in the 83-85 win range.
- Several AL contenders land in nearby ranges at the same time.
- That overlap creates a crowded wildcard race, so "84 wins" converts to a playoff berth less often than fans might expect.

## Pipeline Odds Check
| Team | Recomputed Playoff% | playoff-odds-latest.json | Delta |
|---|---:|---:|---:|
| BAL | 38.9% | 38.9% | +0.0 pts |
