"""
mlb-core-benchmarks — Fetches FanGraphs batting + pitching stats via the
FanGraphs JSON API, evaluates pass/fail benchmarks for core Orioles players,
and writes JSON to S3.

Uses the FanGraphs leaderboard API directly (no pybaseball dependency)
so this Lambda only needs the mlb-pipeline-common layer.

Runs daily as part of the mlb-daily-pipeline Step Function.
"""
import json
import logging
import math
from datetime import datetime, timezone

import requests
from mlb_common.config import PLAYER_STATS_BUCKET, SEASON_YEAR
from mlb_common.aws_helpers import write_json_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# FanGraphs API helpers
# ---------------------------------------------------------------------------

FG_API_URL = "https://www.fangraphs.com/api/leaders/major-league/data"
BAL_TEAM_ID = "2"


def fetch_fangraphs(stats_type, season, team=BAL_TEAM_ID, qual=0):
    """Fetch player stats from the FanGraphs JSON API.

    Args:
        stats_type: 'bat' for batters, 'pit' for pitchers.
        season: MLB season year.
        team: FanGraphs team ID (2 = BAL). Use '' for all teams.
        qual: Minimum qualifier (0 = no minimum).

    Returns:
        List of player dicts with all available stats.
    """
    params = {
        "pos": "all",
        "stats": stats_type,
        "lg": "all",
        "qual": str(qual),
        "season": str(season),
        "season1": str(season),
        "month": "0",
        "team": team,
        "pageitems": "500",
        "pagenum": "1",
        "ind": "0",
        "type": "c,6,34,35,36,37,38,39,40,41,42,43,44,45,310,311,312,313",
    }
    resp = requests.get(FG_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", [])
    logger.info(f"FanGraphs {stats_type}: {len(rows)} rows for team={team}")
    return rows


# ---------------------------------------------------------------------------
# Player definitions and benchmarks
# ---------------------------------------------------------------------------

BATTERS = [
    {
        "name": "Gunnar Henderson",
        "playerId": "683002",
        "position": "SS",
        "benchmarks": [
            {"key": "barrel_pct", "label": "Barrel% >= 10%", "description": "Returned to 2024 power form", "target": 10.0, "direction": "gte", "category": "power", "stat": "Barrel%"},
            {"key": "wrc_plus", "label": "wRC+ >= 140", "description": "Superstar-level production", "target": 140, "direction": "gte", "category": "production", "stat": "wRC+"},
            {"key": "hr_pace", "label": "HR pace >= 30", "description": "On pace for 30+ home runs", "target": 30, "direction": "gte", "category": "power", "stat": "hr_pace"},
        ],
    },
    {
        "name": "Adley Rutschman",
        "playerId": "668939",
        "position": "C",
        "benchmarks": [
            {"key": "obp", "label": "OBP >= .340", "description": "Elite on-base ability", "target": .340, "direction": "gte", "category": "discipline", "stat": "OBP"},
            {"key": "bb_pct", "label": "BB% >= 10%", "description": "Above-average walk rate", "target": 10.0, "direction": "gte", "category": "discipline", "stat": "BB%"},
            {"key": "wrc_plus", "label": "wRC+ >= 115", "description": "Above-average offensive catcher", "target": 115, "direction": "gte", "category": "production", "stat": "wRC+"},
        ],
    },
    {
        "name": "Jordan Westburg",
        "playerId": "682614",
        "position": "2B/3B",
        "benchmarks": [
            {"key": "ops", "label": "OPS >= .800", "description": "Solid middle-of-the-order bat", "target": .800, "direction": "gte", "category": "production", "stat": "OPS"},
            {"key": "iso", "label": "ISO >= .180", "description": "Sustained power production", "target": .180, "direction": "gte", "category": "power", "stat": "ISO"},
            {"key": "games_pace", "label": "Games pace >= 140", "description": "Full-season health", "target": 140, "direction": "gte", "category": "health", "stat": "games_pace"},
        ],
    },
    {
        "name": "Colton Cowser",
        "playerId": "681297",
        "position": "OF",
        "benchmarks": [
            {"key": "k_pct", "label": "K% <= 22%", "description": "Improved contact ability", "target": 22.0, "direction": "lte", "category": "contact", "stat": "K%"},
            {"key": "hard_pct", "label": "Hard% >= 38%", "description": "Quality of contact", "target": 38.0, "direction": "gte", "category": "power", "stat": "Hard%"},
            {"key": "wrc_plus", "label": "wRC+ >= 110", "description": "Above-average regular", "target": 110, "direction": "gte", "category": "production", "stat": "wRC+"},
        ],
    },
    {
        "name": "Pete Alonso",
        "playerId": "624413",
        "position": "1B",
        "benchmarks": [
            {"key": "hr_pace", "label": "HR pace >= 30", "description": "On pace for 30+ home runs", "target": 30, "direction": "gte", "category": "power", "stat": "hr_pace"},
            {"key": "exit_velo", "label": "Exit velo >= 91 mph", "description": "No physical decline", "target": 91.0, "direction": "gte", "category": "power", "stat": "EV"},
            {"key": "slg", "label": "SLG >= .470", "description": "Power production in the lineup", "target": .470, "direction": "gte", "category": "power", "stat": "SLG"},
        ],
    },
    {
        "name": "Jackson Holliday",
        "playerId": "696137",
        "position": "2B",
        "benchmarks": [
            {"key": "k_pct", "label": "K% <= 25%", "description": "Improved contact from 2024", "target": 25.0, "direction": "lte", "category": "contact", "stat": "K%"},
            {"key": "bb_pct", "label": "BB% >= 9%", "description": "MLB-level plate discipline", "target": 9.0, "direction": "gte", "category": "discipline", "stat": "BB%"},
            {"key": "avg", "label": "AVG >= .250", "description": "Basic hitting threshold", "target": .250, "direction": "gte", "category": "contact", "stat": "AVG"},
        ],
    },
]

PITCHERS = [
    {
        "name": "Kyle Bradish",
        "playerId": "669062",
        "position": "SP",
        "benchmarks": [
            {"key": "era", "label": "ERA <= 3.50", "description": "Ace-level production", "target": 3.50, "direction": "lte", "category": "production", "stat": "ERA"},
            {"key": "k_per_9", "label": "K/9 >= 9.0", "description": "Swing-and-miss stuff intact", "target": 9.0, "direction": "gte", "category": "power", "stat": "K/9"},
            {"key": "ip_pace", "label": "IP pace >= 160", "description": "Full-season health", "target": 160, "direction": "gte", "category": "health", "stat": "ip_pace"},
        ],
    },
    {
        "name": "Trevor Rogers",
        "playerId": "669432",
        "position": "SP",
        "benchmarks": [
            {"key": "era", "label": "ERA <= 4.00", "description": "Solid starter threshold", "target": 4.00, "direction": "lte", "category": "production", "stat": "ERA"},
            {"key": "whip", "label": "WHIP <= 1.25", "description": "Limiting baserunners", "target": 1.25, "direction": "lte", "category": "contact", "stat": "WHIP"},
            {"key": "k_pct", "label": "K% >= 22%", "description": "Adequate strikeout rate", "target": 22.0, "direction": "gte", "category": "power", "stat": "K%"},
        ],
    },
    {
        "name": "Shane Baz",
        "playerId": "669358",
        "position": "SP",
        "benchmarks": [
            {"key": "era", "label": "ERA <= 3.75", "description": "Above-average starter", "target": 3.75, "direction": "lte", "category": "production", "stat": "ERA"},
            {"key": "fip", "label": "FIP <= 3.75", "description": "Skills match results", "target": 3.75, "direction": "lte", "category": "production", "stat": "FIP"},
            {"key": "ip_pace", "label": "IP pace >= 140", "description": "Health indicator", "target": 140, "direction": "gte", "category": "health", "stat": "ip_pace"},
        ],
    },
    {
        "name": "Ryan Helsley",
        "playerId": "664854",
        "position": "CL",
        "benchmarks": [
            {"key": "era", "label": "ERA <= 2.50", "description": "Dominant reliever threshold", "target": 2.50, "direction": "lte", "category": "production", "stat": "ERA"},
            {"key": "k_per_9", "label": "K/9 >= 11.0", "description": "Elite swing-and-miss", "target": 11.0, "direction": "gte", "category": "power", "stat": "K/9"},
            {"key": "sv_pace", "label": "SV pace >= 35", "description": "Closer workload", "target": 35, "direction": "gte", "category": "production", "stat": "sv_pace"},
        ],
    },
]

BULLPEN_DEF = {
    "name": "Team Bullpen",
    "playerId": "bullpen",
    "position": "RP",
    "benchmarks": [
        {"key": "era", "label": "ERA <= 3.75", "description": "Solid relief corps", "target": 3.75, "direction": "lte", "category": "production"},
        {"key": "k_per_9", "label": "K/9 >= 9.5", "description": "Swing-and-miss from the pen", "target": 9.5, "direction": "gte", "category": "power"},
        {"key": "whip", "label": "WHIP <= 1.25", "description": "Limiting baserunners in leverage", "target": 1.25, "direction": "lte", "category": "contact"},
    ],
}

ALL_PLAYERS = BATTERS + PITCHERS

S3_KEY = "benchmarks/core-benchmarks-latest.json"


# ---------------------------------------------------------------------------
# Stat helpers
# ---------------------------------------------------------------------------

def find_player(rows, name):
    """Find a player dict by name. Returns None if not found."""
    # FanGraphs API uses 'PlayerName' for the display name
    for row in rows:
        if row.get("PlayerName") == name:
            return row
    # Fuzzy: try last name
    last_name = name.split()[-1].lower()
    matches = [r for r in rows if last_name in r.get("PlayerName", "").lower()]
    if len(matches) == 1:
        logger.info(f"Fuzzy match: '{name}' -> '{matches[0]['PlayerName']}'")
        return matches[0]
    logger.warning(f"Player '{name}' not found in FanGraphs data")
    return None


def safe_float(val):
    """Convert a value to float, returning None for None/NaN."""
    if val is None:
        return None
    v = float(val)
    if math.isnan(v):
        return None
    return v


def get_stat_value(row, stat_key, team_games=None):
    """Extract a stat value from a player dict. Returns None if unavailable."""
    if row is None:
        return None

    if stat_key == "hr_pace":
        g = safe_float(row.get("G"))
        hr = safe_float(row.get("HR"))
        if g and g > 0 and hr is not None:
            return round((hr / g) * 162, 1)
        return None

    if stat_key == "games_pace":
        g = safe_float(row.get("G"))
        if g is not None and team_games and team_games > 0:
            return round((g / team_games) * 162, 0)
        return None

    if stat_key == "ip_pace":
        ip = safe_float(row.get("IP"))
        if ip is not None and team_games and team_games > 0:
            return round((ip / team_games) * 162, 1)
        return None

    if stat_key == "sv_pace":
        sv = safe_float(row.get("SV"))
        if sv is not None and team_games and team_games > 0:
            return round((sv / team_games) * 162, 1)
        return None

    val = safe_float(row.get(stat_key))
    if val is None:
        return None

    # FanGraphs API returns BB%, K%, Barrel%, Hard% as 0-1 decimals
    if stat_key in ("BB%", "K%", "Barrel%", "Hard%"):
        val = val * 100

    return val


PACE_RAW_KEYS = {
    "hr_pace": "HR",
    "ip_pace": "IP",
    "games_pace": "G",
    "sv_pace": "SV",
}


def get_raw_value(row, stat_key):
    """For pace-based keys, return the raw counting stat (e.g. actual HR, IP)."""
    raw_key = PACE_RAW_KEYS.get(stat_key)
    if raw_key is None or row is None:
        return None
    val = safe_float(row.get(raw_key))
    if val is None:
        return None
    return round(val, 1)


def evaluate_benchmark(current, target, direction):
    """Evaluate whether a benchmark is met."""
    if current is None:
        return False
    if direction == "gte":
        return current >= target
    if direction == "lte":
        return current <= target
    return False


def round_stat(current, stat_key):
    """Round a stat value appropriately."""
    if current is None:
        return None
    if stat_key in ("OBP", "SLG", "OPS", "AVG", "ISO"):
        return round(current, 3)
    if stat_key in ("BB%", "K%", "Barrel%", "Hard%"):
        return round(current, 1)
    if stat_key in ("EV", "ERA", "FIP", "WHIP", "K/9"):
        return round(current, 2)
    if stat_key in ("wRC+",):
        return round(current, 0)
    return round(current, 1)


def estimate_team_games(batting_rows):
    """Estimate how many games the team has played so far."""
    max_g = 0
    for player_def in BATTERS:
        row = find_player(batting_rows, player_def["name"])
        if row is not None:
            g = safe_float(row.get("G"))
            if g and g > max_g:
                max_g = int(g)
    return max_g if max_g > 0 else 162


def aggregate_bullpen(pitching_rows):
    """Aggregate bullpen stats for BAL relievers (pitchers with GS == 0)."""
    relievers = [p for p in pitching_rows if safe_float(p.get("GS")) == 0]

    if not relievers:
        logger.warning("No BAL relievers found for bullpen aggregation")
        return None

    total_ip = sum(safe_float(p.get("IP")) or 0 for p in relievers)
    total_er = sum(safe_float(p.get("ER")) or 0 for p in relievers)
    total_so = sum(safe_float(p.get("SO")) or 0 for p in relievers)
    total_bb = sum(safe_float(p.get("BB")) or 0 for p in relievers)
    total_h = sum(safe_float(p.get("H")) or 0 for p in relievers)

    if total_ip <= 0:
        return None

    logger.info(f"Bullpen: {len(relievers)} relievers, {total_ip:.1f} IP")

    return {
        "era": round(total_er / total_ip * 9, 2),
        "k_per_9": round(total_so / total_ip * 9, 2),
        "whip": round((total_bb + total_h) / total_ip, 2),
    }


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_benchmarks(season):
    """Build the full benchmarks JSON structure."""
    logger.info(f"Fetching FanGraphs batting stats for {season}...")
    batting_rows = fetch_fangraphs("bat", season, team=BAL_TEAM_ID, qual=0)

    logger.info(f"Fetching FanGraphs pitching stats for {season}...")
    pitching_rows = fetch_fangraphs("pit", season, team=BAL_TEAM_ID, qual=0)

    team_games = estimate_team_games(batting_rows)
    logger.info(f"Estimated team games played: {team_games}")

    pitcher_names = {p["name"] for p in PITCHERS}

    players_output = []
    for player_def in ALL_PLAYERS:
        rows = pitching_rows if player_def["name"] in pitcher_names else batting_rows
        row = find_player(rows, player_def["name"])
        benchmarks = []

        for bm in player_def["benchmarks"]:
            current = get_stat_value(row, bm["stat"], team_games)
            current = round_stat(current, bm.get("stat", bm["key"]))
            met = evaluate_benchmark(current, bm["target"], bm["direction"])
            actual = get_raw_value(row, bm["key"])

            entry = {
                "key": bm["key"],
                "label": bm["label"],
                "description": bm["description"],
                "target": bm["target"],
                "direction": bm["direction"],
                "current": current,
                "met": met,
                "category": bm["category"],
            }
            if actual is not None:
                entry["actual"] = actual
            benchmarks.append(entry)

        player_type = "pitcher" if player_def["name"] in pitcher_names else "batter"
        players_output.append({
            "name": player_def["name"],
            "playerId": player_def["playerId"],
            "position": player_def["position"],
            "type": player_type,
            "benchmarks": benchmarks,
        })

    # Bullpen aggregate
    bullpen_stats = aggregate_bullpen(pitching_rows)
    bullpen_benchmarks = []
    for bm in BULLPEN_DEF["benchmarks"]:
        current = bullpen_stats.get(bm["key"]) if bullpen_stats else None
        met = evaluate_benchmark(current, bm["target"], bm["direction"])
        bullpen_benchmarks.append({
            "key": bm["key"],
            "label": bm["label"],
            "description": bm["description"],
            "target": bm["target"],
            "direction": bm["direction"],
            "current": current,
            "met": met,
            "category": bm["category"],
        })
    players_output.append({
        "name": BULLPEN_DEF["name"],
        "playerId": BULLPEN_DEF["playerId"],
        "position": BULLPEN_DEF["position"],
        "type": "pitcher",
        "benchmarks": bullpen_benchmarks,
    })

    total_met = sum(1 for p in players_output for b in p["benchmarks"] if b["met"])
    total = sum(len(p["benchmarks"]) for p in players_output)
    logger.info(f"Results: {total_met} / {total} benchmarks met")

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "season": season,
        "players": players_output,
    }


def lambda_handler(event, context):
    season = SEASON_YEAR
    logger.info(f"Running core benchmarks for {season} season")

    data = build_benchmarks(season)

    write_json_to_s3(data, PLAYER_STATS_BUCKET, S3_KEY)
    logger.info(f"Uploaded to s3://{PLAYER_STATS_BUCKET}/{S3_KEY}")

    total_met = sum(1 for p in data["players"] for b in p["benchmarks"] if b["met"])
    total = sum(len(p["benchmarks"]) for p in data["players"])

    return {
        "statusCode": 200,
        "body": json.dumps({
            "season": season,
            "players": len(data["players"]),
            "benchmarks_met": f"{total_met}/{total}",
        }),
    }
