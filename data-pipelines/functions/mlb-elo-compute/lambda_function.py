"""
mlb-elo-compute — Single canonical ELO rating engine.

Replaces: mlb-daily-elo-compute + mlb-elo-ratings-calculator

Canonical formula (from mlb-daily-elo-compute):
- K = 20, HFA = 55
- MOV = log(|score_diff| + 1) * (2.2 / (0.001 * |elo_diff| + 2.2))

After ELO updates, fetches current-season pitcher FIP data from the
MLB Stats API and writes it to S3 for downstream use by the projections
Lambda (FIP-adjusted win probabilities + probability shrinkage).
"""
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from mlb_common.config import (
    ELO_BUCKET, ELO_PRIOR_SEASON_KEY, ELO_CURRENT_SEASON_KEY,
    SCHEDULE_BUCKET, SCHEDULE_KEY, ELO_TABLE, ELO_HFA,
    SEASON_YEAR, FIP_KEY,
)
from mlb_common.aws_helpers import (
    read_csv_from_s3, append_csv_to_s3, write_csv_to_s3,
    write_json_to_s3, dynamo_put_item,
)
from mlb_common.team_codes import SCHEDULE_TO_ELO_MAP
from mlb_common.elo import expected_score, margin_of_victory_mult, update_elo
from mlb_common.fip import fetch_pitcher_fip

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def standardize_team(code):
    """Convert end-of-season ELO file codes to canonical schedule format."""
    return SCHEDULE_TO_ELO_MAP.get(code, code)


def lambda_handler(event, context):
    today = datetime.utcnow().date()
    yesterday = (today - timedelta(days=1)).isoformat()

    # Load end-of-prior-season ELO baseline
    elo_baseline_df = read_csv_from_s3(ELO_BUCKET, ELO_PRIOR_SEASON_KEY)
    elo_baseline_df['team'] = elo_baseline_df['team'].apply(standardize_team)

    # Load schedule
    schedule_df = read_csv_from_s3(SCHEDULE_BUCKET, SCHEDULE_KEY)
    schedule_df['homeTeam'] = schedule_df['homeTeam'].apply(standardize_team)
    schedule_df['awayTeam'] = schedule_df['awayTeam'].apply(standardize_team)

    # Initialize team ELO from baseline
    team_elo = dict(zip(elo_baseline_df['team'], elo_baseline_df['elo']))

    # Override with most recent values from current season if available
    try:
        current_df = read_csv_from_s3(ELO_BUCKET, ELO_CURRENT_SEASON_KEY)
        latest = current_df.sort_values('date').groupby('homeTeam')['homeElo_post'].last().to_dict()
        latest.update(current_df.sort_values('date').groupby('awayTeam')['awayElo_post'].last().to_dict())
        team_elo.update(latest)
    except Exception:
        logger.info("No existing current-season ELO file — starting from baseline")

    # Filter to yesterday's completed games
    games = schedule_df[schedule_df['date'] == yesterday].dropna(subset=['homeScore', 'awayScore'])

    elo_rows = []

    for _, row in games.iterrows():
        home, away = row['homeTeam'], row['awayTeam']
        home_score, away_score = row['homeScore'], row['awayScore']
        game_pk = row['gamePk']

        if home not in team_elo or away not in team_elo:
            logger.warning(f"Missing ELO for {home} or {away} — skipping game {game_pk}")
            continue

        elo_home = team_elo[home]
        elo_away = team_elo[away]

        prob_home = expected_score(elo_home, elo_away, hfa=ELO_HFA)
        result_home = 1 if home_score > away_score else 0

        score_diff = abs(home_score - away_score)
        mov = margin_of_victory_mult(score_diff, elo_home - elo_away)
        elo_shift = update_elo(elo_home, prob_home, result_home, mov_mult=mov)

        team_elo[home] = elo_home + elo_shift
        team_elo[away] = elo_away - elo_shift

        # Update DynamoDB per team
        for team, new_elo in [(home, team_elo[home]), (away, team_elo[away])]:
            dynamo_put_item(ELO_TABLE, {
                'team': team,
                'elo': round(new_elo, 2),
                'last_updated': datetime.utcnow().isoformat(),
                'last_gamePk': int(game_pk),
            })

        elo_rows.append({
            'date': yesterday,
            'gamePk': int(game_pk),
            'homeTeam': home,
            'awayTeam': away,
            'homeScore': int(home_score),
            'awayScore': int(away_score),
            'homeElo_pre': round(elo_home, 2),
            'awayElo_pre': round(elo_away, 2),
            'homeElo_post': round(team_elo[home], 2),
            'awayElo_post': round(team_elo[away], 2),
            'elo_shift': round(elo_shift, 2),
        })

    if elo_rows:
        output_df = pd.DataFrame(elo_rows)
        append_csv_to_s3(output_df, ELO_BUCKET, ELO_CURRENT_SEASON_KEY)
        logger.info(f"Updated ELO for {len(elo_rows)} games on {yesterday}")
    else:
        logger.info(f"No completed games found for {yesterday}")

    # Write latest.json for Angular frontend
    elo_latest = [
        {'team': team, 'elo': round(elo, 2)}
        for team, elo in sorted(team_elo.items(), key=lambda x: x[1], reverse=True)
    ]
    write_json_to_s3({
        'updated': datetime.utcnow().isoformat(),
        'ratings': elo_latest,
    }, ELO_BUCKET, 'elo-latest.json')

    # Fetch pitcher FIP data and write to S3 for downstream projections Lambda
    try:
        fip_dict, lg_fip = fetch_pitcher_fip(SEASON_YEAR)
        fip_rows = [
            {'pitcher_id': pid, 'name': info['name'], 'fip': info['fip'], 'ip': info['ip']}
            for pid, info in fip_dict.items()
        ]
        fip_df = pd.DataFrame(fip_rows)
        write_csv_to_s3(fip_df, ELO_BUCKET, FIP_KEY)
        write_json_to_s3({
            'updated': datetime.utcnow().isoformat(),
            'lg_fip': round(lg_fip, 3),
            'pitcher_count': len(fip_dict),
        }, ELO_BUCKET, 'fip-latest.json')
        logger.info(f"Wrote FIP data for {len(fip_dict)} pitchers to S3")
    except Exception as e:
        logger.error(f"FIP fetch failed (non-fatal): {e}")

    # Fetch injury IL data and compute ELO adjustments for downstream projections
    try:
        from mlb_common.injury import fetch_injury_elo_adjustments
        injury_data = fetch_injury_elo_adjustments(SEASON_YEAR)
        write_json_to_s3(injury_data, ELO_BUCKET, 'injury-adjustments-latest.json')
        logger.info(f"Wrote injury adjustments for {len(injury_data['adjustments'])} teams")
    except Exception as e:
        logger.warning(f"Injury adjustment failed (non-fatal): {e}")

    return {
        'statusCode': 200,
        'body': json.dumps(f"Processed {len(elo_rows)} games for {yesterday}"),
    }
