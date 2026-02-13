"""
Recompute ELO ratings from scratch using raw retrosheet game logs (1871-2025).

V2: Adds franchise continuity mapping so relocated/renamed teams carry forward
their ELO ratings. Only outputs the 30 current MLB teams.

Uses the canonical formula:
  K = 20, HFA = 55
  MOV = log(|score_diff| + 1) * (2.2 / (0.001 * |elo_diff| + 2.2))
  Win probability = 1 / (1 + 10^((elo_b - (elo_a + HFA)) / 400))
"""
import csv
import math
import os
from collections import defaultdict
from datetime import datetime

# Config
DATA_DIR = os.path.dirname(os.path.abspath(__file__)) + '/retrosheet_data'
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Canonical ELO parameters
ELO_K = 20
ELO_HFA = 55
ELO_INIT = 1500
MOV_MULTIPLIER = 2.2

# Retrosheet game log columns
COL_DATE = 0
COL_GAME_NUM = 1
COL_VISITOR = 3
COL_HOME = 6
COL_VISITOR_SCORE = 9
COL_HOME_SCORE = 10

# Franchise continuity mapping: retrosheet code → current team code
# Teams that relocated or renamed carry their ELO forward
FRANCHISE_MAP = {
    # American League
    'NYA': 'NYY',   # New York Yankees (always NYA in retrosheet)
    'CHA': 'CWS',   # Chicago White Sox (always CHA in retrosheet)
    'KCA': 'KC',     # Kansas City Royals
    'TBA': 'TB',     # Tampa Bay Rays (Devil Rays → Rays)
    'ANA': 'LAA',    # Los Angeles Angels (California Angels → Anaheim → LA Angels)
    'CAL': 'LAA',    # California Angels
    'SE1': 'MIL',    # Seattle Pilots → Milwaukee Brewers
    'ML3': 'MIL',    # Milwaukee Brewers (after 1998 move to NL)
    'WS1': 'MIN',    # Washington Senators I → Minnesota Twins
    'WS2': 'TEX',    # Washington Senators II → Texas Rangers
    'PHA': 'ATH',    # Philadelphia A's → Kansas City A's → Oakland A's → Athletics
    'KC2': 'ATH',    # Kansas City A's → Oakland A's → Athletics
    'OAK': 'ATH',    # Oakland A's → Athletics (Sacramento, 2025+)
    'SLA': 'BAL',    # St. Louis Browns → Baltimore Orioles
    'ML2': 'BAL',    # Milwaukee Brewers (1901) → St. Louis Browns → Baltimore Orioles

    # National League
    'NYN': 'NYM',    # New York Mets
    'CHN': 'CHC',    # Chicago Cubs
    'SFN': 'SF',     # San Francisco Giants
    'NY1': 'SF',     # New York Giants → San Francisco Giants
    'LAN': 'LAD',    # Los Angeles Dodgers
    'BRO': 'LAD',    # Brooklyn Dodgers → Los Angeles Dodgers
    'SDN': 'SD',     # San Diego Padres
    'SLN': 'STL',    # St. Louis Cardinals
    'BSN': 'ATL',    # Boston Braves → Milwaukee Braves → Atlanta Braves
    'MLN': 'ATL',    # Milwaukee Braves → Atlanta Braves
    'FLO': 'MIA',    # Florida Marlins → Miami Marlins
    'MON': 'WSH',    # Montreal Expos → Washington Nationals
    'WAS': 'WSH',    # Washington Nationals (retrosheet uses WAS for some years)
    'WSN': 'WSH',    # Washington Nationals

    # Teams that kept their retrosheet codes (mapped to Stats API format)
    'ARI': 'AZ',
    'SDP': 'SD',     # alternate code
    'SFG': 'SF',     # alternate code
    'KCR': 'KC',     # alternate code
    'TBR': 'TB',     # alternate code
    'CHW': 'CWS',    # alternate code
}

# Current 30 MLB teams (canonical codes matching our pipeline)
CURRENT_TEAMS = {
    'ATH', 'ATL', 'AZ', 'BAL', 'BOS', 'CHC', 'CIN', 'CLE', 'COL', 'CWS',
    'DET', 'HOU', 'KC', 'LAA', 'LAD', 'MIA', 'MIL', 'MIN', 'NYM', 'NYY',
    'PHI', 'PIT', 'SD', 'SEA', 'SF', 'STL', 'TB', 'TEX', 'TOR', 'WSH',
}


def map_team(retrosheet_code):
    """Map a retrosheet team code to its current franchise code."""
    return FRANCHISE_MAP.get(retrosheet_code, retrosheet_code)


def expected_score(elo_a, elo_b, hfa=0):
    return 1 / (1 + 10 ** ((elo_b - (elo_a + hfa)) / 400))


def margin_of_victory_mult(score_diff, elo_diff):
    return math.log(abs(score_diff) + 1) * (MOV_MULTIPLIER / (0.001 * abs(elo_diff) + MOV_MULTIPLIER))


def parse_retrosheet_file(filepath):
    games = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 11:
                continue
            try:
                date_str = row[COL_DATE].strip('"')
                visitor = row[COL_VISITOR].strip('"')
                home = row[COL_HOME].strip('"')
                visitor_score = int(row[COL_VISITOR_SCORE])
                home_score = int(row[COL_HOME_SCORE])
                game_num = row[COL_GAME_NUM].strip('"')
                date = datetime.strptime(date_str, '%Y%m%d').date()
                games.append({
                    'date': date,
                    'home_raw': home,
                    'away_raw': visitor,
                    'home': map_team(home),
                    'away': map_team(visitor),
                    'home_score': home_score,
                    'away_score': visitor_score,
                    'game_num': game_num,
                })
            except (ValueError, IndexError):
                continue
    return games


def load_all_games():
    all_games = []
    for year in range(1871, 2026):
        for filename in [f'gl{year}.txt', f'GL{year}.TXT']:
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.exists(filepath):
                games = parse_retrosheet_file(filepath)
                all_games.extend(games)
                print(f'  {year}: {len(games)} games')
                break
        else:
            print(f'  {year}: FILE NOT FOUND')
    all_games.sort(key=lambda g: (g['date'], g['game_num']))
    return all_games


def compute_elo(all_games):
    team_elo = defaultdict(lambda: ELO_INIT)
    elo_rows = []
    season_end_ratings = {}
    current_year = None

    for game in all_games:
        year = game['date'].year
        if current_year is not None and year != current_year:
            # Save end-of-season: only current 30 teams
            season_end_ratings[current_year] = {
                t: team_elo[t] for t in team_elo if t in CURRENT_TEAMS
            }
        current_year = year

        home = game['home']
        away = game['away']

        elo_home = team_elo[home]
        elo_away = team_elo[away]

        prob_home = expected_score(elo_home, elo_away, hfa=ELO_HFA)

        if game['home_score'] > game['away_score']:
            result_home = 1.0
        elif game['home_score'] < game['away_score']:
            result_home = 0.0
        else:
            result_home = 0.5

        score_diff = abs(game['home_score'] - game['away_score'])
        mov = 1.0 if score_diff == 0 else margin_of_victory_mult(score_diff, elo_home - elo_away)

        elo_shift = ELO_K * mov * (result_home - prob_home)
        team_elo[home] = elo_home + elo_shift
        team_elo[away] = elo_away - elo_shift

        elo_rows.append({
            'date': game['date'].isoformat(),
            'home_team': home,
            'away_team': away,
            'home_score': game['home_score'],
            'away_score': game['away_score'],
            'home_elo_before': round(elo_home, 4),
            'away_elo_before': round(elo_away, 4),
            'home_elo_after': round(team_elo[home], 4),
            'away_elo_after': round(team_elo[away], 4),
        })

    # Final year
    if current_year is not None:
        season_end_ratings[current_year] = {
            t: team_elo[t] for t in team_elo if t in CURRENT_TEAMS
        }

    return elo_rows, season_end_ratings


def write_season_end(season_end_ratings, year):
    ratings = season_end_ratings.get(year, {})
    path = os.path.join(OUTPUT_DIR, f'elo_rating_end_of_{year}_recomputed.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['team', 'elo'])
        for team in sorted(ratings.keys()):
            writer.writerow([team, round(ratings[team], 2)])
    return path, ratings


def compare(label, recomputed, existing_file):
    if not os.path.exists(existing_file):
        print(f'  {label}: file not found')
        return

    existing = {}
    with open(existing_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row['team']] = float(row['elo'])

    print(f'\n  === {label} ===')
    print(f'  {"Team":<6} {"Existing":>10} {"Recomputed":>12} {"Diff":>10}')
    print(f'  {"-"*44}')

    total_diff = 0
    count = 0
    for team in sorted(CURRENT_TEAMS):
        old = existing.get(team)
        new = recomputed.get(team)
        if old is not None and new is not None:
            diff = new - old
            total_diff += abs(diff)
            count += 1
            flag = '  ***' if abs(diff) > 30 else ''
            print(f'  {team:<6} {old:>10.2f} {new:>12.2f} {diff:>+10.2f}{flag}')
        elif old is not None:
            print(f'  {team:<6} {old:>10.2f} {"—":>12}')
        elif new is not None:
            print(f'  {team:<6} {"—":>10} {new:>12.2f}')

    if count > 0:
        print(f'\n  Matched {count}/30 teams, avg |diff| = {total_diff/count:.2f}')


def main():
    print('=' * 60)
    print('ELO RECOMPUTATION v2 — WITH FRANCHISE MAPPING')
    print(f'K={ELO_K}, HFA={ELO_HFA}, MOV=log, mult={MOV_MULTIPLIER}')
    print('=' * 60)

    print('\nLoading games...')
    all_games = load_all_games()
    print(f'\nTotal: {len(all_games)} games, {all_games[0]["date"]} to {all_games[-1]["date"]}')

    # Check for unmapped teams in recent years
    recent_teams = set()
    for g in all_games:
        if g['date'].year >= 2020:
            recent_teams.add(g['home'])
            recent_teams.add(g['away'])
    unmapped = recent_teams - CURRENT_TEAMS
    if unmapped:
        print(f'\n  WARNING: Unmapped teams in 2020+: {unmapped}')
    else:
        print(f'\n  All recent teams mapped to current 30 franchises.')

    print('\nComputing ELO...')
    elo_rows, season_end_ratings = compute_elo(all_games)

    print('\nEnd-of-season ratings:')
    for year in [2023, 2024, 2025]:
        path, ratings = write_season_end(season_end_ratings, year)
        print(f'  {year}: {len(ratings)} teams → {path}')
        # Print top/bottom 5
        sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        print(f'    Top 5: {", ".join(f"{t} ({e:.0f})" for t, e in sorted_teams[:5])}')
        print(f'    Bot 5: {", ".join(f"{t} ({e:.0f})" for t, e in sorted_teams[-5:])}')

    # Full history
    full_path = os.path.join(OUTPUT_DIR, 'elo-ratings-full-recomputed.csv')
    with open(full_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'date', 'home_team', 'away_team', 'home_score', 'away_score',
            'home_elo_before', 'away_elo_before', 'home_elo_after', 'away_elo_after',
        ])
        writer.writeheader()
        writer.writerows(elo_rows)
    print(f'\nFull history: {len(elo_rows)} games → {full_path}')

    # Comparisons
    scratchpad = OUTPUT_DIR
    print('\n' + '=' * 60)
    print('COMPARISON: Recomputed vs Existing')
    print('=' * 60)

    # We need to map the existing 2024 file's codes to canonical
    # The existing file uses retrosheet codes (OAK, KCR, etc.)
    # Let me create a temp mapped version
    existing_2024 = os.path.join(scratchpad, 'elo_rating_end_of_2024.csv')
    if os.path.exists(existing_2024):
        mapped_2024 = os.path.join(scratchpad, 'elo_rating_end_of_2024_mapped.csv')
        with open(existing_2024) as f_in, open(mapped_2024, 'w', newline='') as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=['team', 'elo'])
            writer.writeheader()
            for row in reader:
                writer.writerow({
                    'team': map_team(row['team']),
                    'elo': row['elo'],
                })
        compare('End of 2024 (old formula HFA=35 → recomputed HFA=55)',
                season_end_ratings[2024], mapped_2024)

    existing_2025 = os.path.join(scratchpad, 'elo_rating_end_of_2025.csv')
    compare('End of 2025 (Lambda HFA=55 seeded from HFA=35 → recomputed clean)',
            season_end_ratings[2025], existing_2025)


if __name__ == '__main__':
    main()
