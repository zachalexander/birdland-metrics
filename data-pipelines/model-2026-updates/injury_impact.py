"""
Injury/IL impact assessment for MLB teams.

Pulls IL rosters from MLB Stats API, maps to FanGraphs WAR via pybaseball,
and quantifies per-team injury impact for ELO/win probability adjustments.

For players without current-year WAR (injured early), falls back to prior-year WAR.
Starting pitchers on IL are flagged separately since they affect FIP matchup calculations.

Usage:
  python injury_impact.py                  # Current date, all 30 teams
  python injury_impact.py 2025-07-15       # Specific date snapshot
  python injury_impact.py 2025-07-15 BAL   # Specific date + team
"""
import csv
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime

import statsapi

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_all_teams(season):
    """Get all 30 MLB team IDs and abbreviations."""
    teams = statsapi.get('teams', {'sportId': 1, 'season': season})
    return [(t['id'], t['abbreviation'], t['name']) for t in teams['teams']]


def get_il_players(team_id, query_date):
    """Get all players on the injured list for a team on a given date."""
    roster = statsapi.get('team_roster', {
        'teamId': team_id,
        'date': query_date.strftime('%m/%d/%Y'),
        'rosterType': '40Man',
    })
    il_players = []
    for p in roster['roster']:
        if 'Injured' in p['status'].get('description', ''):
            il_players.append({
                'mlb_id': p['person']['id'],
                'name': p['person']['fullName'],
                'position': p['position']['abbreviation'],
                'il_type': p['status']['description'],
                'is_pitcher': p['position']['abbreviation'] == 'P',
            })
    return il_players


def load_war_data(season):
    """Load batting and pitching WAR from FanGraphs via pybaseball."""
    from pybaseball import batting_stats, pitching_stats

    print(f'  Loading {season} batting WAR from FanGraphs...')
    bat = batting_stats(season, qual=0)
    bat_war = dict(zip(bat['IDfg'], bat['WAR']))

    print(f'  Loading {season} pitching WAR from FanGraphs...')
    pit = pitching_stats(season, qual=0)
    pit_war = dict(zip(pit['IDfg'], pit['WAR']))

    print(f'  {len(bat_war)} batters, {len(pit_war)} pitchers loaded')
    return bat_war, pit_war


def build_id_crossref(mlb_ids):
    """Map MLB API player IDs to FanGraphs IDs."""
    from pybaseball import playerid_reverse_lookup

    if not mlb_ids:
        return {}
    print(f'  Cross-referencing {len(mlb_ids)} player IDs...')
    xref = playerid_reverse_lookup(list(mlb_ids), key_type='mlbam')
    mapping = {}
    for _, row in xref.iterrows():
        fg_id = row['key_fangraphs']
        if fg_id and fg_id != -1:
            mapping[row['key_mlbam']] = int(fg_id)
    print(f'  Mapped {len(mapping)}/{len(mlb_ids)} players')
    return mapping


def lookup_war(fg_id, bat_war, pit_war, bat_war_prev, pit_war_prev):
    """Look up WAR for a player, falling back to prior year if needed.

    Since FanGraphs includes pitchers in batting stats with 0.0 WAR,
    we check both batting and pitching and take the higher value.
    """
    if fg_id is None:
        return None, None

    # Try current year — take max of batting and pitching WAR
    bat_w = bat_war.get(fg_id)
    pit_w = pit_war.get(fg_id)
    if bat_w is not None or pit_w is not None:
        war = max(bat_w or 0.0, pit_w or 0.0)
        # If both are 0 or negative, use whichever is not None (preserve negatives)
        if war == 0.0 and bat_w is not None and pit_w is not None:
            war = max(bat_w, pit_w)
        elif war == 0.0:
            war = bat_w if bat_w is not None else pit_w
        return war, 'current'

    # Fall back to prior year
    bat_w = bat_war_prev.get(fg_id)
    pit_w = pit_war_prev.get(fg_id)
    if bat_w is not None or pit_w is not None:
        war = max(bat_w or 0.0, pit_w or 0.0)
        if war == 0.0 and bat_w is not None and pit_w is not None:
            war = max(bat_w, pit_w)
        elif war == 0.0:
            war = bat_w if bat_w is not None else pit_w
        return war, 'prior_year'

    return None, None


def main():
    # Parse args
    if len(sys.argv) > 1:
        query_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    else:
        query_date = date.today()

    team_filter = sys.argv[2].upper() if len(sys.argv) > 2 else None
    season = query_date.year

    print(f'=== INJURY IMPACT ASSESSMENT — {query_date} ===\n')

    # Step 1: Get teams
    all_teams = get_all_teams(season)
    if team_filter:
        all_teams = [(tid, abbr, name) for tid, abbr, name in all_teams if abbr == team_filter]
        if not all_teams:
            print(f'Team {team_filter} not found')
            return
    print(f'Step 1: {len(all_teams)} teams\n')

    # Step 2: Pull IL rosters
    print(f'Step 2: Pulling IL rosters...')
    team_il = {}
    all_mlb_ids = set()
    for tid, abbr, name in sorted(all_teams, key=lambda x: x[1]):
        il = get_il_players(tid, query_date)
        team_il[abbr] = il
        for p in il:
            all_mlb_ids.add(p['mlb_id'])
        if il:
            print(f'  {abbr}: {len(il)} IL players')
        time.sleep(0.1)

    total_il = sum(len(v) for v in team_il.values())
    print(f'  Total: {total_il} players on IL across {len(team_il)} teams\n')

    # Step 3: Load WAR data (current + prior year for fallback)
    print(f'Step 3: Loading WAR data...')
    bat_war, pit_war = load_war_data(season)
    bat_war_prev, pit_war_prev = load_war_data(season - 1)
    print()

    # Step 4: Cross-reference IDs
    print(f'Step 4: Cross-referencing player IDs...')
    id_map = build_id_crossref(all_mlb_ids)
    print()

    # Step 5: Calculate per-team injury impact
    print(f'Step 5: Calculating injury impact...')
    team_results = []
    all_player_rows = []

    for abbr in sorted(team_il.keys()):
        il_players = team_il[abbr]
        total_war_lost = 0.0
        pitcher_war_lost = 0.0
        sp_count = 0
        mapped = 0

        for p in il_players:
            fg_id = id_map.get(p['mlb_id'])
            war, source = lookup_war(fg_id, bat_war, pit_war, bat_war_prev, pit_war_prev)

            if war is not None:
                mapped += 1
                # Only count positive WAR as "lost" — negative WAR players aren't hurting you
                war_impact = max(war, 0.0)
                total_war_lost += war_impact
                if p['is_pitcher']:
                    pitcher_war_lost += war_impact
            else:
                war_impact = 0.0
                source = 'unknown'

            all_player_rows.append({
                'team': abbr,
                'name': p['name'],
                'position': p['position'],
                'il_type': p['il_type'],
                'mlb_id': p['mlb_id'],
                'fg_id': fg_id or '',
                'war': war if war is not None else '',
                'war_source': source or '',
                'war_impact': round(war_impact, 1),
                'is_pitcher': p['is_pitcher'],
            })

        team_results.append({
            'team': abbr,
            'il_count': len(il_players),
            'il_pitchers': sum(1 for p in il_players if p['is_pitcher']),
            'il_position': sum(1 for p in il_players if not p['is_pitcher']),
            'total_war_lost': round(total_war_lost, 1),
            'pitcher_war_lost': round(pitcher_war_lost, 1),
            'position_war_lost': round(total_war_lost - pitcher_war_lost, 1),
            'players_mapped': mapped,
        })

    team_results.sort(key=lambda x: x['total_war_lost'], reverse=True)

    # Step 6: Display results
    print(f'\n=== TEAM INJURY IMPACT (sorted by WAR lost) ===')
    print(f'{"Team":<5} {"IL#":>4} {"P":>3} {"Pos":>4} {"WAR Lost":>9} {"P WAR":>7} {"Pos WAR":>8}')
    print('-' * 45)
    for r in team_results:
        if r['il_count'] > 0:
            print(f'{r["team"]:<5} {r["il_count"]:>4} {r["il_pitchers"]:>3} '
                  f'{r["il_position"]:>4} {r["total_war_lost"]:>9.1f} '
                  f'{r["pitcher_war_lost"]:>7.1f} {r["position_war_lost"]:>8.1f}')

    # Step 7: Write CSVs
    team_path = os.path.join(OUTPUT_DIR, f'injury_impact_teams_{query_date}.csv')
    with open(team_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'team', 'il_count', 'il_pitchers', 'il_position',
            'total_war_lost', 'pitcher_war_lost', 'position_war_lost', 'players_mapped',
        ])
        writer.writeheader()
        writer.writerows(team_results)

    player_path = os.path.join(OUTPUT_DIR, f'injury_impact_players_{query_date}.csv')
    with open(player_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'team', 'name', 'position', 'il_type', 'mlb_id', 'fg_id',
            'war', 'war_source', 'war_impact', 'is_pitcher',
        ])
        writer.writeheader()
        writer.writerows(all_player_rows)

    print(f'\nWrote {team_path}')
    print(f'Wrote {player_path}')

    # Summary
    total_war = sum(r['total_war_lost'] for r in team_results)
    print(f'\nLeague-wide: {total_il} players on IL, {total_war:.1f} total WAR lost')
    if team_results:
        worst = team_results[0]
        print(f'Most impacted: {worst["team"]} ({worst["total_war_lost"]:.1f} WAR lost, '
              f'{worst["il_count"]} players)')


if __name__ == '__main__':
    main()
