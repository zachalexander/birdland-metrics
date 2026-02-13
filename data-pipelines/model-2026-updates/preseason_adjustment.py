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


def compute_net_war_changes(moves, war_lookup):
    """
    Compute net WAR gained and lost per team.

    Returns:
        team_war_delta: {team_abbr: net_war_change}
        annotated_moves: list of moves with WAR attached
    """
    team_gains = defaultdict(float)
    team_losses = defaultdict(float)
    annotated = []

    for move in moves:
        pid = move['player_id']
        war = war_lookup.get(pid, 0.0)
        move['war'] = war

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
    args = parser.parse_args()

    prior_season = args.season - 1

    # Step 1: Fetch offseason transactions
    moves = fetch_offseason_transactions(prior_season)

    # Step 2: Build WAR lookup
    war_lookup = build_war_lookup(prior_season, years=args.years)

    # Step 3: Compute net WAR changes
    team_delta, annotated_moves = compute_net_war_changes(moves, war_lookup)

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
        import os
        if not os.path.exists(baseline_path):
            # Try downloading from S3 reference path
            baseline_path = None

    if baseline_path and __import__('os').path.exists(baseline_path):
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
