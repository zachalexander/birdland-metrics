"""
mlb-game-results — Fetch daily Orioles game results and save to DynamoDB.

Replaces: mlb-stats-api-game-data

Changes from original:
- Single build_game_item() helper eliminates 6x code duplication (~80 lines vs ~260)
- Unified handling for single games, doubleheaders, today, and yesterday
- Uses put_item consistently (update_item was redundant with same fields)
- No runtime pip install (MLB-StatsAPI from Lambda Layer)
"""
import json
import logging
import statsapi
from datetime import date, timedelta
from mlb_common.config import ORIOLES_TEAM_ID, GAMES_TABLE
from mlb_common.aws_helpers import dynamo_put_item

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def build_game_item(game):
    """
    Build a DynamoDB item from a statsapi.schedule() game dict.

    For completed games, includes scores and pitcher info.
    For scheduled/in-progress games, includes only basic info.
    """
    item = {
        'id': str(game['game_id']),
        'home_team': game['home_name'],
        'away_team': game['away_name'],
        'date': game['game_date'],
        'datetime': game['game_datetime'],
        'venue': game['venue_name'],
        'status': game['status'],
    }

    if game['status'] == 'Final':
        item.update({
            'winning_team': game.get('winning_team', ''),
            'losing_team': game.get('losing_team', ''),
            'away_score': game.get('away_score', 0),
            'home_score': game.get('home_score', 0),
            'winning_pitcher': game.get('winning_pitcher', ''),
            'losing_pitcher': game.get('losing_pitcher', ''),
            'save_pitcher': game.get('save_pitcher', ''),
        })

    return item


def lambda_handler(event, context):
    today = date.today()
    yesterday = today - timedelta(days=1)
    dates = [yesterday, today]
    games_saved = 0

    for game_date in dates:
        formatted = game_date.strftime('%m/%d/%Y')
        label = 'yesterday' if game_date == yesterday else 'today'

        try:
            games = statsapi.schedule(start_date=formatted, end_date=formatted, team=ORIOLES_TEAM_ID)
        except Exception as e:
            logger.error(f"Failed to fetch schedule for {label} ({formatted}): {e}")
            continue

        if not games:
            logger.info(f"No Orioles games {label} ({formatted})")
            continue

        for game in games:
            item = build_game_item(game)
            try:
                dynamo_put_item(GAMES_TABLE, item)
                games_saved += 1
                logger.info(f"Saved game {item['id']} ({label}): {item['away_team']} @ {item['home_team']} — {item['status']}")
            except Exception as e:
                logger.error(f"Failed to save game {item['id']}: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps(f'Saved {games_saved} game(s)'),
    }
