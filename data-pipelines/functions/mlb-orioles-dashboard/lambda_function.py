"""
mlb-orioles-dashboard — Orioles games back + projections → DynamoDB + latest.json.

Replaces: mlb-daily-orioles-games-back

Changes from original:
- Uses shared config for bucket names and table name
- Removed unnecessary day-by-day iteration (only processes today)
- Writes games-back-latest.json and recent-games-latest.json for Angular frontend
- No runtime pip install (dependencies from Lambda Layer)
"""
import json
import logging
import requests
import pandas as pd
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from mlb_common.config import (
    PREDICTIONS_BUCKET, GAMES_BACK_TABLE, GAMES_TABLE,
    ORIOLES_TEAM_ID, AL_LEAGUE_ID, MLB_STANDINGS_URL, SEASON_YEAR,
)
from mlb_common.aws_helpers import (
    s3, dynamo_put_item, dynamo_scan, write_json_to_s3,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_orioles_projections(current_date):
    """Fetch Orioles projection stats from the daily summary CSV in S3."""
    key = f"season_win_projection_summary_{current_date.isoformat()}.csv"
    try:
        response = s3.get_object(Bucket=PREDICTIONS_BUCKET, Key=key)
        df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
        row = df[df['team'] == 'BAL'].iloc[0]
        return {
            'median_wins': Decimal(str(row['median_wins'])),
            'std_dev': Decimal(str(row['std_dev'])),
            'p10': Decimal(str(row['p10'])),
            'p25': Decimal(str(row['p25'])),
            'p75': Decimal(str(row['p75'])),
            'p90': Decimal(str(row['p90'])),
        }
    except Exception as e:
        logger.warning(f"Could not fetch projections for {current_date}: {e}")
        return None


def get_games_back_prediction(current_date):
    """Fetch projected games back from WC3 from S3."""
    key = f"orioles_games_back_prediction_{current_date.isoformat()}.csv"
    try:
        response = s3.get_object(Bucket=PREDICTIONS_BUCKET, Key=key)
        df = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
        return Decimal(str(df['games_back_from_third_wild_card'].iloc[0]))
    except Exception as e:
        logger.warning(f"Could not fetch GB prediction for {current_date}: {e}")
        return None


def fetch_actual_games_back(current_date):
    """Fetch actual wildcard and division games back from MLB Standings API."""
    resp = requests.get(MLB_STANDINGS_URL, params={
        'leagueId': AL_LEAGUE_ID,
        'season': current_date.year,
        'date': current_date.isoformat(),
        'sportId': 1,
    })
    resp.raise_for_status()

    for record in resp.json().get('records', []):
        for team_rec in record['teamRecords']:
            if team_rec['team']['id'] == ORIOLES_TEAM_ID:
                wc_gb = team_rec['wildCardGamesBack']
                div_gb = team_rec['gamesBack']
                return {
                    'wildcard_gb': Decimal('0') if wc_gb == '-' else Decimal(str(wc_gb)),
                    'division_gb': Decimal('0') if div_gb == '-' else Decimal(str(div_gb)),
                }
    return None


def build_recent_games_json():
    """Build recent-games-latest.json from the last 10 completed Orioles games in DynamoDB.
    Falls back to spring training games from the MLB Stats API if no regular season games exist."""
    items = dynamo_scan(GAMES_TABLE)
    completed = [
        g for g in items
        if g.get('status') == 'Final'
        and g.get('date', '').startswith(str(SEASON_YEAR))
    ]
    completed.sort(key=lambda g: g.get('datetime', ''), reverse=True)
    recent = completed[:10]

    if recent:
        return 'R', [{
            'id': g.get('id'),
            'date': g.get('date'),
            'home_team': g.get('home_team'),
            'away_team': g.get('away_team'),
            'home_score': int(g.get('home_score', 0)),
            'away_score': int(g.get('away_score', 0)),
            'winning_team': g.get('winning_team', ''),
            'losing_team': g.get('losing_team', ''),
            'winning_pitcher': g.get('winning_pitcher', ''),
            'losing_pitcher': g.get('losing_pitcher', ''),
            'save_pitcher': g.get('save_pitcher', ''),
            'venue': g.get('venue', ''),
        } for g in recent]

    # No current-season regular season games — try spring training
    logger.info("No regular season games found, fetching spring training")
    game_type, spring_games = fetch_spring_training_games()
    if spring_games:
        return game_type, spring_games

    # No spring training games yet — fall back to most recent games from any season
    logger.info("No spring training games found, falling back to last completed games")
    all_completed = [g for g in items if g.get('status') == 'Final']
    all_completed.sort(key=lambda g: g.get('datetime', ''), reverse=True)
    fallback = all_completed[:10]
    if fallback:
        return 'R', [{
            'id': g.get('id'),
            'date': g.get('date'),
            'home_team': g.get('home_team'),
            'away_team': g.get('away_team'),
            'home_score': int(g.get('home_score', 0)),
            'away_score': int(g.get('away_score', 0)),
            'winning_team': g.get('winning_team', ''),
            'losing_team': g.get('losing_team', ''),
            'winning_pitcher': g.get('winning_pitcher', ''),
            'losing_pitcher': g.get('losing_pitcher', ''),
            'save_pitcher': g.get('save_pitcher', ''),
            'venue': g.get('venue', ''),
        } for g in fallback]

    return 'S', []


def fetch_spring_training_games():
    """Fetch recent completed Orioles spring training games from the MLB Stats API."""
    try:
        resp = requests.get('https://statsapi.mlb.com/api/v1/schedule', params={
            'sportId': 1,
            'teamId': ORIOLES_TEAM_ID,
            'gameType': 'S',
            'season': SEASON_YEAR,
            'hydrate': 'linescore,decisions',
        }, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Could not fetch spring training schedule: {e}")
        return 'S', []

    games = []
    for d in resp.json().get('dates', []):
        for g in d.get('games', []):
            if g.get('status', {}).get('abstractGameState') != 'Final':
                continue

            home = g.get('teams', {}).get('home', {})
            away = g.get('teams', {}).get('away', {})
            home_name = home.get('team', {}).get('name', '')
            away_name = away.get('team', {}).get('name', '')
            home_won = home.get('isWinner', False)

            decisions = g.get('decisions', {})
            winner_p = decisions.get('winner', {}).get('fullName', '')
            loser_p = decisions.get('loser', {}).get('fullName', '')
            save_p = decisions.get('save', {}).get('fullName', '')

            games.append({
                'id': str(g.get('gamePk', '')),
                'date': g.get('officialDate', ''),
                'home_team': home_name,
                'away_team': away_name,
                'home_score': int(home.get('score', 0)),
                'away_score': int(away.get('score', 0)),
                'winning_team': home_name if home_won else away_name,
                'losing_team': away_name if home_won else home_name,
                'winning_pitcher': winner_p,
                'losing_pitcher': loser_p,
                'save_pitcher': save_p,
                'venue': g.get('venue', {}).get('name', ''),
            })

    # Most recent 10, sorted by date descending
    games.sort(key=lambda x: x['date'], reverse=True)
    logger.info(f"Found {len(games)} completed spring training games")
    return 'S', games[:10]


def lambda_handler(event, context):
    today = date.today()
    logger.info(f"Processing Orioles dashboard for {today}")

    # Fetch actual standings (returns None in offseason)
    actual_gb = fetch_actual_games_back(today)

    if actual_gb:
        # Regular season — full dashboard update
        projections = get_orioles_projections(today)
        gb_prediction = get_games_back_prediction(today)

        item = {
            'id': f'mlb-day-{today.isoformat()}',
            'date': today.isoformat(),
            **actual_gb,
        }
        if projections:
            item.update(projections)
        if gb_prediction is not None:
            item['proj_gb_from_wc3'] = gb_prediction

        dynamo_put_item(GAMES_BACK_TABLE, item)
        logger.info(f"Saved games back record for {today}")

        games_back_json = {
            'updated': datetime.utcnow().isoformat(),
            'date': today.isoformat(),
            'wildcard_gb': float(actual_gb['wildcard_gb']),
            'division_gb': float(actual_gb['division_gb']),
        }
        if projections:
            games_back_json['projections'] = {k: float(v) for k, v in projections.items()}
        if gb_prediction is not None:
            games_back_json['proj_gb_from_wc3'] = float(gb_prediction)

        write_json_to_s3(games_back_json, PREDICTIONS_BUCKET, 'games-back-latest.json')
    else:
        logger.info("No standings available (offseason) — skipping games-back update")

    # Write recent-games-latest.json (falls back to spring training in offseason)
    game_type, recent_games = build_recent_games_json()
    write_json_to_s3({
        'updated': datetime.utcnow().isoformat(),
        'game_type': game_type,
        'games': recent_games,
    }, PREDICTIONS_BUCKET, 'recent-games-latest.json')

    return {
        'statusCode': 200,
        'body': json.dumps(f'Dashboard updated for {today}'),
    }
