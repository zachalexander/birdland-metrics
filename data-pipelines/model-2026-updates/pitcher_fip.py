"""
Calculate FIP for all MLB pitchers from the MLB Stats API.

FIP = ((13 * HR) + (3 * (BB + HBP)) - (2 * K)) / IP + cFIP
where cFIP = lgERA - ((13*lgHR + 3*(lgBB+lgHBP) - 2*lgK) / lgIP)

Two modes:
  - Schedule mode (current season): Extract starter IDs from schedule CSV
  - Roster mode (any season): Pull all pitchers from all 30 team rosters

Usage:
  python pitcher_fip.py 2025              # Current season (uses schedule CSV if available)
  python pitcher_fip.py 2024 --roster     # Historical season (uses team rosters)
"""
import csv
import json
import os
import sys
import time
import statsapi

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_ip(ip_str):
    """Parse innings pitched string (e.g., '64.1' means 64 and 1/3 innings)."""
    if not ip_str:
        return 0.0
    parts = str(ip_str).split('.')
    whole = int(parts[0])
    if len(parts) > 1:
        thirds = int(parts[1])
        return whole + thirds / 3.0
    return float(whole)


def get_starter_ids_from_schedule(schedule_path):
    """Extract unique starting pitcher IDs from a schedule CSV."""
    starters = {}
    with open(schedule_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] != 'Final':
                continue
            for prefix in ['home', 'away']:
                pid_str = row.get(f'{prefix}StartingPitcherId', '').strip()
                name = row.get(f'{prefix}StartingPitcherName', '').strip()
                if pid_str and pid_str != '':
                    pid = int(float(pid_str))
                    if pid not in starters:
                        starters[pid] = name
    return starters


def get_all_pitchers_from_rosters(season):
    """Get all pitcher IDs from all 30 team rosters for a given season."""
    teams = statsapi.get('teams', {'sportId': 1, 'season': season})
    team_ids = [(t['id'], t['abbreviation']) for t in teams['teams']]

    all_pitchers = {}
    for tid, abbr in sorted(team_ids):
        roster = statsapi.get('team_roster', {
            'teamId': tid, 'season': season, 'rosterType': 'fullSeason',
        })
        for p in roster['roster']:
            if p['position']['abbreviation'] == 'P':
                pid = p['person']['id']
                if pid not in all_pitchers:
                    all_pitchers[pid] = p['person']['fullName']
        time.sleep(0.1)
    return all_pitchers


def fetch_pitcher_stats(pitcher_id, season, use_year_by_year=False):
    """Fetch season pitching stats for a single pitcher."""
    try:
        stat_type = 'yearByYear' if use_year_by_year else 'season'
        data = statsapi.player_stat_data(
            pitcher_id, group='pitching', type=stat_type, sportId=1
        )
        for stat_entry in data.get('stats', []):
            if stat_entry.get('season') == str(season):
                s = stat_entry['stats']
                ip = parse_ip(s.get('inningsPitched', '0'))
                if ip > 0:
                    return {
                        'name': f"{data.get('first_name', '')} {data.get('last_name', '')}",
                        'team': data.get('current_team', ''),
                        'ip': ip,
                        'hr': s.get('homeRuns', 0),
                        'bb': s.get('baseOnBalls', 0),
                        'hbp': s.get('hitByPitch', s.get('hitBatsmen', 0)),
                        'k': s.get('strikeOuts', 0),
                        'era': float(s.get('era', '0')),
                        'games_started': s.get('gamesStarted', 0),
                        'games_played': s.get('gamesPlayed', 0),
                    }
    except Exception:
        pass
    return None


def calculate_fip_constant(all_stats):
    """Calculate the league-wide FIP constant.
    cFIP = lgERA - ((13*lgHR + 3*(lgBB+lgHBP) - 2*lgK) / lgIP)
    """
    total_ip = sum(s['ip'] for s in all_stats)
    if total_ip == 0:
        return 3.10  # Fallback
    total_hr = sum(s['hr'] for s in all_stats)
    total_bb = sum(s['bb'] for s in all_stats)
    total_hbp = sum(s['hbp'] for s in all_stats)
    total_k = sum(s['k'] for s in all_stats)
    total_er = sum(s['era'] * s['ip'] / 9.0 for s in all_stats)

    lg_era = total_er * 9.0 / total_ip
    raw_fip = (13 * total_hr + 3 * (total_bb + total_hbp) - 2 * total_k) / total_ip
    cfip = lg_era - raw_fip

    print(f'  League totals: IP={total_ip:.1f}, K={total_k}, BB={total_bb}, '
          f'HBP={total_hbp}, HR={total_hr}')
    print(f'  League ERA: {lg_era:.3f}, FIP constant: {cfip:.3f}')
    return cfip


def calculate_fip(stats, cfip):
    """Calculate FIP for a single pitcher."""
    if stats['ip'] <= 0:
        return None
    return (13 * stats['hr'] + 3 * (stats['bb'] + stats['hbp']) - 2 * stats['k']) / stats['ip'] + cfip


def main():
    from datetime import datetime
    current_year = datetime.now().year

    season = int(sys.argv[1]) if len(sys.argv) > 1 else current_year
    use_roster = '--roster' in sys.argv or season < current_year

    # For historical seasons, yearByYear is needed since 'season' type only returns current year
    use_year_by_year = season < current_year

    print(f'=== FIP CALCULATION — {season} SEASON ===')
    print(f'Mode: {"roster" if use_roster else "schedule"}, '
          f'API type: {"yearByYear" if use_year_by_year else "season"}\n')

    # Step 1: Get pitcher IDs
    schedule_path = os.path.join(OUTPUT_DIR, f'schedule_{season}_full.csv')
    if not use_roster and os.path.exists(schedule_path):
        pitchers = get_starter_ids_from_schedule(schedule_path)
        print(f'Step 1: {len(pitchers)} unique starters from schedule CSV')
    else:
        pitchers = get_all_pitchers_from_rosters(season)
        print(f'Step 1: {len(pitchers)} unique pitchers from 30 team rosters')
    print()

    # Step 2: Fetch stats
    print(f'Step 2: Fetching pitcher stats...')
    all_stats = {}
    errors = 0
    for i, (pid, name) in enumerate(sorted(pitchers.items())):
        stats = fetch_pitcher_stats(pid, season, use_year_by_year)
        if stats:
            stats['pitcher_id'] = pid
            all_stats[pid] = stats
        else:
            errors += 1
        if (i + 1) % 100 == 0:
            print(f'  ... {i+1}/{len(pitchers)} ({len(all_stats)} with stats, {errors} errors)')
            time.sleep(0.5)

    print(f'  Done: {len(all_stats)} pitchers with stats, {errors} errors\n')

    # Step 3: Calculate FIP constant from ALL pitchers (matches FanGraphs methodology)
    print(f'Step 3: FIP constant (all {len(all_stats)} pitchers)...')
    cfip = calculate_fip_constant(list(all_stats.values()))
    print()

    # Step 4: Calculate individual FIP
    fip_table = []
    for pid, stats in all_stats.items():
        fip = calculate_fip(stats, cfip)
        if fip is not None:
            fip_table.append({
                'pitcher_id': pid,
                'name': stats['name'],
                'team': stats['team'],
                'ip': round(stats['ip'], 1),
                'era': stats['era'],
                'fip': round(fip, 2),
                'k': stats['k'],
                'bb': stats['bb'],
                'hbp': stats['hbp'],
                'hr': stats['hr'],
                'games_started': stats['games_started'],
            })

    fip_table.sort(key=lambda x: x['fip'])

    # Step 5: Display top/bottom
    min_ip, min_gs = 80, 10
    sp_only = [r for r in fip_table if r['ip'] >= min_ip and r['games_started'] >= min_gs]

    print(f'=== TOP 15 SP BY FIP (min {min_ip} IP, {min_gs}+ GS) ===')
    print(f'{"#":<4} {"Name":<25} {"Team":<25} {"IP":>6} {"ERA":>6} {"FIP":>6}')
    print('-' * 78)
    for i, r in enumerate(sp_only[:15], 1):
        print(f'{i:<4} {r["name"]:<25} {r["team"]:<25} {r["ip"]:>6.1f} {r["era"]:>6.2f} {r["fip"]:>6.2f}')

    print(f'\n=== BOTTOM 5 SP BY FIP ===')
    for i, r in enumerate(reversed(sp_only[-5:]), 1):
        print(f'{i:<4} {r["name"]:<25} {r["team"]:<25} {r["ip"]:>6.1f} {r["era"]:>6.2f} {r["fip"]:>6.2f}')

    # Step 6: Write CSV
    output_path = os.path.join(OUTPUT_DIR, f'pitcher_fip_{season}.csv')
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'pitcher_id', 'name', 'team', 'ip', 'era', 'fip',
            'k', 'bb', 'hbp', 'hr', 'games_started',
        ])
        writer.writeheader()
        writer.writerows(fip_table)

    print(f'\nWrote {len(fip_table)} pitchers to {output_path}')

    if sp_only:
        fips = [r['fip'] for r in sp_only]
        print(f'Qualified SP FIP range: {min(fips):.2f} to {max(fips):.2f}, '
              f'mean: {sum(fips)/len(fips):.2f}')


if __name__ == '__main__':
    main()
