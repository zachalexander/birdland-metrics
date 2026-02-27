// --- S3 JSON response envelopes ---

export interface PlayoffOddsResponse {
  updated: string;
  simulations: number;
  odds: PlayoffOdds[];
}

export interface StandingsResponse {
  updated: string;
  standings: TeamStanding[];
}

export interface ProjectionsResponse {
  updated: string;
  projections: TeamProjection[];
}

export interface EloResponse {
  updated: string;
  ratings: EloRating[];
}

export interface RecentGamesResponse {
  updated: string;
  game_type?: 'R' | 'S';
  games: RecentGame[];
}

// --- Data models ---

export interface PlayoffOdds {
  team: string;
  playoff_pct: number;
  division_pct: number;
  wildcard_pct: number;
}

export interface TeamStanding {
  team: string;
  median_wins: number;
  avg_wins: number;
  std_dev: number;
  p10: number;
  p90: number;
}

export interface TeamProjection {
  team: string;
  median_wins: number;
  avg_wins: number;
  std_dev: number;
  p10: number;
  p25: number;
  p75: number;
  p90: number;
}

export interface EloRating {
  team: string;
  elo: number;
}

export interface RecentGame {
  id: string;
  date: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  winning_team: string;
  losing_team: string;
  winning_pitcher: string;
  losing_pitcher: string;
  save_pitcher: string;
  venue: string;
}

export interface EloHistoryPoint {
  date: string;
  elo: number;
}

export interface PlayoffOddsHistoryPoint {
  date: string;
  team: string;
  playoff_pct: number;
  division_pct?: number;
  wildcard_pct?: number;
}

export interface EloHistoryResponse {
  teams: Record<string, EloHistoryPoint[]>;
}

// --- Player stats ---

export interface PlayerBatting {
  player_id: string;
  mlb_id?: number;
  name: string;
  team: string;
  g: number;
  pa: number;
  ab: number;
  h: number;
  doubles: number;
  triples: number;
  hr: number;
  rbi: number;
  bb: number;
  so: number;
  sb: number;
  cs: number;
  avg: number;
  obp: number;
  slg: number;
  ops: number;
  war?: number;
}

export interface PlayerPitching {
  player_id: string;
  mlb_id?: number;
  name: string;
  team: string;
  g: number;
  gs: number;
  ip: number;
  h: number;
  er: number;
  bb: number;
  so: number;
  hr: number;
  w: number;
  l: number;
  sv: number;
  era: number;
  whip: number;
  k_per_9: number;
  fip: number;
  war?: number;
}

export interface PlayerStatsResponse {
  updated: string;
  season: number;
  batting: PlayerBatting[];
  pitching: PlayerPitching[];
}

export interface PlayerSeasonStats {
  season: number;
  games: number;
  pa: number;
  avg: number;
  obp: number;
  slg: number;
  ops: number;
  hr: number;
  sb: number;
  runs: number;
  rbi: number;
  bb_pct: number;
  k_pct: number;
  iso: number;
  babip: number;
  woba: number;
  wrc_plus: number;
  war: number;
  hard_pct: number;
  barrel_pct: number;
  ev: number;
  launch_angle: number;
  gb_pct: number;
  fb_pct: number;
  ld_pct: number;
  pull_pct: number;
  spd: number;
  bsr: number;
  off: number;
  def_val: number;
}

// --- Core player benchmarks ---

export type BenchmarkDirection = 'gte' | 'lte';
export type BenchmarkCategory = 'power' | 'contact' | 'discipline' | 'production' | 'health';

export interface PlayerBenchmark {
  key: string;
  label: string;
  description: string;
  target: number;
  direction: BenchmarkDirection;
  current: number | null;
  actual?: number;
  met: boolean;
  category: BenchmarkCategory;
  // Projection-derived fields
  projected?: number;
  pacePct?: number | null;
}

export interface BenchmarkPlayer {
  name: string;
  playerId: string;
  position: string;
  type: 'batter' | 'pitcher';
  photoUrl?: string;
  benchmarks: PlayerBenchmark[];
  projectionConfidence?: number;
}

export interface CoreBenchmarksResponse {
  updated: string;
  season: number;
  players: BenchmarkPlayer[];
  projectionSource?: string;
}

// --- Player projections ---

export interface PlayerProjectionStats {
  season: number;
  games: number;
  war: number;
  // Batter stats (optional for pitchers)
  pa?: number;
  avg?: number;
  obp?: number;
  slg?: number;
  ops?: number;
  hr?: number;
  sb?: number;
  bb_pct?: number;
  k_pct?: number;
  iso?: number;
  babip?: number;
  woba?: number;
  wrc_plus?: number;
  barrel_pct?: number;
  hard_pct?: number;
  ev?: number;
  launch_angle?: number;
  // Pitcher stats (optional for batters)
  era?: number;
  fip?: number;
  whip?: number;
  k_per_9?: number;
  bb_per_9?: number;
  ip?: number;
  gs?: number;
  sv?: number;
}

export interface PlayerProjection {
  player_name: string;
  player_id: number;       // FanGraphs ID
  mlbam_id: number;        // MLB Advanced Media ID
  position: string;
  age: number;
  projection_type: 'marcel' | 'statcast_enhanced' | 'blended';
  stats: PlayerProjectionStats;
  confidence: number;
}

export interface PlayerProjectionsResponse {
  team: string;
  season: number;
  generated_at: string;
  projections: PlayerProjection[];
}

// --- Team display helpers ---

export const TEAM_NAMES: Record<string, string> = {
  BAL: 'Orioles', NYY: 'Yankees', BOS: 'Red Sox', TB: 'Rays', TOR: 'Blue Jays',
  CLE: 'Guardians', CWS: 'White Sox', DET: 'Tigers', KC: 'Royals', MIN: 'Twins',
  HOU: 'Astros', LAA: 'Angels', ATH: 'Athletics', SEA: 'Mariners', TEX: 'Rangers',
  ATL: 'Braves', MIA: 'Marlins', NYM: 'Mets', PHI: 'Phillies', WSH: 'Nationals',
  CHC: 'Cubs', CIN: 'Reds', MIL: 'Brewers', PIT: 'Pirates', STL: 'Cardinals',
  ARI: 'Diamondbacks', COL: 'Rockies', LAD: 'Dodgers', SD: 'Padres', SF: 'Giants',
};

export const AL_EAST = ['BAL', 'NYY', 'BOS', 'TB', 'TOR'];
export const AL_CENTRAL = ['CLE', 'CWS', 'DET', 'KC', 'MIN'];
export const AL_WEST = ['HOU', 'LAA', 'ATH', 'SEA', 'TEX'];

/** Convert full team name (e.g. "Baltimore Orioles") to abbreviation ("BAL") */
export function teamAbbr(fullName: string): string {
  const map: Record<string, string> = {
    'Baltimore Orioles': 'BAL', 'New York Yankees': 'NYY', 'Boston Red Sox': 'BOS',
    'Tampa Bay Rays': 'TB', 'Toronto Blue Jays': 'TOR',
    'Cleveland Guardians': 'CLE', 'Chicago White Sox': 'CWS', 'Detroit Tigers': 'DET',
    'Kansas City Royals': 'KC', 'Minnesota Twins': 'MIN',
    'Houston Astros': 'HOU', 'Los Angeles Angels': 'LAA', 'Athletics': 'ATH',
    'Oakland Athletics': 'ATH', 'Sacramento Athletics': 'ATH',
    'Seattle Mariners': 'SEA', 'Texas Rangers': 'TEX',
    'Atlanta Braves': 'ATL', 'Miami Marlins': 'MIA', 'New York Mets': 'NYM',
    'Philadelphia Phillies': 'PHI', 'Washington Nationals': 'WSH',
    'Chicago Cubs': 'CHC', 'Cincinnati Reds': 'CIN', 'Milwaukee Brewers': 'MIL',
    'Pittsburgh Pirates': 'PIT', 'St. Louis Cardinals': 'STL',
    'Arizona Diamondbacks': 'ARI', 'Colorado Rockies': 'COL',
    'Los Angeles Dodgers': 'LAD', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
  };
  return map[fullName] ?? fullName;
}
