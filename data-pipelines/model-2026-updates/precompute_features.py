"""
Pre-compute features for the enhanced model: rolling FIP + bullpen FIP.

This script fetches game logs from the MLB Stats API and computes:
  1. Rolling FIP (last N starts) for every starter on every game date
  2. Team bullpen FIP for each season

Output:
  - rolling_fip_{season}.csv: pitcher_id, date, rolling_fip, starts_in_window
  - bullpen_fip_{season}.csv: team, bullpen_fip, bullpen_ip, num_relievers

Usage:
  python precompute_features.py 2025          # Single season
  python precompute_features.py 2023 2024 2025  # Multiple seasons
"""
import csv
import math
import os
import sys
import time
import requests

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

ROLLING_WINDOW = 7  # Number of recent starts for rolling FIP


def parse_ip(ip_str):
    """Parse innings pitched string (e.g., '6.1' means 6 and 1/3 innings)."""
    if not ip_str:
        return 0.0
    parts = str(ip_str).split('.')
    whole = int(parts[0])
    if len(parts) > 1:
        thirds = int(parts[1])
        return whole + thirds / 3.0
    return float(whole)


def get_starter_ids_from_schedule(schedule_path):
    """Extract unique starting pitcher IDs and names from a schedule CSV."""
    starters = {}
    with open(schedule_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] != 'Final':
                continue
            for prefix in ['home', 'away']:
                pid_str = row.get(f'{prefix}StartingPitcherId', '').strip()
                name = row.get(f'{prefix}StartingPitcherName', '').strip()
                if pid_str:
                    pid = int(float(pid_str))
                    if pid not in starters:
                        starters[pid] = name
    return starters


def get_pitcher_ids_from_fip(fip_path):
    """Get all pitcher IDs from a FIP CSV (for seasons without schedule pitcher IDs)."""
    pitchers = {}
    with open(fip_path) as f:
        for row in csv.DictReader(f):
            pid = int(float(row['pitcher_id']))
            name = row.get('name', '').strip()
            gs = int(row.get('games_started', 0))
            if gs >= 3:  # Only fetch game logs for pitchers with 3+ starts
                pitchers[pid] = name
    return pitchers


def fetch_game_log(pitcher_id, season):
    """Fetch game-by-game pitching stats for a pitcher in a season."""
    url = f'https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats'
    params = {'stats': 'gameLog', 'group': 'pitching', 'season': season}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get('stats') or not data['stats'][0].get('splits'):
            return []

        games = []
        for entry in data['stats'][0]['splits']:
            s = entry['stat']
            if s.get('gamesStarted', 0) == 0:
                continue  # Skip relief appearances
            ip = parse_ip(s.get('inningsPitched', '0'))
            if ip <= 0:
                continue
            games.append({
                'date': entry.get('date', ''),
                'ip': ip,
                'k': s.get('strikeOuts', 0),
                'bb': s.get('baseOnBalls', 0),
                'hbp': s.get('hitByPitch', 0),
                'hr': s.get('homeRuns', 0),
            })
        games.sort(key=lambda g: g['date'])
        return games
    except Exception:
        return []


def compute_rolling_fip(games, cfip, window=ROLLING_WINDOW):
    """Compute rolling FIP for each start date from prior N starts.

    For game on date D, rolling FIP uses the last `window` starts BEFORE date D.
    This avoids lookahead bias — we only know what happened before the prediction.
    """
    rolling = []
    for i, game in enumerate(games):
        # Use starts before this one (no lookahead)
        prior = games[max(0, i - window):i]
        if not prior:
            rolling.append({
                'date': game['date'],
                'rolling_fip': None,
                'starts_in_window': 0,
            })
            continue

        total_ip = sum(g['ip'] for g in prior)
        if total_ip <= 0:
            rolling.append({
                'date': game['date'],
                'rolling_fip': None,
                'starts_in_window': len(prior),
            })
            continue

        total_hr = sum(g['hr'] for g in prior)
        total_bb = sum(g['bb'] for g in prior)
        total_hbp = sum(g['hbp'] for g in prior)
        total_k = sum(g['k'] for g in prior)

        raw_fip = (13 * total_hr + 3 * (total_bb + total_hbp) - 2 * total_k) / total_ip
        fip = raw_fip + cfip

        rolling.append({
            'date': game['date'],
            'rolling_fip': round(fip, 2),
            'starts_in_window': len(prior),
        })
    return rolling


def compute_bullpen_fip(fip_path, cfip):
    """Compute team-level bullpen FIP from individual pitcher FIP data.

    Relievers: pitchers where games_started < 5 (or GS/GP < 0.5).
    Weighted by IP.
    """
    team_relievers = {}
    with open(fip_path) as f:
        for row in csv.DictReader(f):
            gs = int(row.get('games_started', 0))
            ip = float(row['ip'])
            if gs >= 5 or ip < 5:
                continue  # Skip starters and pitchers with minimal IP
            team = row['team']
            if team not in team_relievers:
                team_relievers[team] = []
            team_relievers[team].append({
                'name': row['name'],
                'ip': ip,
                'k': int(row['k']),
                'bb': int(row['bb']),
                'hbp': int(row['hbp']),
                'hr': int(row['hr']),
            })

    results = []
    for team in sorted(team_relievers.keys()):
        relievers = team_relievers[team]
        total_ip = sum(r['ip'] for r in relievers)
        if total_ip <= 0:
            continue
        total_hr = sum(r['hr'] for r in relievers)
        total_bb = sum(r['bb'] for r in relievers)
        total_hbp = sum(r['hbp'] for r in relievers)
        total_k = sum(r['k'] for r in relievers)
        raw_fip = (13 * total_hr + 3 * (total_bb + total_hbp) - 2 * total_k) / total_ip
        bp_fip = raw_fip + cfip
        results.append({
            'team': team,
            'bullpen_fip': round(bp_fip, 2),
            'bullpen_ip': round(total_ip, 1),
            'num_relievers': len(relievers),
        })
    return results


def process_season(season):
    """Pre-compute all features for a single season."""
    print(f'\n=== PRE-COMPUTING FEATURES: {season} ===\n')

    fip_path = os.path.join(DATA_DIR, f'pitcher_fip_{season}.csv')
    schedule_path = os.path.join(DATA_DIR, f'schedule_{season}_full.csv')

    if not os.path.exists(fip_path):
        print(f'FIP data not found: {fip_path}')
        return

    # Get FIP constant from the FIP file (recalculate from all pitchers)
    all_ip, all_hr, all_bb, all_hbp, all_k, all_er_ip = 0, 0, 0, 0, 0, 0
    with open(fip_path) as f:
        for row in csv.DictReader(f):
            ip = float(row['ip'])
            all_ip += ip
            all_hr += int(row['hr'])
            all_bb += int(row['bb'])
            all_hbp += int(row['hbp'])
            all_k += int(row['k'])
            all_er_ip += float(row['era']) * ip / 9.0
    lg_era = all_er_ip * 9.0 / all_ip if all_ip > 0 else 4.0
    cfip = lg_era - (13 * all_hr + 3 * (all_bb + all_hbp) - 2 * all_k) / all_ip
    print(f'FIP constant: {cfip:.3f}')

    # Step 1: Get pitcher IDs
    # Try schedule first (has pitcher IDs for 2025), fall back to FIP file
    if os.path.exists(schedule_path):
        starters = get_starter_ids_from_schedule(schedule_path)
        if not starters:
            starters = get_pitcher_ids_from_fip(fip_path)
    else:
        starters = get_pitcher_ids_from_fip(fip_path)

    # Filter to starters only (need game logs for rolling FIP)
    starter_ids = set()
    with open(fip_path) as f:
        for row in csv.DictReader(f):
            pid = int(float(row['pitcher_id']))
            gs = int(row.get('games_started', 0))
            if gs >= 3:
                starter_ids.add(pid)

    print(f'Step 1: {len(starter_ids)} starters with 3+ GS')

    # Step 2: Fetch game logs
    print(f'Step 2: Fetching game logs...')
    all_rolling = []
    fetched = 0
    errors = 0
    for i, pid in enumerate(sorted(starter_ids)):
        games = fetch_game_log(pid, season)
        if games:
            rolling = compute_rolling_fip(games, cfip, ROLLING_WINDOW)
            for r in rolling:
                r['pitcher_id'] = pid
            all_rolling.extend(rolling)
            fetched += 1
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            print(f'  {i+1}/{len(starter_ids)} ({fetched} with logs, {errors} errors)')
            time.sleep(0.3)

    print(f'  Done: {fetched} pitchers, {len(all_rolling)} game entries')

    # Write rolling FIP CSV
    rolling_path = os.path.join(DATA_DIR, f'rolling_fip_{season}.csv')
    with open(rolling_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'pitcher_id', 'date', 'rolling_fip', 'starts_in_window',
        ])
        writer.writeheader()
        for r in all_rolling:
            if r['rolling_fip'] is not None:
                writer.writerow(r)
    print(f'Wrote {rolling_path}')

    # Step 3: Compute bullpen FIP
    print(f'\nStep 3: Computing bullpen FIP...')
    bp_results = compute_bullpen_fip(fip_path, cfip)

    bp_path = os.path.join(DATA_DIR, f'bullpen_fip_{season}.csv')
    with open(bp_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'team', 'bullpen_fip', 'bullpen_ip', 'num_relievers',
        ])
        writer.writeheader()
        writer.writerows(bp_results)
    print(f'Wrote {bp_path}')

    # Display bullpen FIP
    bp_results.sort(key=lambda x: x['bullpen_fip'])
    print(f'\n{"Team":<25} {"BP FIP":>7} {"IP":>7} {"#RP":>4}')
    print('-' * 46)
    for r in bp_results[:5]:
        print(f'{r["team"]:<25} {r["bullpen_fip"]:>7.2f} {r["bullpen_ip"]:>7.1f} {r["num_relievers"]:>4}')
    print('...')
    for r in bp_results[-5:]:
        print(f'{r["team"]:<25} {r["bullpen_fip"]:>7.2f} {r["bullpen_ip"]:>7.1f} {r["num_relievers"]:>4}')


def main():
    seasons = [int(s) for s in sys.argv[1:]] if len(sys.argv) > 1 else [2025]
    for season in seasons:
        process_season(season)


if __name__ == '__main__':
    main()
