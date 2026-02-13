"""
mlb-schedule-sync — Fetch full season schedule from MLB Stats API and save to S3.

Replaces: mlb-remaining-2025-schedule

Changes from original:
- Uses shared config (no hardcoded season/bucket)
- Uses bulk schedule endpoint with hydrations to avoid 2400+ individual API calls
- Only falls back to individual game feed for pitcher data when needed
- No runtime pip install (dependencies from Lambda Layer)
"""
import csv
import io
import json
import logging
import requests
from mlb_common.config import (
    SEASON_YEAR, SCHEDULE_BUCKET, SCHEDULE_KEY,
    MLB_SCHEDULE_URL, MLB_GAME_FEED_URL,
)
from mlb_common.aws_helpers import s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = requests.Session()

CSV_FIELDS = [
    'date', 'gamePk', 'status', 'homeTeam', 'awayTeam',
    'homeScore', 'awayScore', 'venueName',
    'homeStartingPitcherId', 'homeStartingPitcherName',
    'awayStartingPitcherId', 'awayStartingPitcherName',
]


def fetch_full_schedule():
    """Fetch the entire regular season schedule with scores and team info hydrated."""
    params = {
        'sportId': 1,
        'season': SEASON_YEAR,
        'gameTypes': 'R',
        'hydrate': 'decisions,linescore,team,probablePitcher',
        'limit': 5000,
    }
    resp = session.get(MLB_SCHEDULE_URL, params=params)
    resp.raise_for_status()
    return resp.json().get('dates', [])


def backfill_score(game_pk):
    """Fetch scores from the live game feed for games with missing score data."""
    try:
        url = MLB_GAME_FEED_URL.format(gamePk=game_pk)
        r = session.get(url)
        r.raise_for_status()
        teams = r.json().get('liveData', {}).get('linescore', {}).get('teams', {})
        return teams.get('home', {}).get('runs'), teams.get('away', {}).get('runs')
    except Exception as e:
        logger.warning(f"Backfill failed for {game_pk}: {e}")
        return None, None


def extract_game_row(game, date_str):
    """Extract a flat CSV row from a hydrated game object."""
    status = game.get('status', {}).get('abstractGameState')
    home_team = game['teams']['home']['team'].get('abbreviation')
    away_team = game['teams']['away']['team'].get('abbreviation')
    home_score = game['teams']['home'].get('score')
    away_score = game['teams']['away'].get('score')

    # Backfill missing scores for completed games
    if status == 'Final' and (home_score is None or away_score is None):
        bhs, bas = backfill_score(game['gamePk'])
        home_score = bhs if bhs is not None else home_score
        away_score = bas if bas is not None else away_score

    if status == 'Final' and (home_score is None or away_score is None):
        logger.warning(f"Skipping final game {game['gamePk']} on {date_str} — missing score")
        return None

    # Extract pitcher info from hydrated probablePitcher data
    probables = game.get('teams', {})
    home_pitcher = probables.get('home', {}).get('probablePitcher', {})
    away_pitcher = probables.get('away', {}).get('probablePitcher', {})

    venue = game.get('venue', {}).get('name', '')

    return [
        date_str,
        str(game['gamePk']),
        status,
        home_team,
        away_team,
        home_score if home_score is not None else '',
        away_score if away_score is not None else '',
        venue,
        home_pitcher.get('id', ''),
        home_pitcher.get('fullName', ''),
        away_pitcher.get('id', ''),
        away_pitcher.get('fullName', ''),
    ]


def lambda_handler(event, context):
    try:
        schedule_blocks = fetch_full_schedule()
        total_days = len(schedule_blocks)
        logger.info(f"Fetched {total_days} days for {SEASON_YEAR}")

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_FIELDS)

        seen = set()
        game_count = 0

        for block in schedule_blocks:
            date_str = block.get('date')
            for game in block.get('games', []):
                if game.get('gameType') != 'R':
                    continue
                pk = str(game.get('gamePk'))
                if pk in seen:
                    continue
                seen.add(pk)

                row = extract_game_row(game, date_str)
                if row:
                    writer.writerow(row)
                    game_count += 1

        s3.put_object(Bucket=SCHEDULE_BUCKET, Key=SCHEDULE_KEY, Body=buffer.getvalue())
        logger.info(f"Saved {game_count} games to s3://{SCHEDULE_BUCKET}/{SCHEDULE_KEY}")

        return {
            'statusCode': 200,
            'body': json.dumps({'days': total_days, 'games': game_count}),
        }

    except Exception as e:
        logger.error(f"Error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
