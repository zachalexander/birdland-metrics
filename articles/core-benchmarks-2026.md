# The 33 Benchmarks That Will Define the Orioles' 2026 Season

The Orioles added more projected fWAR this offseason than any team in baseball. They signed Pete Alonso. They traded for Shane Baz and Taylor Ward. They brought in Ryan Helsley to close games and Chris Bassitt to eat innings. By FanGraphs' accounting, Baltimore gained 13.0 projected fWAR and lost just 3.6 — a net of +9.4, the best mark in the sport.

But projected WAR is an abstraction. It tells you what should happen in aggregate, not what needs to happen from the specific players who will determine whether this team wins 90 games or 80. For that, you need something more granular.

That's what our core benchmarks are. We've identified 33 specific, measurable targets across 11 players and units — six position players, four pitchers, and the bullpen as a whole. Each benchmark is drawn from the player's career data, projection systems, and the specific question their 2026 season needs to answer.

If the Orioles hit most of these benchmarks, they're a division contender. If they miss most of them, the offseason spending won't matter.

---

## How We Built the Benchmarks

Every benchmark follows the same structure: a stat, a threshold, and a direction. Barrel% >= 10%. ERA <= 3.50. K% <= 22%. Each one is designed to answer a single question about whether a player is performing at the level the Orioles need.

The targets aren't arbitrary. They come from three sources:

**Career baselines.** For returning players, we looked at what they've already shown they can do. Gunnar Henderson posted an 11.2% barrel rate in 2024 and 8.5% in 2025. The benchmark of 10% asks: is he closer to the MVP version or the merely-good version? Adley Rutschman's OBP target of .340 reflects his .365 mark in 2023 — we know the skill is there; the question is whether it shows up consistently.

**Projection systems.** ZiPS and Steamer project Henderson at roughly 6.0 fWAR, which implies a wRC+ in the 130-140 range. We set his target at 140 — the superstar threshold — because that's what the Orioles need from their best player, not just what the median projection suggests.

**Positional context.** Rutschman's wRC+ benchmark is 115, not 140, because above-average offensive production from the catcher position is a different standard than from shortstop. Pete Alonso's benchmarks are all power-focused because that's the specific skill Baltimore is paying for. Jackson Holliday's targets are deliberately modest — K% <= 25%, AVG >= .250 — because the question for a 22-year-old isn't whether he's a star yet, it's whether he belongs.

Each player gets exactly three benchmarks. Three is enough to capture the key dimensions of their contribution without diluting the signal. If a player hits all three, they're doing their job. If they hit zero, something has gone wrong.

### Data Pipeline

All benchmark data is sourced from FanGraphs via the pybaseball API. The pipeline pulls current-season batting and pitching leaderboards, matches each tracked player by name, and evaluates their stats against the predefined targets. For pace-based metrics — home run pace, innings pitched pace, games pace, saves pace — the raw counting stat is projected over a full 162-game season using the formula `(stat / games_played) * 162`. The pipeline also aggregates all Orioles relief pitchers to produce a composite bullpen line.

Results update automatically and are displayed on the home page with real-time pass/fail indicators.

---

## Position Players

### Gunnar Henderson — The Franchise

**Benchmarks:** Barrel% >= 10% | wRC+ >= 140 | HR pace >= 30

Henderson is the most important player on the roster and his benchmarks reflect the highest bar. The question isn't whether he's good — he has 18.2 career WAR at age 24 — it's which version of him shows up.

In 2024, Henderson was a top-5 WAR player in baseball: 37 home runs, .529 slugging, 154 wRC+, 7.9 fWAR. In 2025, the power disappeared. His barrel rate dropped from 11.2% to 8.5%. His ISO fell from .248 to .165. The home runs were cut in half to 17. But his exit velocity held steady at 92 mph, his strikeout rate continued its year-over-year decline to 21%, and he stole 30 bases. The raw tools didn't go anywhere — the approach shifted.

The barrel rate benchmark is the leading indicator. If Henderson is barreling the ball at 10%+ by mid-season, the power is back and 30 home runs are in play. If he's still below 9%, we're watching 2025 again — a productive player, but not the MVP candidate the Orioles are building around.

At 140 wRC+, Henderson would rank among the top 15-20 hitters in baseball. That's the tier the Orioles need him in to separate from the rest of the AL East.

### Adley Rutschman — The On-Base Engine

**Benchmarks:** OBP >= .340 | BB% >= 10% | wRC+ >= 115

Rutschman's value starts with getting on base. His .365 OBP in 2023 was among the best in baseball from any position. In 2025, it slipped to .307 — a significant regression that coincided with what looked like a conscious effort to add power to his game.

The benchmarks ask Rutschman to be the disciplined hitter he was, not the power hitter he tried to become. A .340 OBP and 10% walk rate from the catcher position is elite. A 115 wRC+ makes him one of the best offensive catchers in the American League. All three targets are within his established range — the question is whether he returns to the approach that made him special.

In a lineup that now includes Pete Alonso, Rutschman doesn't need to drive the ball for power. He needs to get on base ahead of the sluggers. These benchmarks reflect that role.

### Jordan Westburg — The Durability Test

**Benchmarks:** OPS >= .800 | ISO >= .180 | Games pace >= 140

Westburg's talent isn't in question — he posted a .192 ISO in 2025, showing legitimate pop from the middle infield. The concern is availability. His games pace benchmark of 140 is the most important of the three because Westburg's production only matters if he's in the lineup consistently.

An .800 OPS would make Westburg one of the more productive second basemen in the league. Combined with the ISO target, the benchmarks describe a player who provides above-average power from a premium defensive position for a full season. That player is worth 3-4 WAR and is a cornerstone of a contending infield.

### Colton Cowser — The Contact Question

**Benchmarks:** K% <= 22% | Hard% >= 38% | wRC+ >= 110

Cowser's 2025 season was defined by one number: a 35.6% strikeout rate. That's well above the threshold where strikeouts start to overwhelm a hitter's other skills. The good news is that when Cowser made contact, it was quality contact — his 39.2% hard-hit rate was solid.

The benchmarks ask Cowser to cut his strikeout rate by nearly 14 percentage points while maintaining his hard contact. That's a big developmental leap. But Cowser was the 5th overall pick in the 2021 draft, and the bat-to-ball skills were a core part of his prospect profile. The question is whether the 2025 strikeout spike was an adjustment period or a skill limitation.

At a 22% K-rate with a 38%+ hard-hit rate and 110 wRC+, Cowser would be an above-average everyday outfielder. That's the baseline the Orioles need from the position.

### Pete Alonso — The Acquisition

**Benchmarks:** HR pace >= 30 | Exit velo >= 91 mph | SLG >= .470

Alonso's benchmarks are the most straightforward on the board: hit the ball hard, hit it far, do it often. Baltimore signed Alonso to a five-year deal because they needed a middle-of-the-order power bat, and these three targets describe exactly what they're paying for.

The exit velocity benchmark is the canary in the coal mine. At 93.5 mph average exit velo in 2025, Alonso showed no signs of physical decline. If that number stays above 91, the raw power is intact and the counting stats should follow. A 30-homer pace with a .470+ SLG makes Alonso one of the most dangerous first basemen in the league — and gives the Orioles a lineup protector they haven't had since... well, since before they had one.

In 2025, Alonso was on pace for 38 home runs with a .524 SLG. He cleared all three benchmarks comfortably. The question in 2026 is whether a new park and new league affect those numbers.

### Jackson Holliday — The Adjustment

**Benchmarks:** K% <= 25% | BB% >= 9% | AVG >= .250

Holliday's benchmarks are intentionally conservative. He's a 22-year-old former #1 overall prospect who struggled badly in his initial major league exposure in 2024, then showed meaningful improvement in 2025 — cutting his strikeout rate to 21.6% and hitting .242.

The targets don't ask Holliday to be a star. They ask him to be a competent major leaguer: make enough contact (K% <= 25%), draw enough walks (BB% >= 9%), and hit for a respectable average (AVG >= .250). If he meets all three, the Orioles have a cost-controlled second baseman who can hold down the position while his bat develops further.

What's notable is that Holliday already met one of his three benchmarks in 2025 — his 21.6% K-rate was well under the 25% target. The discipline threshold of 9% BB-rate was just barely missed at 8.6%. He's close, and the benchmarks are designed to reflect where "close" needs to become "there."

---

## Pitchers

### Kyle Bradish — The Ace Returns

**Benchmarks:** ERA <= 3.50 | K/9 >= 9.0 | IP pace >= 160

Bradish is the most important pitcher on the staff, and his benchmarks reflect two distinct questions: can he pitch at an ace level, and can he stay healthy long enough for it to matter?

The production benchmarks are already answered in the early data — Bradish posted a 2.53 ERA with a dominant 13.22 K/9 in his initial outings. The stuff is clearly there. But the innings pace target of 160 is the benchmark that matters most. After missing significant time with injury, Bradish needs to prove he can absorb a full starter's workload. In 2025, he threw just 32 innings.

At 160+ innings with a sub-3.50 ERA, Bradish would be one of the 15 best starters in the American League. That's the kind of front-of-rotation arm that turns a good pitching staff into a great one.

### Trevor Rogers — The Surprise

**Benchmarks:** ERA <= 4.00 | WHIP <= 1.25 | K% >= 22%

Rogers' benchmarks ask a simple question: can he be a reliable mid-rotation starter? After arriving from Miami, Rogers has been exceptional early — a 1.81 ERA and 0.90 WHIP with a 24.3% strikeout rate. He's cleared all three benchmarks with room to spare.

The targets were set conservatively because Rogers has been inconsistent across his career. A 4.00 ERA and 1.25 WHIP describe a league-average-to-solid starter. If Rogers sustains anything close to his current performance, the Orioles have found a rotation steal. If he regresses to his career norms, meeting the benchmarks would still make him a useful piece.

### Shane Baz — The Upside Play

**Benchmarks:** ERA <= 3.75 | FIP <= 3.75 | IP pace >= 140

Baz was acquired from Tampa Bay in a trade that added 1.8 projected fWAR to the Orioles. His benchmarks include both ERA and FIP because the relationship between the two tells you whether a pitcher is getting lucky or actually pitching well. A pitcher whose ERA matches his FIP is sustainable; a pitcher whose ERA is far below his FIP is due for regression.

In 2025, Baz posted a 4.87 ERA with a 4.37 FIP — both above his benchmarks, but the FIP was closer to the target. His 166.1 innings show that durability isn't the concern; it's the quality of outcomes. In 2026, the Orioles need Baz to take a step forward in both metrics. A sub-3.75 ERA with a matching FIP would make him a legitimate #3 starter.

### Ryan Helsley — The Closer

**Benchmarks:** ERA <= 2.50 | K/9 >= 11.0 | SV pace >= 35

Helsley was signed specifically to solve the Orioles' late-inning problem. His benchmarks describe a dominant closer: sub-2.50 ERA, 11+ K/9, and a saves pace that indicates he's pitching in high-leverage situations consistently.

In 2025, Helsley posted a 4.50 ERA with a 10.13 K/9 and was on pace for just 21 saves. None of the three benchmarks were met. The question in 2026 is whether 2025 was an aberration or a new normal. Helsley's 2024 season — 1.30 ERA, 14.04 K/9, 49 saves — showed what he's capable of. These benchmarks don't ask him to replicate his peak; they ask him to be within shouting distance of it.

### Team Bullpen — The Collective

**Benchmarks:** ERA <= 3.75 | K/9 >= 9.5 | WHIP <= 1.25

The bullpen is the only unit-level entry in the benchmarks, and intentionally so. Relievers are volatile individually — what matters is whether the group, as a whole, can hold leads and get outs. In 2025, the Orioles bullpen posted a 4.87 ERA, 9.0 K/9, and 1.56 WHIP — missing all three targets.

The addition of Helsley, Andrew Kittredge (via trade from the Cubs), and natural development from the internal arms gives the bullpen a different composition in 2026. The benchmarks describe a league-average-to-good relief corps: 3.75 ERA, 9.5 K/9, 1.25 WHIP. If the pen hits those marks, the Orioles' improved offense and starting pitching won't be wasted by late-inning collapses.

---

## How It All Connects

The benchmarks aren't independent of each other. They describe a specific version of the 2026 Orioles — the version that contends for the AL East title.

**The offense needs Henderson and Alonso to anchor it.** Henderson's 140 wRC+ and 30-homer pace, combined with Alonso's power production, gives Baltimore a 1-2 punch that changes how opposing pitchers approach the entire lineup. Rutschman getting on base at a .340 clip ahead of them is the multiplier.

**The pitching needs health.** Bradish's innings pace and Baz's durability are the benchmarks that the rest of the staff is built around. Rogers provides insurance. If Bradish and Baz both hit their innings targets, the Orioles have a rotation that can compete with anyone in the American League.

**The young players need to take steps.** Cowser's contact improvements, Holliday's baseline competence, and Westburg's availability are the difference between a lineup with depth and a lineup with holes. None of them need to be stars. They need to not be weaknesses.

**The bullpen needs to be league-average.** After a disastrous 2025, the bar is simply getting to a 3.75 ERA. That's not elite. It's functional. And for a team that added this much talent to the rotation and lineup, functional might be enough.

---

## The Bottom Line

As of today, 14 of the 33 benchmarks are being met. That's 42% — not where the Orioles want to be, but the season is young and several benchmarks are pace-based projections that will stabilize over more games.

The benchmarks to watch most closely:

- **Henderson's barrel rate** — the single best leading indicator of whether the power is coming back
- **Bradish's innings accumulation** — health is the variable that everything else is built on
- **The bullpen ERA** — the most significant gap between 2025 reality and 2026 need
- **Cowser's strikeout rate** — the biggest developmental question in the lineup

We'll update these benchmarks daily throughout the season. The tracker on the home page shows real-time progress against all 33 targets, sourced directly from FanGraphs data. Toggle to "2025 Results" to see how these same players performed against these targets last year — useful context for whether the benchmarks are realistic or aspirational.

This is what a competitive window looks like up close: specific players, specific targets, specific questions. The answers will define the Orioles' 2026 season.
