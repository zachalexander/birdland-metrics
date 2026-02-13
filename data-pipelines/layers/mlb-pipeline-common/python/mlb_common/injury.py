"""
Injury/IL impact assessment for MLB teams.

Pulls IL rosters from MLB Stats API, maps to FanGraphs WAR via pybaseball,
and computes per-team ELO adjustments based on WAR lost to injuries.

Applied at projection time only — stored ELO ratings remain clean.
"""
import logging
import time
from datetime import datetime

import statsapi
from pybaseball import batting_stats, pitching_stats, playerid_reverse_lookup

from mlb_common.config import INJURY_WAR_TO_ELO, SEASON_YEAR
from mlb_common.team_codes import TEAM_ID_TO_ABBR

logger = logging.getLogger(__name__)


def fetch_il_rosters(season):
    """
    Fetch injured list rosters for all 30 MLB teams.

    Uses the MLB Stats API 40-man roster endpoint and filters to players
    with 'Injured' in their status description.

    Args:
        season: MLB season year (e.g. 2026)

    Returns:
        {team_abbr: [{'mlb_id', 'name', 'position', 'il_type', 'is_pitcher'}, ...]}
    """
    teams = statsapi.get('teams', {'sportId': 1, 'season': season})
    il_rosters = {}
    all_team_ids = [(t['id'], TEAM_ID_TO_ABBR.get(t['id'], t['abbreviation']))
                    for t in teams['teams']]

    for team_id, abbr in sorted(all_team_ids, key=lambda x: x[1]):
        try:
            roster = statsapi.get('team_roster', {
                'teamId': team_id,
                'rosterType': '40Man',
            })
        except Exception as e:
            logger.warning(f"Could not fetch roster for {abbr} (id={team_id}): {e}")
            continue

        il_players = []
        for p in roster.get('roster', []):
            if 'Injured' in p['status'].get('description', ''):
                il_players.append({
                    'mlb_id': p['person']['id'],
                    'name': p['person']['fullName'],
                    'position': p['position']['abbreviation'],
                    'il_type': p['status']['description'],
                    'is_pitcher': p['position']['abbreviation'] == 'P',
                })

        if il_players:
            il_rosters[abbr] = il_players

        time.sleep(0.1)  # Rate-limit API calls

    total = sum(len(v) for v in il_rosters.values())
    logger.info(f"Found {total} IL players across {len(il_rosters)} teams")
    return il_rosters


def build_war_lookup(season):
    """
    Build MLB player ID → WAR lookup from FanGraphs via pybaseball.

    Loads both current-year and prior-year WAR. For players without
    current-year stats (injured early), falls back to prior-year WAR.

    Args:
        season: MLB season year

    Returns:
        {mlb_player_id: war_value}
    """
    # Load current season WAR
    try:
        bat = batting_stats(season, qual=0)
        bat_war = dict(zip(bat['IDfg'], bat['WAR']))
    except Exception as e:
        logger.warning(f"Could not load {season} batting stats: {e}")
        bat_war = {}

    try:
        pit = pitching_stats(season, qual=0)
        pit_war = dict(zip(pit['IDfg'], pit['WAR']))
    except Exception as e:
        logger.warning(f"Could not load {season} pitching stats: {e}")
        pit_war = {}

    # Load prior season WAR as fallback
    prior = season - 1
    try:
        bat_prev = batting_stats(prior, qual=0)
        bat_war_prev = dict(zip(bat_prev['IDfg'], bat_prev['WAR']))
    except Exception:
        bat_war_prev = {}

    try:
        pit_prev = pitching_stats(prior, qual=0)
        pit_war_prev = dict(zip(pit_prev['IDfg'], pit_prev['WAR']))
    except Exception:
        pit_war_prev = {}

    # Merge current-year FanGraphs WAR (take max of batting/pitching)
    fg_war = {}
    for fg_id in set(list(bat_war.keys()) + list(pit_war.keys())):
        b = bat_war.get(fg_id)
        p = pit_war.get(fg_id)
        if b is not None and p is not None:
            fg_war[fg_id] = max(b, p)
        else:
            fg_war[fg_id] = b if b is not None else p

    # Same for prior year
    fg_war_prev = {}
    for fg_id in set(list(bat_war_prev.keys()) + list(pit_war_prev.keys())):
        b = bat_war_prev.get(fg_id)
        p = pit_war_prev.get(fg_id)
        if b is not None and p is not None:
            fg_war_prev[fg_id] = max(b, p)
        else:
            fg_war_prev[fg_id] = b if b is not None else p

    logger.info(f"Loaded WAR: {len(fg_war)} players ({season}), {len(fg_war_prev)} players ({prior})")
    return fg_war, fg_war_prev


def _crossref_ids(mlb_ids):
    """Map MLB API player IDs to FanGraphs IDs via pybaseball."""
    if not mlb_ids:
        return {}
    xref = playerid_reverse_lookup(list(mlb_ids), key_type='mlbam')
    mapping = {}
    for _, row in xref.iterrows():
        fg_id = row.get('key_fangraphs')
        if fg_id and fg_id != -1:
            mapping[int(row['key_mlbam'])] = int(fg_id)
    logger.info(f"Cross-referenced {len(mapping)}/{len(mlb_ids)} player IDs")
    return mapping


def compute_injury_adjustments(il_rosters, fg_war, fg_war_prev, id_map,
                               war_to_elo=None):
    """
    Compute per-team ELO adjustments from injury data.

    For each team, sums the positive WAR of all IL players (negative WAR
    players aren't hurting you by being absent) and converts to an ELO penalty.

    Args:
        il_rosters: {team_abbr: [player_dicts]} from fetch_il_rosters()
        fg_war: {fg_id: war} current season
        fg_war_prev: {fg_id: war} prior season (fallback)
        id_map: {mlb_id: fg_id} from _crossref_ids()
        war_to_elo: ELO points per 1.0 WAR (default from config)

    Returns:
        list of team adjustment dicts for S3 output
    """
    if war_to_elo is None:
        war_to_elo = INJURY_WAR_TO_ELO

    adjustments = []

    for abbr, players in sorted(il_rosters.items()):
        total_war_lost = 0.0
        player_details = []

        for p in players:
            fg_id = id_map.get(p['mlb_id'])
            war = None
            source = 'unknown'

            if fg_id is not None:
                # Try current year first
                if fg_id in fg_war:
                    war = fg_war[fg_id]
                    source = 'current'
                # Fall back to prior year
                elif fg_id in fg_war_prev:
                    war = fg_war_prev[fg_id]
                    source = 'prior_year'

            # Only count positive WAR as "lost"
            war_impact = max(war, 0.0) if war is not None else 0.0
            total_war_lost += war_impact

            player_details.append({
                'name': p['name'],
                'war': round(war, 1) if war is not None else None,
                'war_source': source,
                'position': p['position'],
                'il_type': p['il_type'],
            })

        elo_adj = -1 * total_war_lost * war_to_elo

        adjustments.append({
            'team': abbr,
            'elo_adjustment': round(elo_adj, 1),
            'war_lost': round(total_war_lost, 1),
            'il_count': len(players),
            'players': player_details,
        })

    return adjustments


def fetch_injury_elo_adjustments(season=None):
    """
    Top-level convenience function: fetch IL rosters, compute WAR, return adjustments.

    Returns a dict ready to write to S3 as injury-adjustments-latest.json.

    Args:
        season: MLB season year (defaults to SEASON_YEAR from config)

    Returns:
        {
            'updated': ISO timestamp,
            'season': int,
            'adjustments': [{'team', 'elo_adjustment', 'war_lost', 'il_count', 'players'}, ...]
        }
    """
    if season is None:
        season = SEASON_YEAR

    # Step 1: Fetch IL rosters
    il_rosters = fetch_il_rosters(season)

    # Step 2: Collect all MLB IDs for cross-referencing
    all_mlb_ids = set()
    for players in il_rosters.values():
        for p in players:
            all_mlb_ids.add(p['mlb_id'])

    # Step 3: Build WAR lookup
    fg_war, fg_war_prev = build_war_lookup(season)

    # Step 4: Cross-reference MLB IDs → FanGraphs IDs
    id_map = _crossref_ids(all_mlb_ids)

    # Step 5: Compute adjustments
    adjustments = compute_injury_adjustments(il_rosters, fg_war, fg_war_prev, id_map)

    total_teams = sum(1 for a in adjustments if a['elo_adjustment'] != 0)
    logger.info(f"Computed injury adjustments: {total_teams} teams with non-zero impact")

    return {
        'updated': datetime.utcnow().isoformat(),
        'season': season,
        'adjustments': adjustments,
    }
