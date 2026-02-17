"""
Central configuration for the MLB data pipeline.
All values read from environment variables with sensible defaults.
"""
import os
from datetime import datetime

# Season
SEASON_YEAR = int(os.getenv('SEASON_YEAR', str(datetime.utcnow().year)))
PRIOR_SEASON_YEAR = SEASON_YEAR - 1

# S3 buckets
SCHEDULE_BUCKET = os.getenv('SCHEDULE_BUCKET', f'mlb-schedule-{SEASON_YEAR}')
PREDICTIONS_BUCKET = os.getenv('PREDICTIONS_BUCKET', f'mlb-predictions-{SEASON_YEAR}')
ELO_BUCKET = os.getenv('ELO_BUCKET', 'mlb-elo-ratings-output')
LOGOS_BUCKET = os.getenv('LOGOS_BUCKET', 'mlb-logos-for-visuals')
PLAYER_STATS_BUCKET = os.getenv('PLAYER_STATS_BUCKET', 'mlb-player-stats-retrosheet')

# S3 keys
SCHEDULE_KEY = os.getenv('SCHEDULE_KEY', f'schedule_{SEASON_YEAR}_full.csv')
ELO_PRIOR_SEASON_KEY = os.getenv('ELO_PRIOR_SEASON_KEY', f'elo_rating_end_of_{PRIOR_SEASON_YEAR}.csv')
ELO_CURRENT_SEASON_KEY = os.getenv('ELO_CURRENT_SEASON_KEY', f'elo-ratings-{SEASON_YEAR}.csv')

# DynamoDB tables
ELO_TABLE = os.getenv('ELO_TABLE', 'mlb-elo-team-ratings')
GAMES_TABLE = os.getenv('GAMES_TABLE', 'Orioles-Games')
GAMES_BACK_TABLE = os.getenv('GAMES_BACK_TABLE', 'Orioles-Games_Back')

# ELO parameters
ELO_K = int(os.getenv('ELO_K', '20'))
ELO_HFA = int(os.getenv('ELO_HFA', '55'))
ELO_INIT = int(os.getenv('ELO_INIT', '1500'))
MOV_MULTIPLIER = float(os.getenv('MOV_MULTIPLIER', '2.2'))

# Enhanced model parameters (FIP adjustment + probability shrinkage)
FIP_WEIGHT = int(os.getenv('FIP_WEIGHT', '50'))
PROB_SHRINKAGE = float(os.getenv('PROB_SHRINKAGE', '0.16'))

# S3 key for FIP data
FIP_KEY = os.getenv('FIP_KEY', f'pitcher_fip_{SEASON_YEAR}.csv')

# Injury adjustment
INJURY_WAR_TO_ELO = float(os.getenv('INJURY_WAR_TO_ELO', '5.5'))

# Simulation parameters
SIM_COUNT = int(os.getenv('SIM_COUNT', '10000'))

# Orioles
ORIOLES_TEAM_ID = 110
AL_LEAGUE_ID = 103

# MLB Stats API
MLB_SCHEDULE_URL = 'https://statsapi.mlb.com/api/v1/schedule'
MLB_STANDINGS_URL = 'https://statsapi.mlb.com/api/v1/standings'
MLB_GAME_FEED_URL = 'https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live'
MLB_PITCHING_STATS_URL = 'https://statsapi.mlb.com/api/v1/stats'
