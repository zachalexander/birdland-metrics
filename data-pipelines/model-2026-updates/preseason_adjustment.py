# -*- coding: utf-8 -*-
"""
preseason_adjustment.py — Adjust ELO ratings for offseason roster changes.

Computes net WAR gained/lost per team from offseason transactions (trades,
free agent signings, waiver claims, releases) and converts to an ELO shift.

Run once before Opening Day:
    python3 preseason_adjustment.py --season 2026

Data sources:
    - MLB Stats API /transactions endpoint (trades, signings, etc.)
    - pybaseball for prior-season WAR (FanGraphs fWAR)
    - End-of-prior-season ELO baseline CSV

Output:
    - preseason_elo_{season}.csv — adjusted ELO ratings for each team
    - offseason_transactions_{season}.csv — detailed transaction log with WAR
"""
import argparse
import os
import sys
import requests
import pandas as pd
from collections import defaultdict
from pybaseball import batting_stats, pitching_stats, playerid_reverse_lookup

# --- Configuration ---

# ELO points per 1.0 WAR of roster change
# Derivation: ~80 ELO separates 81-win and 95-win teams (14 wins),
# so 1 win ≈ 5.7 ELO. 1 WAR ≈ 1 win above replacement.
WAR_TO_ELO = 5.5

# MLB team ID to schedule abbreviation mapping
TEAM_ID_TO_ABBR = {
    108: 'LAA', 109: 'AZ', 110: 'BAL', 111: 'BOS', 112: 'CHC',
    113: 'CIN', 114: 'CLE', 115: 'COL', 116: 'DET', 117: 'HOU',
    118: 'KC', 119: 'LAD', 120: 'WSH', 121: 'NYM', 133: 'ATH',
    134: 'PIT', 135: 'SD', 136: 'SEA', 137: 'SF', 138: 'STL',
    139: 'TB', 140: 'TEX', 141: 'TOR', 142: 'MIN', 143: 'PHI',
    144: 'ATL', 145: 'CWS', 146: 'MIA', 147: 'NYY', 158: 'MIL',
}

# Offseason window (approximate — adjust per year)
OFFSEASON_WINDOWS = {
    2026: ('2025-11-01', '2026-03-20'),
    2027: ('2026-11-01', '2027-03-20'),
}


# Prospect rank -> expected first-year MLB WAR conversion table.
# Based on historical prospect-to-MLB production research (BA/FanGraphs).
# Each tuple is (max_rank, expected_war).
PROSPECT_RANK_TO_WAR = [
    (5,   2.0),
    (10,  1.5),
    (25,  1.0),
    (50,  0.7),
    (100, 0.4),
]
PROSPECT_RANK_DEFAULT_WAR = 0.2  # rank 101+


def prospect_rank_to_war(rank):
    """Convert a consensus prospect ranking to expected first-year WAR."""
    for max_rank, war in PROSPECT_RANK_TO_WAR:
        if rank <= max_rank:
            return war
    return PROSPECT_RANK_DEFAULT_WAR


def load_war_overrides(overrides_path):
    """
    Load WAR overrides from a CSV file.

    CSV columns:
        player_id (int, required): MLB player ID
        player_name (str): for readability
        war_override (float, optional): direct WAR override value
        prospect_rank (int, optional): consensus prospect ranking (converted to WAR)
        source (str, optional): e.g. "NPB translation", "MLB Pipeline Top 100"

    If war_override is provided, it takes priority. Otherwise prospect_rank
    is converted using the PROSPECT_RANK_TO_WAR table.

    Returns: dict of {mlb_player_id: war_value}
    """
    if not os.path.exists(overrides_path):
        return {}

    df = pd.read_csv(overrides_path)
    if 'player_id' not in df.columns:
        print(f"  WARNING: overrides CSV missing 'player_id' column, skipping")
        return {}

    overrides = {}
    for _, row in df.iterrows():
        pid = int(row['player_id'])
        name = row.get('player_name', pid)

        if 'war_override' in row and pd.notna(row.get('war_override')):
            war = float(row['war_override'])
            overrides[pid] = war
        elif 'prospect_rank' in row and pd.notna(row.get('prospect_rank')):
            rank = int(row['prospect_rank'])
            war = prospect_rank_to_war(rank)
            overrides[pid] = war
        else:
            continue

        source = row.get('source', '') if 'source' in row and pd.notna(row.get('source')) else ''
        print(f"  Override: {str(name):<25s} -> {war:+.1f} WAR  ({source})")

    return overrides


def fetch_offseason_transactions(prior_season):
    """
    Fetch roster-changing transactions from the MLB API.

    Returns a list of dicts: {player_id, player_name, from_team, to_team, type, description}
    """
    season = prior_season + 1
    start, end = OFFSEASON_WINDOWS.get(season, (f'{prior_season}-11-01', f'{season}-03-20'))

    print(f"Fetching transactions from {start} to {end}...")
    resp = requests.get('https://statsapi.mlb.com/api/v1/transactions', params={
        'startDate': start,
        'endDate': end,
        'sportId': 1,
    }, timeout=30)
    resp.raise_for_status()
    raw_txns = resp.json().get('transactions', [])
    print(f"  Raw transactions: {len(raw_txns)}")

    # Transaction types that move players between organizations
    GAIN_TYPES = {'SFA', 'CLW', 'R5', 'R5M'}
    LOSS_TYPES = {'DFA', 'REL'}
    TRADE_TYPE = 'TR'

    moves = []
    for t in raw_txns:
        player = t.get('person')
        if not player:
            continue

        type_code = t.get('typeCode', '')
        desc = t.get('description', '')
        player_id = player['id']
        player_name = player.get('fullName', '')
        to_team = t.get('toTeam', {})
        from_team = t.get('fromTeam', {})
        to_id = to_team.get('id')
        from_id = from_team.get('id')

        if type_code == TRADE_TYPE:
            if from_id in TEAM_ID_TO_ABBR and to_id in TEAM_ID_TO_ABBR:
                moves.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'from_team': TEAM_ID_TO_ABBR[from_id],
                    'to_team': TEAM_ID_TO_ABBR[to_id],
                    'type': 'trade',
                    'description': desc,
                })

        elif type_code in GAIN_TYPES:
            if to_id not in TEAM_ID_TO_ABBR:
                continue
            # Skip minor league signings
            if type_code == 'SFA' and 'minor league' in desc.lower():
                continue
            moves.append({
                'player_id': player_id,
                'player_name': player_name,
                'from_team': None,
                'to_team': TEAM_ID_TO_ABBR[to_id],
                'type': t.get('typeDesc', type_code),
                'description': desc,
            })

        elif type_code in LOSS_TYPES:
            if to_id not in TEAM_ID_TO_ABBR:
                continue
            # For DFA/REL, toTeam is the team the player is LEAVING
            moves.append({
                'player_id': player_id,
                'player_name': player_name,
                'from_team': TEAM_ID_TO_ABBR[to_id],
                'to_team': None,
                'type': t.get('typeDesc', type_code),
                'description': desc,
            })

    print(f"  Roster-changing moves: {len(moves)}")
    return moves


def build_war_lookup(prior_season, years=1):
    """
    Build a mapping of MLB player ID -> WAR.

    Uses pybaseball to get FanGraphs WAR, then maps FanGraphs IDs to MLB IDs.
    For two-way players, uses the higher of batting or pitching WAR.

    Args:
        prior_season: most recent completed season
        years: number of seasons to average (1=single season, 2-3=multi-year avg)
    """
    seasons = list(range(prior_season - years + 1, prior_season + 1))
    print(f"\nLoading WAR data from FanGraphs for {seasons}...")

    # Collect FanGraphs ID -> [WAR values per season]
    fg_war_by_season = defaultdict(list)
    all_fg_ids = set()

    for season in seasons:
        bat = batting_stats(season, qual=0)
        pit = pitching_stats(season, qual=0)
        print(f"  {season}: {len(bat)} batters, {len(pit)} pitchers")

        # Take max of batting/pitching WAR per player per season
        season_war = {}
        for _, row in bat.iterrows():
            fg_id = int(row['IDfg'])
            war = float(row['WAR'])
            season_war[fg_id] = max(season_war.get(fg_id, -999), war)
        for _, row in pit.iterrows():
            fg_id = int(row['IDfg'])
            war = float(row['WAR'])
            season_war[fg_id] = max(season_war.get(fg_id, -999), war)

        for fg_id, war in season_war.items():
            fg_war_by_season[fg_id].append(war)
            all_fg_ids.add(fg_id)

    # Average WAR across available seasons
    fg_war = {}
    for fg_id, wars in fg_war_by_season.items():
        fg_war[fg_id] = sum(wars) / len(wars)

    # Map FanGraphs IDs to MLB IDs
    print("  Building FanGraphs -> MLB ID mapping...")
    lookup = playerid_reverse_lookup(list(all_fg_ids), key_type='fangraphs')
    matched = lookup[lookup['key_mlbam'] > 0]
    print(f"  Matched {len(matched)} of {len(all_fg_ids)} players to MLB IDs")

    # Build MLB ID -> WAR mapping
    mlb_war = {}
    for _, row in matched.iterrows():
        mlb_id = int(row['key_mlbam'])
        fg_id = int(row['key_fangraphs'])
        if fg_id in fg_war:
            mlb_war[mlb_id] = fg_war[fg_id]

    return mlb_war


def build_projected_war_lookup(prior_season, years=3):
    """
    Build a Marcel-style projected WAR lookup: MLB player ID -> projected WAR.

    Marcel methodology (Tom Tango):
      1. 5/4/3 recency weighting across up to 3 seasons
      2. Regression to the mean based on playing time
      3. Age adjustment: +0.1/yr under 28, -0.1/yr over 28, capped at ±0.5

    Args:
        prior_season: most recent completed season
        years: number of seasons to look back (default 3)
    """
    seasons = list(range(prior_season - years + 1, prior_season + 1))
    weights = [3, 4, 5][-len(seasons):]  # oldest=3, newest=5
    print(f"\nBuilding Marcel projections from {seasons} (weights {weights})...")

    # Collect per-season WAR + playing time keyed by FanGraphs ID
    fg_season_data = defaultdict(dict)  # fg_id -> {season: {war, pa, ip}}
    all_fg_ids = set()

    for season in seasons:
        bat = batting_stats(season, qual=0)
        pit = pitching_stats(season, qual=0)
        print(f"  {season}: {len(bat)} batters, {len(pit)} pitchers")

        # Track batting stats
        for _, row in bat.iterrows():
            fg_id = int(row['IDfg'])
            all_fg_ids.add(fg_id)
            existing = fg_season_data[fg_id].get(season, {'war': -999, 'pa': 0, 'ip': 0})
            bat_war = float(row['WAR'])
            pa = int(row['PA']) if 'PA' in row and pd.notna(row['PA']) else 0
            if bat_war > existing['war']:
                existing['war'] = bat_war
            existing['pa'] = max(existing['pa'], pa)
            fg_season_data[fg_id][season] = existing

        # Track pitching stats
        for _, row in pit.iterrows():
            fg_id = int(row['IDfg'])
            all_fg_ids.add(fg_id)
            existing = fg_season_data[fg_id].get(season, {'war': -999, 'pa': 0, 'ip': 0})
            pit_war = float(row['WAR'])
            ip = float(row['IP']) if 'IP' in row and pd.notna(row['IP']) else 0
            if pit_war > existing['war']:
                existing['war'] = pit_war
            existing['ip'] = max(existing['ip'], ip)
            fg_season_data[fg_id][season] = existing

    # Map FanGraphs IDs to MLB IDs + get birth year for age adjustment
    print("  Building FanGraphs -> MLB ID mapping (with birth years)...")
    lookup = playerid_reverse_lookup(list(all_fg_ids), key_type='fangraphs')
    matched = lookup[lookup['key_mlbam'] > 0]
    print(f"  Matched {len(matched)} of {len(all_fg_ids)} players")

    # Build birth year map: fg_id -> birth_year
    fg_birth_year = {}
    for _, row in matched.iterrows():
        fg_id = int(row['key_fangraphs'])
        if 'birth_year' in row and pd.notna(row['birth_year']):
            fg_birth_year[fg_id] = int(row['birth_year'])

    # Compute Marcel projection per player
    projection_season = prior_season + 1
    mlb_projected = {}

    for _, row in matched.iterrows():
        mlb_id = int(row['key_mlbam'])
        fg_id = int(row['key_fangraphs'])
        player_seasons = fg_season_data.get(fg_id, {})
        if not player_seasons:
            continue

        # 5/4/3 weighted WAR + weighted PA/IP
        weighted_war = 0.0
        total_weight = 0.0
        weighted_pa = 0.0
        weighted_ip = 0.0
        for season, w in zip(seasons, weights):
            if season in player_seasons:
                d = player_seasons[season]
                war_val = d['war'] if d['war'] > -999 else 0.0
                weighted_war += w * war_val
                total_weight += w
                weighted_pa += w * d['pa']
                weighted_ip += w * d['ip']

        if total_weight == 0:
            continue

        weighted_war /= total_weight
        weighted_pa /= total_weight
        weighted_ip /= total_weight

        # Regression to the mean
        # Determine if primarily a pitcher (more IP than PA-equivalent)
        if weighted_ip > weighted_pa / 4:
            reliability = weighted_ip / (weighted_ip + 400)
        else:
            reliability = weighted_pa / (weighted_pa + 1200)

        projected = reliability * weighted_war

        # Age adjustment
        birth_year = fg_birth_year.get(fg_id)
        if birth_year:
            age = projection_season - birth_year
            if age < 28:
                age_adj = min(0.1 * (28 - age), 0.5)
            elif age > 28:
                age_adj = max(-0.1 * (age - 28), -0.5)
            else:
                age_adj = 0.0
            projected += age_adj

        mlb_projected[mlb_id] = projected

    print(f"  Marcel projections computed for {len(mlb_projected)} players")
    return mlb_projected


def compute_net_war_changes(moves, war_lookup, war_projected=None, blend_weight=0.5):
    """
    Compute net WAR gained and lost per team.

    Args:
        moves: list of transaction dicts
        war_lookup: MLB ID -> historical WAR (simple average)
        war_projected: MLB ID -> Marcel projected WAR (optional)
        blend_weight: weight for projected WAR in blend (0.0 = all historical, 1.0 = all projected)

    Returns:
        team_war_delta: {team_abbr: net_war_change} (uses blended WAR)
        annotated_moves: list of moves with war_historical, war_projected, war_blended, war
    """
    team_gains = defaultdict(float)
    team_losses = defaultdict(float)
    annotated = []

    for move in moves:
        pid = move['player_id']
        hist = war_lookup.get(pid, 0.0)
        move['war_historical'] = hist

        if war_projected is not None:
            proj = war_projected.get(pid, 0.0)
            blended = blend_weight * proj + (1 - blend_weight) * hist
            move['war_projected'] = proj
            move['war_blended'] = blended
            move['war'] = blended
        else:
            move['war_projected'] = None
            move['war_blended'] = None
            move['war'] = hist

        war = move['war']
        if move['to_team']:
            team_gains[move['to_team']] += war
        if move['from_team']:
            team_losses[move['from_team']] += war

        annotated.append(move)

    # Net change = gains - losses
    all_teams = set(list(team_gains.keys()) + list(team_losses.keys()))
    team_delta = {}
    for team in sorted(all_teams):
        gained = team_gains[team]
        lost = team_losses[team]
        team_delta[team] = gained - lost

    return team_delta, annotated


def apply_elo_adjustment(elo_baseline_path, team_delta, war_to_elo=WAR_TO_ELO):
    """
    Apply WAR-based ELO adjustments to end-of-season baseline.

    Args:
        elo_baseline_path: path to CSV with columns [team, elo]
        team_delta: {team: net_war_change}
        war_to_elo: ELO points per 1.0 WAR

    Returns:
        DataFrame with original ELO, adjustment, and preseason ELO
    """
    baseline = pd.read_csv(elo_baseline_path)
    rows = []
    for _, row in baseline.iterrows():
        team = row['team']
        base_elo = row['elo']
        net_war = team_delta.get(team, 0.0)
        adjustment = round(net_war * war_to_elo, 1)
        rows.append({
            'team': team,
            'elo_end_of_season': round(base_elo, 2),
            'net_war_change': round(net_war, 1),
            'elo_adjustment': adjustment,
            'preseason_elo': round(base_elo + adjustment, 2),
        })

    df = pd.DataFrame(rows).sort_values('preseason_elo', ascending=False)
    return df


def main():
    parser = argparse.ArgumentParser(description='Preseason ELO adjustment from offseason transactions')
    parser.add_argument('--season', type=int, default=2026, help='Upcoming season year (default: 2026)')
    parser.add_argument('--war-to-elo', type=float, default=WAR_TO_ELO, help=f'ELO points per 1 WAR (default: {WAR_TO_ELO})')
    parser.add_argument('--years', type=int, default=1,
                        help='Number of seasons to average WAR over (default: 1)')
    parser.add_argument('--baseline', type=str, default=None,
                        help='Path to end-of-prior-season ELO CSV (default: auto-detect)')
    parser.add_argument('--blend-weight', type=float, default=0.5,
                        help='Weight for projected WAR in blend (0.0=all historical, 1.0=all projected, default: 0.5)')
    parser.add_argument('--skip-projection', action='store_true',
                        help='Skip Marcel projection, use historical WAR only')
    parser.add_argument('--overrides', type=str, default=None,
                        help='Path to war_overrides.csv for prospects/international signings (default: auto-detect)')
    args = parser.parse_args()

    prior_season = args.season - 1

    # Step 1: Fetch offseason transactions
    moves = fetch_offseason_transactions(prior_season)

    # Step 2: Build WAR lookups
    war_lookup = build_war_lookup(prior_season, years=args.years)

    war_projected = None
    if not args.skip_projection:
        war_projected = build_projected_war_lookup(prior_season, years=min(args.years, 3))

    # Step 2b: Load WAR overrides for prospects/international signings
    overrides_path = args.overrides or f'./war_overrides_{args.season}.csv'
    if os.path.exists(overrides_path):
        print(f"\nLoading WAR overrides from {overrides_path}...")
        war_overrides = load_war_overrides(overrides_path)
        print(f"  {len(war_overrides)} overrides loaded")

        # Apply overrides as fallbacks (only fill in players missing from lookups,
        # or override players with 0.0 WAR in both)
        for pid, war_val in war_overrides.items():
            hist_val = war_lookup.get(pid, 0.0)
            proj_val = war_projected.get(pid, 0.0) if war_projected else 0.0
            if hist_val == 0.0:
                war_lookup[pid] = war_val
            if war_projected is not None and proj_val == 0.0:
                war_projected[pid] = war_val
    else:
        print(f"\nNo overrides file found at {overrides_path} — skipping.")

    # Step 3: Compute net WAR changes
    team_delta, annotated_moves = compute_net_war_changes(
        moves, war_lookup, war_projected=war_projected, blend_weight=args.blend_weight
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"NET WAR CHANGES — {args.season} OFFSEASON")
    print(f"{'='*60}")
    sorted_delta = sorted(team_delta.items(), key=lambda x: x[1], reverse=True)
    for team, delta in sorted_delta:
        elo_adj = delta * args.war_to_elo
        direction = '+' if delta >= 0 else ''
        print(f"  {team:4s}  WAR: {direction}{delta:5.1f}   ELO: {direction}{elo_adj:6.1f}")

    # Save annotated transactions
    output_dir = '.'
    txn_df = pd.DataFrame(annotated_moves)
    txn_path = f'{output_dir}/offseason_transactions_{args.season}.csv'
    txn_df.to_csv(txn_path, index=False)
    print(f"\nSaved {len(txn_df)} transactions to {txn_path}")

    # Step 4: Apply ELO adjustment if baseline exists
    if args.baseline:
        baseline_path = args.baseline
    else:
        baseline_path = f'../layers/mlb-pipeline-common/python/mlb_common/elo_rating_end_of_{prior_season}.csv'
        if not os.path.exists(baseline_path):
            # Try downloading from S3 reference path
            baseline_path = None

    if baseline_path and os.path.exists(baseline_path):
        result_df = apply_elo_adjustment(baseline_path, team_delta, args.war_to_elo)
        result_path = f'{output_dir}/preseason_elo_{args.season}.csv'
        result_df.to_csv(result_path, index=False)
        print(f"\n{'='*60}")
        print(f"PRESEASON ELO RATINGS — {args.season}")
        print(f"{'='*60}")
        for _, row in result_df.iterrows():
            adj_str = f"{row['elo_adjustment']:+.1f}" if row['elo_adjustment'] != 0 else "  0.0"
            print(f"  {row['team']:4s}  {row['elo_end_of_season']:7.2f}  {adj_str:>7s}  -> {row['preseason_elo']:7.2f}")
        print(f"\nSaved to {result_path}")
    else:
        print(f"\nNo baseline ELO file found — skipping ELO adjustment.")
        print(f"Run with --baseline <path> to apply adjustments.")

    # Show biggest individual moves
    print(f"\n{'='*60}")
    print(f"TOP 10 WAR GAINS")
    print(f"{'='*60}")
    gains = [m for m in annotated_moves if m['to_team'] and m['war'] > 0]
    gains.sort(key=lambda x: x['war'], reverse=True)
    for m in gains[:10]:
        print(f"  {m['to_team']:4s} +{m['war']:4.1f}  {m['player_name']:25s}  ({m['type']})")

    print(f"\n{'='*60}")
    print(f"TOP 10 WAR LOSSES")
    print(f"{'='*60}")
    losses = [m for m in annotated_moves if m['from_team'] and m['war'] > 0]
    losses.sort(key=lambda x: x['war'], reverse=True)
    for m in losses[:10]:
        print(f"  {m['from_team']:4s} -{m['war']:4.1f}  {m['player_name']:25s}  ({m['type']})")


if __name__ == '__main__':
    main()
