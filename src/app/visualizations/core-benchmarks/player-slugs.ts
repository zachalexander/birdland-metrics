export interface PlayerSlugEntry {
  id: string;
  slug: string;
  name: string;
  description: string;
}

const PLAYERS: PlayerSlugEntry[] = [
  {
    id: '683002',
    slug: 'gunnar-henderson',
    name: 'Gunnar Henderson',
    description:
      'Gunnar Henderson\'s 2024 was a full-scale breakout — 37 home runs, a 139 wRC+, and a top-five MVP finish. But 2025 was a step back across the board: his barrel rate dropped to 8.5%, his wRC+ fell to 120, and his power numbers dipped to 17 home runs. His three benchmarks — Barrel% at 10%, wRC+ at 140, and an HR pace of 30 — are designed to answer one question: can he get back to MVP-caliber production? The barrel rate tests whether he\'s squaring the ball up with authority, wRC+ captures his total offensive value, and the HR pace tracks the game-changing power that makes him a franchise cornerstone. If Henderson is the player he was in 2024, the Orioles are a legitimate contender.',
  },
  {
    id: '668939',
    slug: 'adley-rutschman',
    name: 'Adley Rutschman',
    description:
      'Adley Rutschman\'s value has always been tied to his plate discipline — and his 2025 was a case study in what happens when the bat doesn\'t back it up. He still drew walks at a healthy 11% clip, but his OBP dropped to .307 and his wRC+ cratered to 91, well below average. All three benchmarks lean into the discipline-first profile: an OBP of .340 sets the floor for a premium on-base player, BB% at 11% confirms he\'s maintaining his elite walk rate, and a wRC+ of 115 ensures the discipline translates into actual run production. For Rutschman, the question isn\'t whether he can take walks — it\'s whether he can hit enough to make those walks matter.',
  },
  {
    id: '682614',
    slug: 'jordan-westburg',
    name: 'Jordan Westburg',
    description:
      'Jordan Westburg\'s 2025 was cut short at 85 games due to myriad injuries, but the production was there when he played: a .457 slugging percentage, a 115 wRC+, and genuine extra-base pop. His benchmarks — SLG at .450, wRC+ at 110, and a games pace of 140 — reflect two questions: can he sustain the breakout power, and can he stay on the field? His latest partial UCL tear injury will set him back this year, but if he can return in late spring, we have his benchmarks set accordingly. The SLG benchmark tracks extra-base power, wRC+ captures total offensive contribution, and the games pace is the health check that matters most. He will miss the 140-mark, but we hope he can land somewhere in the initial projection (around 110, but that is optimistic). Westburg has the talent to be an above-average everyday player. The UCL is the variable.',
  },
  {
    id: '681297',
    slug: 'colton-cowser',
    name: 'Colton Cowser',
    description:
      'Colton Cowser had a tough 2025. After returning from a fractured left thumb, he had a hard time getting it going. He made hard contact at a solid 39.2% rate and posted a 14.1% barrel rate, showing the raw power tools are real — but a 35.6% strikeout rate overwhelmed everything else, dragging his wRC+ down to 83. His benchmarks zero in on the contact-versus-power balance: K% at 28% tests whether he can cut strikeouts to a more sustainable level, Barrel% at 12% ensures he\'s squaring the ball up with authority, and wRC+ at 110 is the bottom-line production number. Cowser doesn\'t need to be a star. He needs to stop striking out enough to let his hard contact profile play.',
  },
  {
    id: '624413',
    slug: 'pete-alonso',
    name: 'Pete Alonso',
    description:
      'Pete Alonso arrived in Baltimore as the marquee free-agent signing, and his benchmarks are straightforward: justify the investment with power. His 2025 with the Mets showed the bat is still there — 38 home runs, a 93.5 mph average exit velocity, and a .524 slugging percentage. All three benchmarks are power-focused: HR pace at 35 pushes him toward elite power production, Barrel% at 15% tests whether he\'s squaring the ball up at the rate that drives his power, and SLG at .500 tracks total extra-base production at a premium level. Alonso cleared all three thresholds last year. The question for 2026 isn\'t whether Alonso can hit — it\'s whether he keeps hitting in a new league, a new lineup, and a new ballpark.',
  },
  {
    id: '696137',
    slug: 'jackson-holliday',
    name: 'Jackson Holliday',
    description:
      'Jackson Holliday\'s 2025 showed real growth after a rough debut: a .242 average, 17 home runs, and 149 games played across his age-21 season. His strikeout rate dropped to 21.6%, but his walk rate (8.6%) and on-base percentage still lagged behind what you\'d expect from a former first-overall pick. His benchmarks target the next developmental step: K% at 25% is a generous ceiling he already clears, BB% at 9% pushes him toward better pitch selection, and OBP at .320 tests whether the discipline improvements translate into getting on base. These aren\'t star-level targets — they\'re proof-of-concept numbers for a young player turning potential into production. We\'ll see if Holliday can take that next step in 2026 after he recovers from the broken hamate injury he suffered early in spring training.',
  },
  {
    id: '680694',
    slug: 'kyle-bradish',
    name: 'Kyle Bradish',
    description:
      'Kyle Bradish is one of the most talented arms on the Orioles staff — the question is whether he experiences any lingering arm issues that kept him out for most of the past two seasons. In a limited 32 innings in 2025, the stuff was electric: a 2.53 ERA and a 13.22 K/9 rate that ranked among the best in baseball. His benchmarks — ERA at 3.50, K/9 at 9.5, and an IP pace of 130 — tell a clear story: the first two are almost formalities if he\'s on the mound, but the innings pace is the real test. A 130-inning target means roughly 23 starts of at least 5.2 innings — a realistic goal for a pitcher returning from Tommy John. If Bradish can deliver that, the Orioles have a legitimate ace.',
  },
  {
    id: '669432',
    slug: 'trevor-rogers',
    name: 'Trevor Rogers',
    description:
      'Trevor Rogers turned heads with a dominant start to his Orioles tenure: a 1.81 ERA, a 0.90 WHIP, and a 24.3% strikeout rate. The benchmarks are calibrated to a co-ace role — ERA at 3.50, WHIP at 1.25, and an IP pace of 130 — and he blew past the rate targets in his initial stint. The question for 2026 is sustainability over a full season. Rogers has historically been inconsistent across full years, and these targets are set at the level where he\'d need to be a reliable top-of-the-rotation arm, not just a hot-streak pitcher. A 130-inning target reflects the workload he\'ll need to carry as a co-ace alongside Bradish.',
  },
  {
    id: '669358',
    slug: 'shane-baz',
    name: 'Shane Baz',
    description:
      'Shane Baz comes to Baltimore after a full 166-inning season with Tampa Bay — proof that the arm can hold up — but the results were below where he\'ll need to be: a 4.87 ERA and a 4.37 FIP. His benchmarks pair production with durability: ERA at 3.75 and FIP at 3.75 set a mid-rotation floor, while an IP pace of 140 ensures he\'s pitching deep enough into games to matter. The ERA and FIP targets are intentionally paired because they tell different stories — ERA captures results, while FIP strips out defense and luck. If both are under 3.75, Baz is pitching like a genuine mid-rotation starter, not just getting lucky.',
  },
  {
    id: '664854',
    slug: 'ryan-helsley',
    name: 'Ryan Helsley',
    description:
      'Ryan Helsley was one of the best closers in baseball in 2024 — a 1.49 ERA, 49 saves, and a strikeout rate that made him nearly unhittable. But his 2025 with the Cardinals saw a significant regression: a 4.50 ERA, a 10.13 K/9, and only 21 saves. His benchmarks are set at strong closer standards: ERA at 3.25, K/9 at 11.0, and a save pace of 35. The ERA target tests whether he can pitch at a level that justifies the ninth inning, K/9 at 11.0 tests whether the dominant stuff is still there, and the save pace ensures he\'s getting high-leverage opportunities — which only happens if the team trusts him. Baltimore needs a reliable closer. These benchmarks test whether Helsley can be that guy.',
  },
  {
    id: 'bullpen',
    slug: 'team-bullpen',
    name: 'Team Bullpen',
    description:
      'The Orioles bullpen was a clear weakness in 2025: a 4.87 ERA, a 9.0 K/9, and a 1.56 WHIP that collectively failed every benchmark. The targets — ERA at 3.75, K/9 at 9.5, and WHIP at 1.25 — aren\'t asking for an elite relief corps. They\'re asking for a competent one. A 3.75 ERA keeps runs at a manageable rate in short stints, K/9 at 9.5 means relievers are missing enough bats to avoid hard contact, and a 1.25 WHIP means they\'re not loading the bases every other inning. This is the aggregate health check for the group behind Helsley — if the pen hits these numbers, it\'s no longer the liability that cost Baltimore games in 2025.',
  },
];

const BY_SLUG = new Map(PLAYERS.map(p => [p.slug, p]));
const BY_ID = new Map(PLAYERS.map(p => [p.id, p]));

export function playerBySlug(slug: string): PlayerSlugEntry | undefined {
  return BY_SLUG.get(slug);
}

export function slugForPlayerId(id: string): string | undefined {
  return BY_ID.get(id)?.slug;
}

export function allPlayerSlugs(): PlayerSlugEntry[] {
  return PLAYERS;
}
