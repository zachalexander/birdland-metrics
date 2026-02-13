"""
mlb-preseason-adjustment — Adjust ELO ratings for offseason roster changes.

Fetches offseason transactions from the MLB Stats API, computes simplified WAR
for each player from bulk batting/pitching stats, and adjusts the end-of-season
ELO baseline before Opening Day.

WAR computation (no pybaseball/FanGraphs dependency):
- Batting WAR: wOBA-based offensive value from MLB bulk hitting stats
- Pitching WAR: FIP-based value from MLB bulk pitching stats
- Defensive value is not captured (averages out across team-level sums)

Scheduled via EventBridge to run weekly in March. Each run is idempotent:
reads the original (raw) baseline and recomputes from scratch, so late-breaking
trades are always reflected.
"""
import json
import logging
import os
import requests
import pandas as pd
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from mlb_common.config import (
    ELO_BUCKET, ELO_PRIOR_SEASON_KEY, ELO_TABLE,
    SEASON_YEAR, PRIOR_SEASON_YEAR, MLB_PITCHING_STATS_URL,
)
from mlb_common.aws_helpers import (
    read_csv_from_s3, write_csv_to_s3, write_json_to_s3, dynamo_put_item,
)
from mlb_common.team_codes import SCHEDULE_TO_ELO_MAP

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---

WAR_TO_ELO = float(os.getenv('WAR_TO_ELO', '5.5'))
WAR_YEARS = int(os.getenv('WAR_YEARS', '3'))

# wOBA linear weights (standard FanGraphs values, stable across seasons)
WOBA_BB = 0.69
WOBA_HBP = 0.72
WOBA_1B = 0.89
WOBA_2B = 1.27
WOBA_3B = 1.62
WOBA_HR = 2.10
WOBA_SCALE = 1.15  # wOBA-to-runs conversion denominator
RUNS_PER_WIN = 10.0
REPLACEMENT_RUNS_PER_600PA = 20.0  # ~2 WAR per 600 PA replacement level
REPLACEMENT_FIP = 5.5  # approximate replacement-level FIP

MLB_HITTING_STATS_URL = 'https://statsapi.mlb.com/api/v1/stats'

# MLB team ID -> schedule abbreviation
TEAM_ID_TO_ABBR = {
    108: 'LAA', 109: 'AZ', 110: 'BAL', 111: 'BOS', 112: 'CHC',
    113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET', 117: 'HOU',
    118: 'KC', 119: 'LAD', 120: 'WSH', 121: 'NYM', 133: 'ATH',
    134: 'PIT', 135: 'SD', 136: 'SEA', 137: 'SF', 138: 'STL',
    139: 'TB', 140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI',
    144: 'ATL', 145: 'CWS', 146: 'MIA', 147: 'NYY', 158: 'MIL',
}

# Transaction types that move players between organizations
GAIN_TYPES = {'SFA', 'CLW', 'R5', 'R5M'}
LOSS_TYPES = {'DFA', 'REL'}


def standardize_team(code):
    return SCHEDULE_TO_ELO_MAP.get(code, code)


# --- WAR Computation ---

def fetch_batting_war(season):
    """Compute simplified batting WAR from MLB Stats API bulk hitting stats."""
    resp = requests.get(MLB_HITTING_STATS_URL, params={
        'stats': 'season', 'group': 'hitting', 'season': season,
        'sportId': 1, 'limit': 2000, 'playerPool': 'ALL',
    }, timeout=30)
    resp.raise_for_status()
    splits = resp.json().get('stats', [{}])[0].get('splits', [])

    # Compute league-wide wOBA from all batters
    lg_num = 0.0
    lg_denom = 0.0
    players = []
    for s in splits:
        stat = s.get('stat', {})
        player = s.get('player', {})
        pa = int(stat.get('plateAppearances', 0))
        if pa < 1:
            continue

        ab = int(stat.get('atBats', 0))
        h = int(stat.get('hits', 0))
        doubles = int(stat.get('doubles', 0))
        triples = int(stat.get('triples', 0))
        hr = int(stat.get('homeRuns', 0))
        bb = int(stat.get('baseOnBalls', 0))
        ibb = int(stat.get('intentionalWalks', 0))
        hbp = int(stat.get('hitByPitch', 0))
        sf = int(stat.get('sacFlies', 0))
        singles = h - doubles - triples - hr

        nibb = bb - ibb
        woba_num = (WOBA_BB * nibb + WOBA_HBP * hbp + WOBA_1B * singles +
                    WOBA_2B * doubles + WOBA_3B * triples + WOBA_HR * hr)
        woba_denom = ab + bb + sf + hbp
        if woba_denom > 0:
            lg_num += woba_num
            lg_denom += woba_denom
            players.append({
                'id': player.get('id'),
                'name': player.get('fullName', ''),
                'pa': pa,
                'woba_num': woba_num,
                'woba_denom': woba_denom,
            })

    lg_woba = lg_num / lg_denom if lg_denom > 0 else 0.320

    # Compute individual batting WAR
    war_dict = {}
    for p in players:
        woba = p['woba_num'] / p['woba_denom']
        wraa = ((woba - lg_woba) / WOBA_SCALE) * p['pa']
        replacement = REPLACEMENT_RUNS_PER_600PA * (p['pa'] / 600)
        war = (wraa + replacement) / RUNS_PER_WIN
        war_dict[p['id']] = {'war': round(war, 2), 'name': p['name'], 'type': 'batting'}

    logger.info(f"Computed batting WAR for {len(war_dict)} players ({season}, lgwOBA={lg_woba:.3f})")
    return war_dict


def fetch_pitching_war(season):
    """Compute simplified pitching WAR from FIP via MLB Stats API."""
    resp = requests.get(MLB_PITCHING_STATS_URL, params={
        'stats': 'season', 'group': 'pitching', 'season': season,
        'sportId': 1, 'limit': 2000, 'playerPool': 'ALL',
    }, timeout=30)
    resp.raise_for_status()
    splits = resp.json().get('stats', [{}])[0].get('splits', [])

    # Compute league FIP constant (cFIP) from all pitchers
    total_ip, total_hr, total_bb, total_hbp, total_k, total_er = 0, 0, 0, 0, 0, 0.0
    pitchers = []
    for s in splits:
        stat = s.get('stat', {})
        player = s.get('player', {})
        ip_str = stat.get('inningsPitched', '0')
        ip = float(ip_str) if ip_str else 0.0
        if ip < 1.0:
            continue

        hr = int(stat.get('homeRuns', 0))
        bb = int(stat.get('baseOnBalls', 0))
        hbp = int(stat.get('hitByPitch', 0))
        k = int(stat.get('strikeOuts', 0))
        era = float(stat.get('era', '0'))

        total_ip += ip
        total_hr += hr
        total_bb += bb
        total_hbp += hbp
        total_k += k
        total_er += era * ip / 9.0
        pitchers.append({
            'id': player.get('id'),
            'name': player.get('fullName', ''),
            'ip': ip, 'hr': hr, 'bb': bb, 'hbp': hbp, 'k': k,
        })

    lg_era = total_er * 9.0 / total_ip if total_ip > 0 else 4.0
    cfip = lg_era - (13 * total_hr + 3 * (total_bb + total_hbp) - 2 * total_k) / total_ip

    # Compute individual pitching WAR
    war_dict = {}
    for p in pitchers:
        fip = (13 * p['hr'] + 3 * (p['bb'] + p['hbp']) - 2 * p['k']) / p['ip'] + cfip
        innings_fraction = p['ip'] / 9.0
        runs_saved = (REPLACEMENT_FIP - fip) * innings_fraction
        war = runs_saved / RUNS_PER_WIN
        war_dict[p['id']] = {'war': round(war, 2), 'name': p['name'], 'type': 'pitching'}

    logger.info(f"Computed pitching WAR for {len(war_dict)} players ({season}, cFIP={cfip:.3f})")
    return war_dict


def build_war_lookup(seasons):
    """
    Build MLB player ID -> WAR mapping averaged across multiple seasons.
    For two-way players, uses the higher of batting or pitching WAR per season.
    """
    player_wars = defaultdict(list)  # player_id -> [war_per_season]
    player_names = {}

    for season in seasons:
        bat_war = fetch_batting_war(season)
        pit_war = fetch_pitching_war(season)

        # Merge: for each player, take max of batting/pitching WAR this season
        all_ids = set(bat_war.keys()) | set(pit_war.keys())
        for pid in all_ids:
            b = bat_war.get(pid, {}).get('war', -999)
            p = pit_war.get(pid, {}).get('war', -999)
            best = max(b, p)
            player_wars[pid].append(best)
            if pid in bat_war:
                player_names[pid] = bat_war[pid]['name']
            elif pid in pit_war:
                player_names[pid] = pit_war[pid]['name']

    # Average across seasons
    war_lookup = {}
    for pid, wars in player_wars.items():
        war_lookup[pid] = {
            'war': round(sum(wars) / len(wars), 2),
            'name': player_names.get(pid, ''),
        }

    logger.info(f"WAR lookup: {len(war_lookup)} players across {len(seasons)} seasons")
    return war_lookup


# --- Transaction Processing ---

def fetch_offseason_transactions():
    """Fetch roster-changing transactions from the MLB Stats API."""
    # Offseason window: November 1 through March 20
    start = f'{PRIOR_SEASON_YEAR}-11-01'
    end = f'{SEASON_YEAR}-03-20'

    resp = requests.get('https://statsapi.mlb.com/api/v1/transactions', params={
        'startDate': start,
        'endDate': end,
        'sportId': 1,
    }, timeout=30)
    resp.raise_for_status()
    raw_txns = resp.json().get('transactions', [])
    logger.info(f"Fetched {len(raw_txns)} raw transactions ({start} to {end})")

    moves = []
    for t in raw_txns:
        player = t.get('person')
        if not player:
            continue

        type_code = t.get('typeCode', '')
        desc = t.get('description', '')
        to_team = t.get('toTeam', {})
        from_team = t.get('fromTeam', {})
        to_id = to_team.get('id')
        from_id = from_team.get('id')

        if type_code == 'TR':
            if from_id in TEAM_ID_TO_ABBR and to_id in TEAM_ID_TO_ABBR:
                moves.append({
                    'player_id': player['id'],
                    'player_name': player.get('fullName', ''),
                    'from_team': TEAM_ID_TO_ABBR[from_id],
                    'to_team': TEAM_ID_TO_ABBR[to_id],
                    'type': 'trade',
                })

        elif type_code in GAIN_TYPES:
            if to_id not in TEAM_ID_TO_ABBR:
                continue
            if type_code == 'SFA' and 'minor league' in desc.lower():
                continue
            moves.append({
                'player_id': player['id'],
                'player_name': player.get('fullName', ''),
                'from_team': None,
                'to_team': TEAM_ID_TO_ABBR[to_id],
                'type': t.get('typeDesc', type_code),
            })

        elif type_code in LOSS_TYPES:
            if to_id not in TEAM_ID_TO_ABBR:
                continue
            moves.append({
                'player_id': player['id'],
                'player_name': player.get('fullName', ''),
                'from_team': TEAM_ID_TO_ABBR[to_id],
                'to_team': None,
                'type': t.get('typeDesc', type_code),
            })

    logger.info(f"Roster-changing moves: {len(moves)}")
    return moves


def compute_team_adjustments(moves, war_lookup):
    """Sum WAR gained and lost per team, return net ELO adjustment."""
    team_gains = defaultdict(float)
    team_losses = defaultdict(float)

    for move in moves:
        pid = move['player_id']
        war = war_lookup.get(pid, {}).get('war', 0.0)

        if move['to_team']:
            team_gains[move['to_team']] += war
        if move['from_team']:
            team_losses[move['from_team']] += war

    all_teams = set(list(team_gains.keys()) + list(team_losses.keys()))
    adjustments = {}
    for team in sorted(all_teams):
        net_war = team_gains[team] - team_losses[team]
        adjustments[team] = {
            'net_war': round(net_war, 2),
            'elo_adj': round(net_war * WAR_TO_ELO, 1),
            'war_gained': round(team_gains[team], 2),
            'war_lost': round(team_losses[team], 2),
        }

    return adjustments


# --- ELO Baseline Adjustment ---

def apply_adjustments(adjustments):
    """
    Read end-of-season ELO baseline, apply WAR-based adjustments, write back.

    Idempotent: always reads from the raw (un-adjusted) backup file,
    so repeated runs don't compound the adjustment.
    """
    raw_key = ELO_PRIOR_SEASON_KEY.replace('.csv', '_raw.csv')

    # Try to read the raw (original) baseline
    try:
        baseline_df = read_csv_from_s3(ELO_BUCKET, raw_key)
        logger.info(f"Read raw baseline from {raw_key}")
    except Exception:
        # First run — read original and create backup
        baseline_df = read_csv_from_s3(ELO_BUCKET, ELO_PRIOR_SEASON_KEY)
        write_csv_to_s3(baseline_df, ELO_BUCKET, raw_key)
        logger.info(f"Backed up original baseline to {raw_key}")

    baseline_df['team'] = baseline_df['team'].apply(standardize_team)

    # Apply adjustments
    results = []
    for _, row in baseline_df.iterrows():
        team = row['team']
        base_elo = float(row['elo'])
        adj = adjustments.get(team, {})
        elo_shift = adj.get('elo_adj', 0.0)
        new_elo = round(base_elo + elo_shift, 2)

        results.append({'team': team, 'elo': new_elo})

        # Update DynamoDB (Decimal required for numeric values)
        dynamo_put_item(ELO_TABLE, {
            'team': team,
            'elo': Decimal(str(new_elo)),
            'last_updated': datetime.utcnow().isoformat(),
            'preseason_adjustment': Decimal(str(round(elo_shift, 1))),
        })

    # Overwrite the baseline file with adjusted values
    adjusted_df = pd.DataFrame(results)
    write_csv_to_s3(adjusted_df, ELO_BUCKET, ELO_PRIOR_SEASON_KEY)
    logger.info(f"Wrote adjusted baseline to {ELO_PRIOR_SEASON_KEY}")

    # Write summary JSON for frontend
    summary = []
    for _, row in adjusted_df.sort_values('elo', ascending=False).iterrows():
        team = row['team']
        adj = adjustments.get(team, {})
        summary.append({
            'team': team,
            'preseason_elo': row['elo'],
            'elo_adjustment': adj.get('elo_adj', 0.0),
            'net_war': adj.get('net_war', 0.0),
        })

    write_json_to_s3({
        'updated': datetime.utcnow().isoformat(),
        'season': SEASON_YEAR,
        'war_years': WAR_YEARS,
        'war_to_elo': WAR_TO_ELO,
        'teams': summary,
    }, ELO_BUCKET, 'preseason-adjustment-latest.json')

    return adjusted_df


def lambda_handler(event=None, context=None):
    seasons = list(range(PRIOR_SEASON_YEAR - WAR_YEARS + 1, PRIOR_SEASON_YEAR + 1))
    logger.info(f"Preseason adjustment for {SEASON_YEAR} (WAR from {seasons})")

    # Step 1: Compute WAR lookup from MLB Stats API
    war_lookup = build_war_lookup(seasons)

    # Step 2: Fetch offseason transactions
    moves = fetch_offseason_transactions()

    # Step 3: Compute team-level WAR adjustments
    adjustments = compute_team_adjustments(moves, war_lookup)

    # Log top movers
    sorted_adj = sorted(adjustments.items(), key=lambda x: x[1]['elo_adj'], reverse=True)
    for team, adj in sorted_adj[:5]:
        logger.info(f"  {team}: WAR {adj['net_war']:+.1f} -> ELO {adj['elo_adj']:+.1f}")
    logger.info("  ...")
    for team, adj in sorted_adj[-5:]:
        logger.info(f"  {team}: WAR {adj['net_war']:+.1f} -> ELO {adj['elo_adj']:+.1f}")

    # Step 4: Apply to ELO baseline
    adjusted_df = apply_adjustments(adjustments)

    return {
        'statusCode': 200,
        'body': json.dumps(f"Adjusted {len(adjusted_df)} teams for {SEASON_YEAR} preseason"),
    }
