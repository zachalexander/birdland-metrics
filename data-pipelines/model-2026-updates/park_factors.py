"""
MLB Park Factors — 5-year rolling averages from FanGraphs.

Basic park factor: 100 = neutral, >100 = hitter-friendly, <100 = pitcher-friendly.
Used to scale FIP adjustments in the enhanced model.

Source: FanGraphs Guts! (https://www.fangraphs.com/guts.aspx?type=pf)
"""

# Park factors by season (Basic 5yr from FanGraphs)
# Team codes use our canonical format (ATH not OAK, WSH not WSN)
PARK_FACTORS = {
    2023: {
        'LAA': 101, 'BAL': 99, 'BOS': 104, 'CWS': 100, 'CLE': 99,
        'DET': 100, 'KC': 103, 'MIN': 101, 'NYY': 99, 'ATH': 96,
        'SEA': 94, 'TB': 96, 'TEX': 99, 'TOR': 99,
        'AZ': 101, 'ATL': 100, 'CHC': 98, 'CIN': 105, 'COL': 113,
        'MIA': 101, 'HOU': 99, 'LAD': 99, 'MIL': 99, 'WSH': 100,
        'NYM': 96, 'PHI': 101, 'PIT': 102, 'STL': 98, 'SD': 96, 'SF': 97,
    },
    2024: {
        'LAA': 101, 'BAL': 99, 'BOS': 104, 'CWS': 100, 'CLE': 99,
        'DET': 100, 'KC': 103, 'MIN': 101, 'NYY': 99, 'ATH': 96,
        'SEA': 94, 'TB': 96, 'TEX': 99, 'TOR': 99,
        'AZ': 101, 'ATL': 100, 'CHC': 98, 'CIN': 105, 'COL': 113,
        'MIA': 101, 'HOU': 99, 'LAD': 99, 'MIL': 99, 'WSH': 100,
        'NYM': 96, 'PHI': 101, 'PIT': 102, 'STL': 98, 'SD': 96, 'SF': 97,
    },
    2025: {
        'LAA': 101, 'BAL': 99, 'BOS': 104, 'CWS': 100, 'CLE': 99,
        'DET': 100, 'KC': 103, 'MIN': 101, 'NYY': 99, 'ATH': 103,
        'SEA': 94, 'TB': 101, 'TEX': 99, 'TOR': 99,
        'AZ': 101, 'ATL': 100, 'CHC': 98, 'CIN': 105, 'COL': 113,
        'MIA': 101, 'HOU': 99, 'LAD': 99, 'MIL': 99, 'WSH': 100,
        'NYM': 96, 'PHI': 101, 'PIT': 102, 'STL': 98, 'SD': 96, 'SF': 97,
    },
}

# Default for unknown seasons (use 2024 as baseline)
DEFAULT_PARK_FACTORS = PARK_FACTORS[2024]


def get_park_factor(team, season=None):
    """Get park factor for a team's home park."""
    factors = PARK_FACTORS.get(season, DEFAULT_PARK_FACTORS)
    return factors.get(team, 100)
