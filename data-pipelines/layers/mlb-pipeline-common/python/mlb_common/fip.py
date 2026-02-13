"""
Shared FIP (Fielding Independent Pitching) utilities.
Fetches pitcher stats from MLB Stats API and computes FIP-adjusted
win probabilities with probability shrinkage.
"""
import logging
import requests
from mlb_common.config import (
    MLB_PITCHING_STATS_URL, FIP_WEIGHT, PROB_SHRINKAGE,
)

logger = logging.getLogger(__name__)


def fetch_pitcher_fip(season):
    """
    Fetch season pitching stats from MLB Stats API and compute FIP for all pitchers.

    Uses a single bulk API call with playerPool=ALL to get every pitcher.

    Args:
        season: MLB season year (e.g. 2026)

    Returns:
        (fip_dict, lg_fip) where:
        - fip_dict = {pitcher_id: {'fip': float, 'ip': float, 'name': str}}
        - lg_fip = league-average FIP (float)
    """
    resp = requests.get(MLB_PITCHING_STATS_URL, params={
        'stats': 'season',
        'group': 'pitching',
        'season': season,
        'sportId': 1,
        'limit': 2000,
        'playerPool': 'ALL',
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Parse individual pitcher stats
    pitchers = []
    for split in data.get('stats', [{}])[0].get('splits', []):
        stat = split.get('stat', {})
        player = split.get('player', {})

        ip_str = stat.get('inningsPitched', '0')
        ip = float(ip_str) if ip_str else 0.0
        if ip < 1.0:
            continue

        pitchers.append({
            'id': player.get('id'),
            'name': player.get('fullName', ''),
            'ip': ip,
            'k': int(stat.get('strikeOuts', 0)),
            'bb': int(stat.get('baseOnBalls', 0)),
            'hbp': int(stat.get('hitByPitch', 0)),
            'hr': int(stat.get('homeRuns', 0)),
            'era': float(stat.get('era', '0')),
        })

    # Compute league-wide cFIP constant from ALL pitchers
    total_ip = sum(p['ip'] for p in pitchers)
    total_hr = sum(p['hr'] for p in pitchers)
    total_bb = sum(p['bb'] for p in pitchers)
    total_hbp = sum(p['hbp'] for p in pitchers)
    total_k = sum(p['k'] for p in pitchers)
    total_er = sum(p['era'] * p['ip'] / 9.0 for p in pitchers)

    lg_era = total_er * 9.0 / total_ip if total_ip > 0 else 4.00
    lg_fip_component = (13 * total_hr + 3 * (total_bb + total_hbp) - 2 * total_k) / total_ip
    cfip = lg_era - lg_fip_component

    # Compute individual FIP
    fip_dict = {}
    for p in pitchers:
        fip = (13 * p['hr'] + 3 * (p['bb'] + p['hbp']) - 2 * p['k']) / p['ip'] + cfip
        fip_dict[p['id']] = {
            'fip': round(fip, 3),
            'ip': p['ip'],
            'name': p['name'],
        }

    lg_fip = cfip + lg_fip_component  # = lg_era
    logger.info(f"Computed FIP for {len(fip_dict)} pitchers (season {season}, cFIP={cfip:.3f}, lgFIP={lg_fip:.3f})")

    return fip_dict, lg_fip


def fip_adjustment(home_pitcher_id, away_pitcher_id, fip_dict, lg_fip):
    """
    Compute ELO point adjustments based on starting pitcher FIP.

    A pitcher with FIP below league average gets a positive adjustment
    (better than average), and vice versa.

    Args:
        home_pitcher_id: MLB player ID for home starter (int or None)
        away_pitcher_id: MLB player ID for away starter (int or None)
        fip_dict: dict from fetch_pitcher_fip()
        lg_fip: league-average FIP

    Returns:
        (home_adj, away_adj) — ELO point adjustments for each team
    """
    home_fip = fip_dict[home_pitcher_id]['fip'] if home_pitcher_id and home_pitcher_id in fip_dict else lg_fip
    away_fip = fip_dict[away_pitcher_id]['fip'] if away_pitcher_id and away_pitcher_id in fip_dict else lg_fip

    home_adj = (lg_fip - home_fip) * FIP_WEIGHT
    away_adj = (lg_fip - away_fip) * FIP_WEIGHT

    return home_adj, away_adj


def apply_shrinkage(raw_prob):
    """
    Apply probability shrinkage to correct ELO overconfidence.

    Pulls extreme probabilities toward 50%. For example, with PROB_SHRINKAGE=0.16:
    - raw 0.70 -> 0.636
    - raw 0.50 -> 0.50 (unchanged)
    - raw 0.30 -> 0.364

    Args:
        raw_prob: Raw win probability from expected_score() (0.0 to 1.0)

    Returns:
        Adjusted probability (float between PROB_SHRINKAGE and 1-PROB_SHRINKAGE)
    """
    return PROB_SHRINKAGE + (1 - 2 * PROB_SHRINKAGE) * raw_prob
