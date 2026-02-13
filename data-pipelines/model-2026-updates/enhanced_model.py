# -*- coding: utf-8 -*-
"""
Enhanced Win Probability Model v2.

Features:
  1. Base ELO ratings (updated after each game)
  2. Starting pitcher FIP matchup (rolling or season-long)
  3. Bullpen quality (team bullpen FIP)
  4. Park factors (venue-specific run environment)
  5. Travel/fatigue penalty (west-to-east, long distance)
  6. Injury impact (WAR lost on IL)

All adjustments are converted to ELO-equivalent points and applied to the
base rating before computing win probability via the logistic formula.

Usage:
  python enhanced_model.py 2025                    # Full season, all features
  python enhanced_model.py 2025 --base-only        # ELO only (for comparison)
  python enhanced_model.py 2025 --v1               # V1 model (season FIP + travel only)
  python enhanced_model.py 2025 --sweep            # Parameter sweep
"""
import csv
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Full team name → schedule abbreviation mapping (for bullpen FIP data)
TEAM_NAME_TO_ABBR = {
    'Arizona Diamondbacks': 'AZ', 'Athletics': 'ATH', 'Atlanta Braves': 'ATL',
    'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC',
    'Chicago White Sox': 'CWS', 'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL', 'Detroit Tigers': 'DET', 'Houston Astros': 'HOU',
    'Kansas City Royals': 'KC', 'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD',
    'Miami Marlins': 'MIA', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN',
    'New York Mets': 'NYM', 'New York Yankees': 'NYY', 'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
    'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}

# === MODEL PARAMETERS ===
# ELO
ELO_K = 20
ELO_HFA = 55
ELO_INIT = 1500
MOV_MULTIPLIER = 2.2

# FIP adjustment: ELO points per 1 FIP unit below league average
# Optimal: 50 (season FIP). Higher weight + higher shrinkage is the best combo.
FIP_WEIGHT = 50

# Bayesian FIP regression: IP of "prior" pulling toward league average.
# A pitcher with FIP_PRIOR_IP innings of data is 50% regressed toward lg avg.
# At 2x this value, 33% regressed. FIP stabilizes around 50-60 IP per FanGraphs.
FIP_PRIOR_IP = 50

# Travel penalty: ELO points deducted for significant west-to-east travel
# Applied when crossing 2+ timezones eastward AND traveling 1000+ miles
# Sweep showed minimal impact (0 is as good as any), keeping small value
TRAVEL_PENALTY = 10

# Injury adjustment: ELO points per 1 WAR lost on IL
# A team missing 5 WAR ≈ 25 ELO points ≈ 3.5% win prob shift
INJURY_WAR_WEIGHT = 5

# Bullpen FIP adjustment: ELO points per 1 bullpen FIP unit below league average
# Bullpens pitch ~33% of innings, so weight is lower than SP FIP
BULLPEN_FIP_WEIGHT = 15

# Park factor scaling: how much park factor affects the FIP adjustment
# 1.0 = full scaling (FIP adj *= 100/park_factor), 0.0 = no adjustment
PARK_FACTOR_SCALE = 1.0

# Probability shrinkage: pull extreme probabilities toward 50%
# p_adjusted = SHRINK + (1 - 2*SHRINK) * p_raw
# 0.16 is optimal — found via sweep with FIP_WEIGHT=50.
# Higher shrinkage corrects ELO+FIP overconfidence without hurting accuracy.
PROB_SHRINKAGE = 0.16


# === ELO MATH ===

def expected_score(elo_a, elo_b, hfa=0):
    """Probability of team A winning given ELO ratings and HFA."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a - hfa) / 400))


def margin_of_victory_mult(score_diff, elo_diff):
    """Margin-of-victory multiplier (log formula)."""
    return math.log(abs(score_diff) + 1) * (MOV_MULTIPLIER / (0.001 * abs(elo_diff) + MOV_MULTIPLIER))


def update_elo(elo, expected, actual, k=ELO_K, mov_mult=1.0):
    """Update ELO rating after a game."""
    return elo + k * mov_mult * (actual - expected)


# === DATA LOADERS ===

def load_elo_baseline(path):
    """Load end-of-prior-season ELO ratings."""
    elos = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            elos[row['team']] = float(row['elo'])
    return elos


def normalize_name(name):
    """Normalize pitcher name for fuzzy matching (strip accents, suffixes)."""
    import unicodedata
    # Decompose unicode and strip combining marks (accents)
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Strip common suffixes
    for suffix in [' Jr.', ' Jr', ' Sr.', ' Sr', ' II', ' III', ' IV', ' V']:
        ascii_name = ascii_name.replace(suffix, '')
    return ascii_name.strip().lower()


def load_fip_data(path):
    """Load pitcher FIP lookup: pitcher_id → (FIP, IP) and name → (FIP, IP)."""
    fips_by_id = {}
    fips_by_name = {}
    lg_fips = []
    with open(path) as f:
        for row in csv.DictReader(f):
            pid = int(float(row['pitcher_id']))
            fip = float(row['fip'])
            ip = float(row['ip'])
            name = row.get('name', '').strip()
            fips_by_id[pid] = (fip, ip)
            if name:
                fips_by_name[normalize_name(name)] = (fip, ip)
            if ip >= 10:
                lg_fips.append((fip, ip))
    # IP-weighted league average FIP
    if lg_fips:
        total_ip = sum(ip for _, ip in lg_fips)
        lg_avg = sum(fip * ip for fip, ip in lg_fips) / total_ip
    else:
        lg_avg = 4.00
    return fips_by_id, fips_by_name, lg_avg


def load_ballpark_data():
    """Load ballpark info and pairwise distances."""
    # Load park info (team → tz_offset)
    tz_offsets = {}
    info_path = os.path.join(DATA_DIR, 'ballpark_info.csv')
    if os.path.exists(info_path):
        with open(info_path) as f:
            for row in csv.DictReader(f):
                tz_offsets[row['team']] = int(row['tz_offset_utc'])

    # Load pairwise distances
    distances = {}
    dist_path = os.path.join(DATA_DIR, 'ballpark_distances.csv')
    if os.path.exists(dist_path):
        with open(dist_path) as f:
            for row in csv.DictReader(f):
                d = float(row['distance_miles'])
                distances[(row['team_a'], row['team_b'])] = d
                distances[(row['team_b'], row['team_a'])] = d
    return tz_offsets, distances


def load_rolling_fip(path):
    """Load pre-computed rolling FIP: (pitcher_id, date) → rolling_fip."""
    rolling = {}
    if not os.path.exists(path):
        return rolling
    with open(path) as f:
        for row in csv.DictReader(f):
            pid = int(float(row['pitcher_id']))
            date = row['date']
            fip = float(row['rolling_fip'])
            starts = int(row['starts_in_window'])
            if starts >= 3:  # Need at least 3 prior starts for reliable rolling FIP
                rolling[(pid, date)] = fip
    return rolling


def load_bullpen_fip(path):
    """Load team bullpen FIP: team_abbr → bullpen_fip (MLB teams only)."""
    bp = {}
    if not os.path.exists(path):
        return bp, 4.00
    lg_fips = []
    with open(path) as f:
        for row in csv.DictReader(f):
            team_name = row['team']
            abbr = TEAM_NAME_TO_ABBR.get(team_name)
            if not abbr:
                continue  # Skip minor league / international teams
            fip = float(row['bullpen_fip'])
            ip = float(row['bullpen_ip'])
            bp[abbr] = fip
            lg_fips.append((fip, ip))
    # IP-weighted league average bullpen FIP
    if lg_fips:
        total_ip = sum(ip for _, ip in lg_fips)
        lg_avg = sum(fip * ip for fip, ip in lg_fips) / total_ip
    else:
        lg_avg = 4.00
    return bp, lg_avg


def load_park_factors(season):
    """Load park factors for a season."""
    try:
        from park_factors import PARK_FACTORS, DEFAULT_PARK_FACTORS
        return PARK_FACTORS.get(season, DEFAULT_PARK_FACTORS)
    except ImportError:
        return {}


def load_schedule(path):
    """Load schedule CSV, return list of game dicts sorted by date."""
    games = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row['status'] != 'Final':
                continue
            home_sp = row.get('homeStartingPitcherId', '').strip()
            away_sp = row.get('awayStartingPitcherId', '').strip()
            games.append({
                'date': row['date'],
                'home': row['homeTeam'],
                'away': row['awayTeam'],
                'home_score': int(row['homeScore']),
                'away_score': int(row['awayScore']),
                'home_sp_id': int(float(home_sp)) if home_sp else None,
                'away_sp_id': int(float(away_sp)) if away_sp else None,
                'home_sp_name': row.get('homeStartingPitcherName', '').strip(),
                'away_sp_name': row.get('awayStartingPitcherName', '').strip(),
                'venue': row.get('venueName', ''),
            })
    games.sort(key=lambda g: g['date'])
    return games


# === TRAVEL DETECTION ===

def build_travel_tracker(games):
    """For each team, determine where they played their previous game.

    Returns dict: (team, date) → previous_venue_team
    This lets us detect if a team just traveled a long distance.
    """
    # Track each team's game history in order
    team_games = defaultdict(list)
    for g in games:
        team_games[g['home']].append({'date': g['date'], 'venue_team': g['home']})
        team_games[g['away']].append({'date': g['date'], 'venue_team': g['home']})

    # For each game, store where the team previously played
    prev_venue = {}
    for team, tg in team_games.items():
        tg.sort(key=lambda x: x['date'])
        for i in range(1, len(tg)):
            prev_venue[(team, tg[i]['date'])] = tg[i - 1]['venue_team']
    return prev_venue


def get_travel_penalty(team, game_date, venue_team, prev_venue, tz_offsets, distances):
    """Calculate travel fatigue penalty for a team arriving at this game.

    Penalty applied when:
      - Team traveled from a different city (not same venue)
      - Distance > 1000 miles
      - Timezone shift is 2+ hours eastward
    """
    prev = prev_venue.get((team, game_date))
    if prev is None or prev == venue_team:
        return 0

    dist = distances.get((prev, venue_team), 0)
    if dist < 1000:
        return 0

    tz_from = tz_offsets.get(prev, -6)
    tz_to = tz_offsets.get(venue_team, -6)
    tz_shift = tz_to - tz_from  # positive = traveling east

    if tz_shift >= 2:
        return TRAVEL_PENALTY
    return 0


# === MAIN MODEL ===

def run_model(season, use_fip=True, use_travel=True, use_injuries=False,
              use_rolling_fip=False, use_bullpen=False, use_park=False,
              quiet=False):
    """Run the enhanced model on a full season."""

    def log(msg):
        if not quiet:
            print(msg)

    # Load data
    schedule_path = os.path.join(DATA_DIR, f'schedule_{season}_full.csv')
    elo_path = os.path.join(DATA_DIR, f'elo_rating_end_of_{season - 1}.csv')
    fip_path = os.path.join(DATA_DIR, f'pitcher_fip_{season}.csv')

    if not os.path.exists(schedule_path):
        log(f'Schedule not found: {schedule_path}')
        return None
    if not os.path.exists(elo_path):
        log(f'ELO baseline not found: {elo_path}')
        return None

    games = load_schedule(schedule_path)
    elos = load_elo_baseline(elo_path)
    log(f'Loaded {len(games)} games, {len(elos)} team ELO ratings')

    # Season FIP (fallback when rolling FIP not available)
    fip_by_id, fip_by_name, lg_fip = {}, {}, 4.00
    if (use_fip or use_rolling_fip) and os.path.exists(fip_path):
        fip_by_id, fip_by_name, lg_fip = load_fip_data(fip_path)
        log(f'Loaded {len(fip_by_id)} pitcher FIPs ({len(fip_by_name)} by name, league avg: {lg_fip:.3f})')
    elif use_fip or use_rolling_fip:
        log(f'FIP data not found: {fip_path} — skipping FIP adjustment')
        use_fip = False
        use_rolling_fip = False

    # Rolling FIP
    rolling_fip = {}
    if use_rolling_fip:
        rolling_path = os.path.join(DATA_DIR, f'rolling_fip_{season}.csv')
        rolling_fip = load_rolling_fip(rolling_path)
        if rolling_fip:
            log(f'Loaded {len(rolling_fip)} rolling FIP entries')
        else:
            log(f'Rolling FIP not found — using season FIP as fallback')

    # Bullpen FIP
    bullpen_fip, lg_bp_fip = {}, 4.00
    if use_bullpen:
        bp_path = os.path.join(DATA_DIR, f'bullpen_fip_{season}.csv')
        bullpen_fip, lg_bp_fip = load_bullpen_fip(bp_path)
        if bullpen_fip:
            log(f'Loaded bullpen FIP for {len(bullpen_fip)} teams (league avg: {lg_bp_fip:.3f})')
        else:
            log(f'Bullpen FIP not found — skipping bullpen adjustment')
            use_bullpen = False

    # Park factors
    park_factors = {}
    if use_park:
        park_factors = load_park_factors(season)
        if park_factors:
            log(f'Loaded park factors for {len(park_factors)} teams')
        else:
            log(f'Park factors not found — skipping park adjustment')
            use_park = False

    # Travel
    tz_offsets, distances = {}, {}
    if use_travel:
        tz_offsets, distances = load_ballpark_data()
        if distances:
            log(f'Loaded ballpark distances ({len(distances)} pairs)')
        else:
            log('Ballpark distance data not found — skipping travel adjustment')
            use_travel = False

    # Injury data
    injury_war = {}
    if use_injuries:
        injury_path = os.path.join(DATA_DIR, f'injury_impact_teams_{season}.csv')
        if os.path.exists(injury_path):
            with open(injury_path) as f:
                for row in csv.DictReader(f):
                    injury_war[row['team']] = float(row['total_war_lost'])
            log(f'Loaded injury data for {len(injury_war)} teams')
        else:
            log(f'Injury data not found — skipping injury adjustment')
            use_injuries = False

    # Build travel tracker
    prev_venue = {}
    if use_travel:
        prev_venue = build_travel_tracker(games)

    # Feature labels
    features = ['ELO']
    if use_rolling_fip:
        features.append('RollingFIP')
    elif use_fip:
        features.append('FIP')
    if use_bullpen:
        features.append('Bullpen')
    if use_park:
        features.append('Park')
    if use_travel:
        features.append('Travel')
    if use_injuries:
        features.append('Injuries')
    log(f'\nModel features: {" + ".join(features)}\n')

    # Process games chronologically
    results = []
    correct = 0
    total_log_loss = 0.0
    total_brier = 0.0
    fip_applied = 0
    rolling_fip_used = 0
    bullpen_applied = 0
    park_applied = 0
    travel_applied = 0

    for game in games:
        home, away = game['home'], game['away']
        home_elo = elos.get(home, ELO_INIT)
        away_elo = elos.get(away, ELO_INIT)

        # --- Adjustments ---
        home_adj = 0
        away_adj = 0

        # SP FIP adjustment: use rolling FIP if available, fall back to season FIP
        # Season FIP is regressed toward league average based on IP (Bayesian shrinkage)
        home_fip_adj = 0
        away_fip_adj = 0
        if use_fip or use_rolling_fip:
            # Home starter FIP
            home_fip = None
            if use_rolling_fip and game['home_sp_id']:
                home_fip = rolling_fip.get((game['home_sp_id'], game['date']))
                if home_fip is not None:
                    rolling_fip_used += 1
            if home_fip is None:  # Fall back to season FIP (with Bayesian regression)
                fip_data = fip_by_id.get(game['home_sp_id'])
                if fip_data is None and game.get('home_sp_name'):
                    fip_data = fip_by_name.get(normalize_name(game['home_sp_name']))
                if fip_data is not None:
                    raw_fip, pitcher_ip = fip_data
                    # Regress toward league avg: more IP = more weight on actual FIP
                    home_fip = (pitcher_ip * raw_fip + FIP_PRIOR_IP * lg_fip) / (pitcher_ip + FIP_PRIOR_IP)

            # Away starter FIP
            away_fip = None
            if use_rolling_fip and game['away_sp_id']:
                away_fip = rolling_fip.get((game['away_sp_id'], game['date']))
                if away_fip is not None:
                    rolling_fip_used += 1
            if away_fip is None:  # Fall back to season FIP (with Bayesian regression)
                fip_data = fip_by_id.get(game['away_sp_id'])
                if fip_data is None and game.get('away_sp_name'):
                    fip_data = fip_by_name.get(normalize_name(game['away_sp_name']))
                if fip_data is not None:
                    raw_fip, pitcher_ip = fip_data
                    away_fip = (pitcher_ip * raw_fip + FIP_PRIOR_IP * lg_fip) / (pitcher_ip + FIP_PRIOR_IP)

            if home_fip is not None:
                home_fip_adj = (lg_fip - home_fip) * FIP_WEIGHT
                fip_applied += 1
            if away_fip is not None:
                away_fip_adj = (lg_fip - away_fip) * FIP_WEIGHT
                fip_applied += 1

        # Park factor scaling: adjust FIP impact based on venue run environment
        # Hitter-friendly parks (PF>100) reduce pitcher advantage, pitcher-friendly parks enhance it
        park_adj_factor = 1.0
        if use_park:
            pf = park_factors.get(home, 100)
            if pf != 100:
                park_adj_factor = 100.0 / pf * PARK_FACTOR_SCALE + (1 - PARK_FACTOR_SCALE)
                park_applied += 1
            home_fip_adj *= park_adj_factor
            away_fip_adj *= park_adj_factor

        home_adj += home_fip_adj
        away_adj += away_fip_adj

        # Bullpen FIP adjustment: better bullpen → ELO boost
        home_bp_adj = 0
        away_bp_adj = 0
        if use_bullpen:
            home_bp_fip = bullpen_fip.get(home)
            away_bp_fip = bullpen_fip.get(away)
            if home_bp_fip is not None:
                home_bp_adj = (lg_bp_fip - home_bp_fip) * BULLPEN_FIP_WEIGHT
                # Park-adjust bullpen FIP too
                if use_park:
                    home_bp_adj *= park_adj_factor
                home_adj += home_bp_adj
                bullpen_applied += 1
            if away_bp_fip is not None:
                away_bp_adj = (lg_bp_fip - away_bp_fip) * BULLPEN_FIP_WEIGHT
                if use_park:
                    away_bp_adj *= park_adj_factor
                away_adj += away_bp_adj
                bullpen_applied += 1

        # Travel penalty (away team only — home team is at home)
        travel_adj = 0
        if use_travel:
            travel_adj = get_travel_penalty(
                away, game['date'], home, prev_venue, tz_offsets, distances
            )
            away_adj -= travel_adj
            if travel_adj > 0:
                travel_applied += 1

        # Injury adjustment
        home_injury_adj = 0
        away_injury_adj = 0
        if use_injuries:
            home_war_lost = injury_war.get(home, 0)
            away_war_lost = injury_war.get(away, 0)
            home_injury_adj = home_war_lost * INJURY_WAR_WEIGHT
            away_injury_adj = away_war_lost * INJURY_WAR_WEIGHT
            home_adj -= home_injury_adj
            away_adj -= away_injury_adj

        # Compute win probability with shrinkage toward 50%
        adj_home_elo = home_elo + home_adj
        adj_away_elo = away_elo + away_adj
        raw_prob = expected_score(adj_home_elo, adj_away_elo, ELO_HFA)
        home_win_prob = PROB_SHRINKAGE + (1 - 2 * PROB_SHRINKAGE) * raw_prob

        # Actual outcome
        home_won = 1 if game['home_score'] > game['away_score'] else 0
        score_diff = game['home_score'] - game['away_score']

        # Metrics
        if (home_win_prob >= 0.5 and home_won) or (home_win_prob < 0.5 and not home_won):
            correct += 1

        # Log loss (clamp to avoid log(0))
        p = max(min(home_win_prob, 0.999), 0.001)
        log_loss = -(home_won * math.log(p) + (1 - home_won) * math.log(1 - p))
        total_log_loss += log_loss

        # Brier score
        brier = (home_win_prob - home_won) ** 2
        total_brier += brier

        results.append({
            'date': game['date'],
            'home': home,
            'away': away,
            'home_score': game['home_score'],
            'away_score': game['away_score'],
            'home_elo': round(home_elo, 1),
            'away_elo': round(away_elo, 1),
            'home_fip_adj': round(home_fip_adj, 1),
            'away_fip_adj': round(away_fip_adj, 1),
            'home_bp_adj': round(home_bp_adj, 1),
            'away_bp_adj': round(away_bp_adj, 1),
            'travel_penalty': round(travel_adj, 1),
            'home_win_prob': round(home_win_prob, 4),
            'home_won': home_won,
            'log_loss': round(log_loss, 4),
            'brier': round(brier, 4),
        })

        # Update ELO ratings based on actual result
        elo_diff = home_elo - away_elo
        mov = margin_of_victory_mult(score_diff, elo_diff) if score_diff != 0 else 1.0
        exp_home = expected_score(home_elo, away_elo, ELO_HFA)
        elos[home] = update_elo(home_elo, exp_home, home_won, ELO_K, mov)
        elos[away] = update_elo(away_elo, 1 - exp_home, 1 - home_won, ELO_K, mov)

    # Summary
    n = len(results)
    accuracy = correct / n if n > 0 else 0
    avg_log_loss = total_log_loss / n if n > 0 else 0
    avg_brier = total_brier / n if n > 0 else 0

    log(f'=== {season} RESULTS ({" + ".join(features)}) ===')
    log(f'Games:        {n}')
    log(f'Accuracy:     {accuracy:.4f} ({correct}/{n})')
    log(f'Log Loss:     {avg_log_loss:.4f}')
    log(f'Brier Score:  {avg_brier:.4f}')
    if use_fip or use_rolling_fip:
        log(f'FIP applied:  {fip_applied} pitcher-games')
    if use_rolling_fip:
        log(f'Rolling FIP:  {rolling_fip_used} pitcher-games (rest used season FIP)')
    if use_bullpen:
        log(f'Bullpen adj:  {bullpen_applied} team-games')
    if use_park:
        log(f'Park adj:     {park_applied} games')
    if use_travel:
        log(f'Travel pens:  {travel_applied} games')

    if not quiet:
        # Calibration buckets
        print(f'\n=== CALIBRATION ===')
        print(f'{"Prob Bucket":<15} {"Games":>6} {"Predicted":>10} {"Actual":>8} {"Diff":>8}')
        print('-' * 50)
        buckets = defaultdict(lambda: {'count': 0, 'pred_sum': 0.0, 'actual_sum': 0})
        for r in results:
            bucket = int(r['home_win_prob'] * 10) / 10  # 0.0, 0.1, ..., 0.9
            bucket = min(bucket, 0.9)
            buckets[bucket]['count'] += 1
            buckets[bucket]['pred_sum'] += r['home_win_prob']
            buckets[bucket]['actual_sum'] += r['home_won']

        for bucket in sorted(buckets.keys()):
            b = buckets[bucket]
            pred_avg = b['pred_sum'] / b['count']
            actual_avg = b['actual_sum'] / b['count']
            diff = actual_avg - pred_avg
            label = f'{bucket:.1f}-{bucket+0.1:.1f}'
            print(f'{label:<15} {b["count"]:>6} {pred_avg:>10.4f} {actual_avg:>8.4f} {diff:>+8.4f}')

        # Write results CSV
        label = '_'.join(f.lower() for f in features)
        output_path = os.path.join(DATA_DIR, f'model_results_{season}_{label}.csv')
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'home', 'away', 'home_score', 'away_score',
                'home_elo', 'away_elo', 'home_fip_adj', 'away_fip_adj',
                'home_bp_adj', 'away_bp_adj',
                'travel_penalty', 'home_win_prob', 'home_won', 'log_loss', 'brier',
            ])
            writer.writeheader()
            writer.writerows(results)
        print(f'\nWrote {output_path}')

    return {
        'season': season,
        'features': features,
        'games': n,
        'accuracy': accuracy,
        'log_loss': avg_log_loss,
        'brier': avg_brier,
    }


def sweep_parameters(season, v2=True):
    """Sweep model parameters to find best values.

    v2=True sweeps all features (rolling FIP, bullpen, park factors).
    v2=False sweeps v1 features only (season FIP, travel).
    """
    global FIP_WEIGHT, FIP_PRIOR_IP, TRAVEL_PENALTY, PROB_SHRINKAGE, BULLPEN_FIP_WEIGHT, PARK_FACTOR_SCALE

    print(f'=== PARAMETER SWEEP {"v2" if v2 else "v1"} — {season} ===\n')

    best = {'log_loss': 999, 'params': {}}
    sweep_results = []

    if v2:
        # V2 sweep: FIP_WEIGHT, BULLPEN_FIP_WEIGHT, PARK_FACTOR_SCALE, PROB_SHRINKAGE
        # Travel stays fixed at 10 (minimal impact), no injuries (date-specific not ready)
        fip_range = [25, 30, 35, 40, 45, 50]
        bp_range = [0, 5, 10, 15, 20, 25]
        park_range = [0.0, 0.5, 1.0]
        shrink_range = [0.06, 0.08, 0.10, 0.12, 0.14]

        total = len(fip_range) * len(bp_range) * len(park_range) * len(shrink_range)
        i = 0

        for fw in fip_range:
            for bw in bp_range:
                for pf in park_range:
                    for ps in shrink_range:
                        i += 1
                        FIP_WEIGHT = fw
                        BULLPEN_FIP_WEIGHT = bw
                        PARK_FACTOR_SCALE = pf
                        PROB_SHRINKAGE = ps
                        TRAVEL_PENALTY = 10  # Fixed

                        result = run_model(
                            season, use_fip=True, use_travel=True,
                            use_rolling_fip=True, use_bullpen=(bw > 0),
                            use_park=(pf > 0), quiet=True,
                        )
                        if result:
                            sweep_results.append({
                                'fip_weight': fw, 'bullpen_weight': bw,
                                'park_scale': pf, 'prob_shrinkage': ps,
                                **result,
                            })
                            if result['log_loss'] < best['log_loss']:
                                best = {'log_loss': result['log_loss'], 'params': {
                                    'fip_weight': fw, 'bullpen_weight': bw,
                                    'park_scale': pf, 'prob_shrinkage': ps,
                                }, **result}

                        if i % 50 == 0:
                            print(f'  {i}/{total} combinations tested...')

        print(f'\n=== SWEEP RESULTS (top 10 by log loss) ===')
        sweep_results.sort(key=lambda x: x['log_loss'])
        print(f'{"FIP_W":>6} {"BP_W":>5} {"PARK":>5} {"SHRINK":>7} {"Acc":>8} {"LogLoss":>9} {"Brier":>8}')
        print('-' * 55)
        for r in sweep_results[:10]:
            print(f'{r["fip_weight"]:>6} {r["bullpen_weight"]:>5} {r["park_scale"]:>5.1f} '
                  f'{r["prob_shrinkage"]:>7.2f} {r["accuracy"]:>8.4f} {r["log_loss"]:>9.4f} '
                  f'{r["brier"]:>8.4f}')

        print(f'\nBest: FIP_WEIGHT={best["params"]["fip_weight"]}, '
              f'BULLPEN_WEIGHT={best["params"]["bullpen_weight"]}, '
              f'PARK_SCALE={best["params"]["park_scale"]:.1f}, '
              f'PROB_SHRINKAGE={best["params"]["prob_shrinkage"]:.2f}')
    else:
        # V1 sweep: FIP_WEIGHT, FIP_PRIOR_IP, PROB_SHRINKAGE
        # Travel fixed at 10 (minimal signal)
        fip_range = [25, 30, 35, 40, 45, 50]
        prior_range = [0, 25, 50, 75, 100]  # 0 = no regression
        shrink_range = [0.08, 0.10, 0.12, 0.14, 0.16]

        total = len(fip_range) * len(prior_range) * len(shrink_range)
        i = 0

        for fw in fip_range:
            for pp in prior_range:
                for ps in shrink_range:
                    i += 1
                    FIP_WEIGHT = fw
                    FIP_PRIOR_IP = pp
                    TRAVEL_PENALTY = 10
                    PROB_SHRINKAGE = ps

                    result = run_model(season, use_fip=True, use_travel=True,
                                       use_injuries=False, quiet=True)
                    if result:
                        sweep_results.append({
                            'fip_weight': fw, 'fip_prior_ip': pp,
                            'prob_shrinkage': ps, **result,
                        })
                        if result['log_loss'] < best['log_loss']:
                            best = {'log_loss': result['log_loss'], 'params': {
                                'fip_weight': fw, 'fip_prior_ip': pp, 'prob_shrinkage': ps,
                            }, **result}

                    if i % 50 == 0:
                        print(f'  {i}/{total} combinations tested...')

        print(f'\n=== SWEEP RESULTS (top 10 by log loss) ===')
        sweep_results.sort(key=lambda x: x['log_loss'])
        print(f'{"FIP_W":>6} {"PRIOR":>6} {"SHRINK":>7} {"Acc":>8} {"LogLoss":>9} {"Brier":>8}')
        print('-' * 50)
        for r in sweep_results[:10]:
            print(f'{r["fip_weight"]:>6} {r["fip_prior_ip"]:>6} {r["prob_shrinkage"]:>7.2f} '
                  f'{r["accuracy"]:>8.4f} {r["log_loss"]:>9.4f} {r["brier"]:>8.4f}')

        print(f'\nBest: FIP_WEIGHT={best["params"]["fip_weight"]}, '
              f'FIP_PRIOR_IP={best["params"]["fip_prior_ip"]}, '
              f'PROB_SHRINKAGE={best["params"]["prob_shrinkage"]:.2f}')

    print(f'  Log Loss: {best["log_loss"]:.4f}, Accuracy: {best["accuracy"]:.4f}, '
          f'Brier: {best["brier"]:.4f}')

    # Write sweep results
    suffix = 'v2' if v2 else 'v1'
    output_path = os.path.join(DATA_DIR, f'param_sweep_{season}_{suffix}.csv')
    fieldnames = list(sweep_results[0].keys()) if sweep_results else []
    # Remove nested 'features' list from CSV
    for r in sweep_results:
        r.pop('features', None)
    with open(output_path, 'w', newline='') as f:
        fieldnames = [k for k in sweep_results[0].keys()] if sweep_results else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sweep_results)
    print(f'Wrote {output_path}')

    return best


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    base_only = '--base-only' in sys.argv
    v1 = '--v1' in sys.argv
    do_sweep = '--sweep' in sys.argv
    do_sweep_v1 = '--sweep-v1' in sys.argv

    if do_sweep:
        sweep_parameters(season, v2=True)
        return
    if do_sweep_v1:
        sweep_parameters(season, v2=False)
        return

    if base_only:
        # ELO only
        print(f'=== BASE ELO MODEL — {season} ===\n')
        run_model(season, use_fip=False, use_travel=False)
        return

    if v1:
        # V1: season FIP + travel (no rolling FIP, bullpen, or park factors)
        print(f'=== V1 ENHANCED MODEL — {season} ===\n')
        enhanced = run_model(season, use_fip=True, use_travel=True)
    else:
        # V2 (default): rolling FIP + bullpen + park factors + travel
        print(f'=== V2 ENHANCED MODEL — {season} ===\n')
        enhanced = run_model(
            season, use_fip=True, use_travel=True,
            use_rolling_fip=True, use_bullpen=True, use_park=True,
        )

    # Run base ELO for comparison
    print(f'\n{"=" * 60}')
    print(f'Running base ELO-only model for comparison...\n')
    base = run_model(season, use_fip=False, use_travel=False)

    if enhanced and base:
        label = 'V1' if v1 else 'V2'
        print(f'\n=== COMPARISON: {season} ({label} vs Base ELO) ===')
        print(f'{"Metric":<15} {"Base ELO":>12} {label:>12} {"Delta":>12}')
        print('-' * 55)
        for metric in ['accuracy', 'log_loss', 'brier']:
            b = base[metric]
            e = enhanced[metric]
            delta = e - b
            better = '+' if (metric == 'accuracy' and delta > 0) or \
                           (metric != 'accuracy' and delta < 0) else '-'
            print(f'{metric:<15} {b:>12.4f} {e:>12.4f} {delta:>+12.4f} {better}')


if __name__ == '__main__':
    main()
