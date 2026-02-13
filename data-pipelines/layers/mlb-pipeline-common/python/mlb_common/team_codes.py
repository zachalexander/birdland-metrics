"""
Single source of truth for MLB team codes, leagues, and divisions.

Canonical abbreviations follow the MLB Stats API convention used in schedule CSVs.
The SCHEDULE_TO_ELO_MAP handles the 8 codes that differ between the schedule CSV
and the end-of-season ELO baseline file (Retrosheet-derived).
"""

# Mapping from end-of-prior-season ELO file codes → schedule/canonical codes
# These are the 8 teams whose Retrosheet-derived abbreviations differ from MLB Stats API
SCHEDULE_TO_ELO_MAP = {
    'WSN': 'WSH',
    'KCR': 'KC',
    'SFG': 'SF',
    'SDP': 'SD',
    'CHW': 'CWS',
    'ARI': 'AZ',
    'OAK': 'ATH',
    'TBR': 'TB',
}

# Reverse mapping: canonical → ELO file format
ELO_TO_SCHEDULE_MAP = {v: k for k, v in SCHEDULE_TO_ELO_MAP.items()}

# All 30 MLB teams: league and division assignments
TEAM_LEAGUE = {
    'BAL': 'AL', 'BOS': 'AL', 'NYY': 'AL', 'TB':  'AL', 'TOR': 'AL',
    'CWS': 'AL', 'CLE': 'AL', 'DET': 'AL', 'KC':  'AL', 'MIN': 'AL',
    'HOU': 'AL', 'LAA': 'AL', 'ATH': 'AL', 'SEA': 'AL', 'TEX': 'AL',
    'ATL': 'NL', 'MIA': 'NL', 'NYM': 'NL', 'PHI': 'NL', 'WSH': 'NL',
    'CHC': 'NL', 'CIN': 'NL', 'MIL': 'NL', 'PIT': 'NL', 'STL': 'NL',
    'AZ':  'NL', 'COL': 'NL', 'LAD': 'NL', 'SD':  'NL', 'SF':  'NL',
}

TEAM_DIVISION = {
    'BAL': 'AL East', 'BOS': 'AL East', 'NYY': 'AL East', 'TB':  'AL East', 'TOR': 'AL East',
    'CWS': 'AL Central', 'CLE': 'AL Central', 'DET': 'AL Central', 'KC':  'AL Central', 'MIN': 'AL Central',
    'HOU': 'AL West', 'LAA': 'AL West', 'ATH': 'AL West', 'SEA': 'AL West', 'TEX': 'AL West',
    'ATL': 'NL East', 'MIA': 'NL East', 'NYM': 'NL East', 'PHI': 'NL East', 'WSH': 'NL East',
    'CHC': 'NL Central', 'CIN': 'NL Central', 'MIL': 'NL Central', 'PIT': 'NL Central', 'STL': 'NL Central',
    'AZ':  'NL West', 'COL': 'NL West', 'LAD': 'NL West', 'SD':  'NL West', 'SF':  'NL West',
}

# Full team name → canonical abbreviation (for MLB Stats API responses that use full names)
TEAM_NAME_TO_ABBREV = {
    'Arizona Diamondbacks': 'AZ',
    'Atlanta Braves': 'ATL',
    'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC',
    'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN',
    'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET',
    'Houston Astros': 'HOU',
    'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA',
    'Los Angeles Dodgers': 'LAD',
    'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN',
    'New York Mets': 'NYM',
    'New York Yankees': 'NYY',
    'Athletics': 'ATH',
    'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD',
    'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA',
    'St. Louis Cardinals': 'STL',
    'Tampa Bay Rays': 'TB',
    'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR',
    'Washington Nationals': 'WSH',
}


# MLB Stats API numeric team ID → canonical abbreviation
TEAM_ID_TO_ABBR = {
    108: 'LAA', 109: 'AZ', 110: 'BAL', 111: 'BOS', 112: 'CHC',
    113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET', 117: 'HOU',
    118: 'KC', 119: 'LAD', 120: 'WSH', 121: 'NYM', 133: 'ATH',
    134: 'PIT', 135: 'SD', 136: 'SEA', 137: 'SF', 138: 'STL',
    139: 'TB', 140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI',
    144: 'ATL', 145: 'CWS', 146: 'MIA', 147: 'NYY', 158: 'MIL',
}


def normalize_team_code(code, source='schedule'):
    """
    Normalize a team abbreviation to canonical (schedule) format.

    Args:
        code: Team abbreviation string
        source: 'schedule' (already canonical), 'elo' (needs mapping from Retrosheet format)

    Returns:
        Canonical team abbreviation
    """
    if source == 'elo':
        return SCHEDULE_TO_ELO_MAP.get(code, code)
    return code
