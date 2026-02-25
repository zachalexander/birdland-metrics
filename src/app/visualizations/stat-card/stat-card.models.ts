export type CardType = 'projections' | 'player-stats' | 'custom';

export type ProjectionStat = 'playoff_pct' | 'division_pct' | 'wildcard_pct' | 'win_total';

export interface ProjectionStatOption {
  key: ProjectionStat;
  label: string;
  contextLabel: string;
}

export const PROJECTION_STAT_OPTIONS: ProjectionStatOption[] = [
  { key: 'playoff_pct', label: 'Playoff Odds', contextLabel: 'Playoff Probability' },
  { key: 'division_pct', label: 'Division Odds', contextLabel: 'Division Win Probability' },
  { key: 'wildcard_pct', label: 'Wild Card Odds', contextLabel: 'Wild Card Probability' },
  { key: 'win_total', label: 'Win Total', contextLabel: 'Projected Wins' },
];

export const FULL_TEAM_NAMES: Record<string, string> = {
  BAL: 'Baltimore Orioles', NYY: 'New York Yankees', BOS: 'Boston Red Sox',
  TB: 'Tampa Bay Rays', TOR: 'Toronto Blue Jays',
  CLE: 'Cleveland Guardians', CWS: 'Chicago White Sox', DET: 'Detroit Tigers',
  KC: 'Kansas City Royals', MIN: 'Minnesota Twins',
  HOU: 'Houston Astros', LAA: 'Los Angeles Angels', ATH: 'Athletics',
  SEA: 'Seattle Mariners', TEX: 'Texas Rangers',
  ATL: 'Atlanta Braves', MIA: 'Miami Marlins', NYM: 'New York Mets',
  PHI: 'Philadelphia Phillies', WSH: 'Washington Nationals',
  CHC: 'Chicago Cubs', CIN: 'Cincinnati Reds', MIL: 'Milwaukee Brewers',
  PIT: 'Pittsburgh Pirates', STL: 'St. Louis Cardinals',
  ARI: 'Arizona Diamondbacks', COL: 'Colorado Rockies', LAD: 'Los Angeles Dodgers',
  SD: 'San Diego Padres', SF: 'San Francisco Giants',
};
