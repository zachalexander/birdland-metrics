"""
mlb-season-projections — Monte Carlo season simulation + standings predictions.

Replaces: mlb-season-simulations + mlb-stats-api-games-back-wc

Uses the enhanced prediction model:
- FIP-adjusted ELO: shifts each team's effective ELO based on starting pitcher FIP
- Probability shrinkage: pulls extreme probabilities toward 50% to correct overconfidence
- ELO ratings themselves are NOT modified — adjustments are prediction-layer only

Changes from original:
- Merged two Lambdas into one (simulations + standings/GB in a single run)
- Added HFA to simulation win probability
- Enhanced with FIP adjustment + probability shrinkage
- Added playoff-odds-latest.json output
- Uses shared team_codes.py for league/division maps
- Uses shared config for all bucket names
- Writes standings-latest.json and projections-latest.json for Angular frontend
- No runtime pip install (pandas/pyarrow from Lambda Layer)
"""
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from mlb_common.config import (
    SCHEDULE_BUCKET, SCHEDULE_KEY, PREDICTIONS_BUCKET,
    ELO_BUCKET, ELO_TABLE, ELO_HFA, SIM_COUNT, FIP_KEY,
    SEASON_YEAR,
)
from mlb_common.aws_helpers import (
    read_csv_from_s3, write_csv_to_s3, write_json_to_s3,
    write_parquet_to_s3, read_json_from_s3, dynamo_scan,
)
from mlb_common.team_codes import TEAM_LEAGUE, TEAM_DIVISION
from mlb_common.elo import expected_score
from mlb_common.fip import fip_adjustment, apply_shrinkage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_latest_elo_ratings():
    """Fetch the most recent ELO rating per team from DynamoDB."""
    items = dynamo_scan(ELO_TABLE)
    latest = {}
    for item in items:
        team = item['team']
        elo = float(item['elo'])
        updated = item.get('last_updated', '')
        if team not in latest or updated > latest[team]['updated']:
            latest[team] = {'elo': elo, 'updated': updated}
    return {team: val['elo'] for team, val in latest.items()}


def load_fip_data():
    """Load FIP data from S3 (written by mlb-elo-compute)."""
    try:
        fip_meta = read_json_from_s3(ELO_BUCKET, 'fip-latest.json')
        lg_fip = fip_meta['lg_fip']

        fip_df = read_csv_from_s3(ELO_BUCKET, FIP_KEY)
        fip_dict = {}
        for _, row in fip_df.iterrows():
            fip_dict[int(row['pitcher_id'])] = {
                'fip': float(row['fip']),
                'ip': float(row['ip']),
                'name': row['name'],
            }
        logger.info(f"Loaded FIP data for {len(fip_dict)} pitchers (lgFIP={lg_fip:.3f})")
        return fip_dict, lg_fip
    except Exception as e:
        logger.warning(f"Could not load FIP data — using raw ELO only: {e}")
        return None, None


def enhanced_probability(elo_home, elo_away, home_pitcher_id, away_pitcher_id, fip_dict, lg_fip):
    """
    Compute FIP-adjusted, shrinkage-corrected win probability.

    If FIP data is unavailable, falls back to raw ELO with shrinkage only.
    """
    home_adj, away_adj = 0, 0
    if fip_dict is not None and lg_fip is not None:
        home_adj, away_adj = fip_adjustment(home_pitcher_id, away_pitcher_id, fip_dict, lg_fip)

    raw_prob = expected_score(elo_home + home_adj, elo_away + away_adj, hfa=ELO_HFA)
    return apply_shrinkage(raw_prob)


def generate_next_game_predictions(schedule_df, elo_ratings, fip_dict, lg_fip):
    """Find each team's next game and compute enhanced win probability."""
    today = pd.Timestamp.today().normalize()
    future = schedule_df[schedule_df['date'] >= today].sort_values('date')

    next_games = []
    seen_teams = set()

    for _, row in future.iterrows():
        home, away = row['homeTeam'], row['awayTeam']
        game_date = row['date'].date()

        # Get starting pitcher IDs if available
        home_sp = int(row['homeStartingPitcherId']) if pd.notna(row.get('homeStartingPitcherId')) else None
        away_sp = int(row['awayStartingPitcherId']) if pd.notna(row.get('awayStartingPitcherId')) else None

        if home not in seen_teams and home in elo_ratings and away in elo_ratings:
            seen_teams.add(home)
            wp = enhanced_probability(elo_ratings[home], elo_ratings[away], home_sp, away_sp, fip_dict, lg_fip)
            # Also compute raw ELO prob for comparison
            raw_wp = expected_score(elo_ratings[home], elo_ratings[away], hfa=ELO_HFA)

            home_sp_name = row.get('homeStartingPitcherName', '')
            away_sp_name = row.get('awayStartingPitcherName', '')

            next_games.append([
                home, away, game_date, 'home', wp, raw_wp,
                elo_ratings[home], elo_ratings[away],
                home_sp_name if pd.notna(home_sp_name) else '',
                away_sp_name if pd.notna(away_sp_name) else '',
            ])

        if away not in seen_teams and away in elo_ratings and home in elo_ratings:
            seen_teams.add(away)
            wp_away = 1 - enhanced_probability(elo_ratings[home], elo_ratings[away], home_sp, away_sp, fip_dict, lg_fip)
            raw_wp_away = 1 - expected_score(elo_ratings[home], elo_ratings[away], hfa=ELO_HFA)

            home_sp_name = row.get('homeStartingPitcherName', '')
            away_sp_name = row.get('awayStartingPitcherName', '')

            next_games.append([
                away, home, game_date, 'away', wp_away, raw_wp_away,
                elo_ratings[away], elo_ratings[home],
                away_sp_name if pd.notna(away_sp_name) else '',
                home_sp_name if pd.notna(home_sp_name) else '',
            ])

    df = pd.DataFrame(next_games, columns=[
        'team', 'opponent', 'date', 'home_away', 'win_probability', 'raw_win_probability',
        'elo_team', 'elo_opp', 'team_starter', 'opp_starter',
    ])
    write_csv_to_s3(df, PREDICTIONS_BUCKET, 'next_game_win_expectancy.csv')
    return df


def simulate_season(schedule_df, elo_ratings, fip_dict, lg_fip):
    """Run Monte Carlo simulations using enhanced probabilities."""
    completed = schedule_df.dropna(subset=['homeScore', 'awayScore'])
    remaining = schedule_df[schedule_df['homeScore'].isna() | schedule_df['awayScore'].isna()]

    teams = sorted(set(schedule_df['homeTeam']) | set(schedule_df['awayTeam']))
    team_idx = {team: i for i, team in enumerate(teams)}
    sim_matrix = np.zeros((SIM_COUNT, len(teams)))

    # Seed with actual wins
    actual_wins = defaultdict(int)
    for _, row in completed.iterrows():
        if row['homeScore'] > row['awayScore']:
            actual_wins[row['homeTeam']] += 1
        else:
            actual_wins[row['awayTeam']] += 1
    for team, idx in team_idx.items():
        sim_matrix[:, idx] = actual_wins[team]

    # Simulate remaining games with enhanced probabilities
    for _, row in remaining.iterrows():
        home, away = row['homeTeam'], row['awayTeam']
        if home not in elo_ratings or away not in elo_ratings:
            continue

        # Get starting pitcher IDs if available
        home_sp = int(row['homeStartingPitcherId']) if pd.notna(row.get('homeStartingPitcherId')) else None
        away_sp = int(row['awayStartingPitcherId']) if pd.notna(row.get('awayStartingPitcherId')) else None

        p_home_win = enhanced_probability(
            elo_ratings[home], elo_ratings[away], home_sp, away_sp, fip_dict, lg_fip
        )

        draws = np.random.rand(SIM_COUNT)
        home_wins = draws < p_home_win
        sim_matrix[:, team_idx[home]] += home_wins.astype(int)
        sim_matrix[:, team_idx[away]] += (~home_wins).astype(int)

    # Save full simulation matrix as parquet
    df_sim = pd.DataFrame(sim_matrix, columns=teams)
    df_sim.insert(0, 'sim_id', range(SIM_COUNT))
    write_parquet_to_s3(df_sim, PREDICTIONS_BUCKET, 'season_win_simulations.parquet')

    # Compute summary statistics
    summary = []
    for team in teams:
        values = df_sim[team].values
        summary.append({
            'team': team,
            'avg_wins': round(values.mean(), 2),
            'median_wins': int(np.median(values)),
            'std_dev': round(values.std(), 2),
            'p10': int(np.percentile(values, 10)),
            'p25': int(np.percentile(values, 25)),
            'p75': int(np.percentile(values, 75)),
            'p90': int(np.percentile(values, 90)),
        })

    df_summary = pd.DataFrame(summary)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    write_csv_to_s3(df_summary, PREDICTIONS_BUCKET, f'season_win_projection_summary_{today_str}.csv')

    return df_summary, df_sim


def compute_playoff_odds(df_sim, teams, injury_adjusted=False):
    """
    Compute playoff probability for each AL team from simulation results.

    MLB format: 3 division winners + 3 wild cards = top 6 in each league make playoffs.
    """
    al_teams = [t for t in teams if TEAM_LEAGUE.get(t) == 'AL']
    al_divisions = {}
    for t in al_teams:
        div = TEAM_DIVISION.get(t, 'Unknown')
        al_divisions.setdefault(div, []).append(t)

    n_sims = len(df_sim)
    playoff_count = defaultdict(int)
    division_count = defaultdict(int)
    wildcard_count = defaultdict(int)

    for sim_idx in range(n_sims):
        # Get wins for each AL team in this simulation
        al_wins = {t: df_sim[t].iloc[sim_idx] for t in al_teams}

        # Division winners: best record in each division
        div_winners = set()
        for div, div_teams in al_divisions.items():
            winner = max(div_teams, key=lambda t: al_wins[t])
            div_winners.add(winner)
            division_count[winner] += 1

        # Wild cards: next 3 best records among non-division winners
        remaining = [(t, al_wins[t]) for t in al_teams if t not in div_winners]
        remaining.sort(key=lambda x: x[1], reverse=True)
        wc_teams = {t for t, _ in remaining[:3]}
        for t in wc_teams:
            wildcard_count[t] += 1

        # All playoff teams
        for t in div_winners | wc_teams:
            playoff_count[t] += 1

    # Build results
    odds = []
    for t in al_teams:
        odds.append({
            'team': t,
            'playoff_pct': round(100 * playoff_count[t] / n_sims, 1),
            'division_pct': round(100 * division_count[t] / n_sims, 1),
            'wildcard_pct': round(100 * wildcard_count[t] / n_sims, 1),
        })
    odds.sort(key=lambda x: x['playoff_pct'], reverse=True)

    odds_payload = {
        'updated': datetime.utcnow().isoformat(),
        'simulations': n_sims,
        'injury_adjusted': injury_adjusted,
        'odds': odds,
    }
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    write_json_to_s3(odds_payload, PREDICTIONS_BUCKET, 'playoff-odds-latest.json')
    write_json_to_s3(odds_payload, PREDICTIONS_BUCKET, f'playoff-odds_{today_str}.json')

    # Append daily snapshot to playoff-odds-history.json
    try:
        history = read_json_from_s3(PREDICTIONS_BUCKET, 'playoff-odds-history.json')
    except Exception:
        history = []
    for o in odds:
        history.append({
            'date': today_str,
            'team': o['team'],
            'playoff_pct': o['playoff_pct'],
            'division_pct': o['division_pct'],
            'wildcard_pct': o['wildcard_pct'],
        })
    write_json_to_s3(history, PREDICTIONS_BUCKET, 'playoff-odds-history.json')
    logger.info(f"Appended {len(odds)} rows to playoff-odds-history.json for {today_str}")

    # Log Orioles specifically
    bal = next((o for o in odds if o['team'] == 'BAL'), None)
    if bal:
        logger.info(f"BAL playoff odds: {bal['playoff_pct']}% (div {bal['division_pct']}%, WC {bal['wildcard_pct']}%)")

    return odds


def compute_standings_and_gb(df_summary, injury_adjusted=False):
    """
    Compute projected end-of-year standings and Orioles games back from WC3.
    Previously done in a separate Lambda (mlb-stats-api-games-back-wc).
    """
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    # AL standings sorted by median wins
    al_teams = df_summary[df_summary['team'].isin(
        [t for t, league in TEAM_LEAGUE.items() if league == 'AL']
    )].sort_values('median_wins', ascending=False)

    write_csv_to_s3(al_teams, PREDICTIONS_BUCKET, f'end-of-year-standings-predictions_{today_str}.csv')

    # Orioles games back from 3rd wild card
    # In current MLB format: 3 division winners + 3 wild cards = top 6 in each league
    # Wild card 3 = 6th place in AL by projected wins
    al_sorted = al_teams.sort_values('median_wins', ascending=False)
    if len(al_sorted) >= 6:
        wc3_wins = al_sorted.iloc[5]['median_wins']
        orioles_row = al_sorted[al_sorted['team'] == 'BAL']
        if not orioles_row.empty:
            orioles_wins = orioles_row.iloc[0]['median_wins']
            gb_from_wc3 = wc3_wins - orioles_wins
            gb_df = pd.DataFrame([{'team': 'BAL', 'games_back_from_third_wild_card': gb_from_wc3}])
            write_csv_to_s3(gb_df, PREDICTIONS_BUCKET, f'orioles_games_back_prediction_{today_str}.csv')

    # Write latest.json files for Angular frontend
    standings_json = al_sorted[['team', 'median_wins', 'avg_wins', 'std_dev', 'p10', 'p90']].to_dict('records')
    write_json_to_s3({
        'updated': datetime.utcnow().isoformat(),
        'standings': standings_json,
    }, PREDICTIONS_BUCKET, 'standings-latest.json')

    projections_json = df_summary[['team', 'median_wins', 'avg_wins', 'std_dev', 'p10', 'p25', 'p75', 'p90']].to_dict('records')
    write_json_to_s3({
        'updated': datetime.utcnow().isoformat(),
        'injury_adjusted': injury_adjusted,
        'projections': projections_json,
    }, PREDICTIONS_BUCKET, 'projections-latest.json')


def load_preseason_elo():
    """Load preseason ELO baseline from S3 for regression."""
    try:
        data = read_json_from_s3(ELO_BUCKET, f'preseason-elo-{SEASON_YEAR}.json')
        logger.info(f"Loaded preseason ELO baseline for {len(data)} teams")
        return data
    except Exception as e:
        logger.warning(f"Could not load preseason ELO baseline — skipping regression: {e}")
        return None


FADE_GAMES = 100  # Games until preseason WAR influence fully fades (backtest-optimal)


def regress_elo_to_preseason(current_elo, preseason_elo, schedule_df):
    """
    Blend current ELO with preseason ELO based on games played.

    Early season: heavily weight preseason (small sample, don't overreact).
    Late season: heavily weight current ELO (season speaks for itself).

    Formula: sim_elo = pct * current + (1 - pct) * preseason
    where pct = min(games_played / FADE_GAMES, 1.0)
    """
    completed = schedule_df.dropna(subset=['homeScore', 'awayScore'])
    games_played = defaultdict(int)
    for _, row in completed.iterrows():
        games_played[row['homeTeam']] += 1
        games_played[row['awayTeam']] += 1

    regressed = {}
    for team, elo in current_elo.items():
        pre = preseason_elo.get(team)
        if pre is None:
            regressed[team] = elo
            continue
        gp = games_played.get(team, 0)
        pct = min(gp / float(FADE_GAMES), 1.0)
        regressed[team] = round(pct * elo + (1 - pct) * pre, 2)

    total_gp = sum(games_played.values()) // 2  # each game counted twice
    logger.info(f"ELO regression: {total_gp} games played, blending current/preseason (fade={FADE_GAMES})")
    if 'BAL' in regressed:
        bal_gp = games_played.get('BAL', 0)
        logger.info(
            f"  BAL: current={current_elo.get('BAL', 0):.1f}, "
            f"preseason={preseason_elo.get('BAL', 0):.1f}, "
            f"regressed={regressed['BAL']:.1f} ({bal_gp} GP, {min(bal_gp/FADE_GAMES, 1.0):.0%} weight)"
        )
    return regressed


def load_injury_adjustments():
    """Load injury ELO adjustments from S3 (written by mlb-elo-compute)."""
    try:
        data = read_json_from_s3(ELO_BUCKET, 'injury-adjustments-latest.json')
        adj = {t['team']: t['elo_adjustment'] for t in data['adjustments']}
        total_teams = sum(1 for v in adj.values() if v != 0)
        logger.info(f"Loaded injury adjustments for {total_teams} teams with IL impact")
        return adj
    except Exception as e:
        logger.warning(f"Could not load injury data — projecting without injuries: {e}")
        return {}


def lambda_handler(event=None, context=None):
    elo_ratings = fetch_latest_elo_ratings()
    logger.info(f"Loaded ELO ratings for {len(elo_ratings)} teams")

    schedule_df = read_csv_from_s3(SCHEDULE_BUCKET, SCHEDULE_KEY)
    schedule_df['date'] = pd.to_datetime(schedule_df['date'])
    logger.info(f"Loaded schedule with {len(schedule_df)} games")

    # Load FIP data (written by mlb-elo-compute earlier in the pipeline)
    fip_dict, lg_fip = load_fip_data()

    # Load injury adjustments and apply to effective ELO
    injury_adj = load_injury_adjustments()
    adjusted_elo = {
        team: elo + injury_adj.get(team, 0)
        for team, elo in elo_ratings.items()
    }

    # Regress ELO toward preseason baseline (reduces early-season volatility)
    preseason_elo = load_preseason_elo()
    if preseason_elo:
        adjusted_elo = regress_elo_to_preseason(adjusted_elo, preseason_elo, schedule_df)

    generate_next_game_predictions(schedule_df, adjusted_elo, fip_dict, lg_fip)
    df_summary, df_sim = simulate_season(schedule_df, adjusted_elo, fip_dict, lg_fip)
    compute_standings_and_gb(df_summary, injury_adjusted=bool(injury_adj))

    # Compute playoff odds from simulation matrix
    teams = sorted(set(schedule_df['homeTeam']) | set(schedule_df['awayTeam']))
    compute_playoff_odds(df_sim, teams, injury_adjusted=bool(injury_adj))

    return {
        'statusCode': 200,
        'body': json.dumps(f"Simulated {SIM_COUNT} seasons for {len(elo_ratings)} teams"),
    }
