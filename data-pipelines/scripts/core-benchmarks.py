#!/usr/bin/env python3
"""
Core player benchmarks pipeline.

Fetches current-season batting and pitching stats from FanGraphs via
pybaseball, evaluates pass/fail benchmarks for core Orioles players,
and outputs JSON. Optionally uploads to S3.

Requirements:
  - Python 3.10+
  - pip install pybaseball boto3

Usage:
  python core-benchmarks.py --season 2026
  python core-benchmarks.py --season 2025 --upload
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pybaseball
import boto3

# ---------------------------------------------------------------------------
# Add the shared mlb_common layer to the path
# ---------------------------------------------------------------------------
LAYER_PATH = Path(__file__).resolve().parent.parent / "layers" / "mlb-pipeline-common" / "python"
sys.path.insert(0, str(LAYER_PATH))

from mlb_common.config import PLAYER_STATS_BUCKET

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "benchmarks"

# ---------------------------------------------------------------------------
# Player definitions and benchmarks
# ---------------------------------------------------------------------------

BATTERS = [
    {
        "name": "Gunnar Henderson",
        "playerId": "683002",
        "position": "SS",
        "narrative": "Can he bounce back to 2024 MVP form?",
        "benchmarks": [
            {
                "key": "barrel_pct",
                "label": "Barrel% >= 10%",
                "description": "Returned to 2024 power form",
                "target": 10.0,
                "direction": "gte",
                "category": "power",
                "stat": "Barrel%",
            },
            {
                "key": "wrc_plus",
                "label": "wRC+ >= 140",
                "description": "Superstar-level production",
                "target": 140,
                "direction": "gte",
                "category": "production",
                "stat": "wRC+",
            },
            {
                "key": "hr_pace",
                "label": "HR pace >= 30",
                "description": "On pace for 30+ home runs",
                "target": 30,
                "direction": "gte",
                "category": "power",
                "stat": "hr_pace",
            },
        ],
    },
    {
        "name": "Adley Rutschman",
        "playerId": "668939",
        "position": "C",
        "narrative": "Elite discipline or power-chasing trap?",
        "benchmarks": [
            {
                "key": "obp",
                "label": "OBP >= .340",
                "description": "Elite on-base ability",
                "target": .340,
                "direction": "gte",
                "category": "discipline",
                "stat": "OBP",
            },
            {
                "key": "bb_pct",
                "label": "BB% >= 10%",
                "description": "Above-average walk rate",
                "target": 10.0,
                "direction": "gte",
                "category": "discipline",
                "stat": "BB%",
            },
            {
                "key": "wrc_plus",
                "label": "wRC+ >= 115",
                "description": "Above-average offensive catcher",
                "target": 115,
                "direction": "gte",
                "category": "production",
                "stat": "wRC+",
            },
        ],
    },
    {
        "name": "Jordan Westburg",
        "playerId": "682614",
        "position": "2B/3B",
        "narrative": "Can the breakout sustain?",
        "benchmarks": [
            {
                "key": "ops",
                "label": "OPS >= .800",
                "description": "Solid middle-of-the-order bat",
                "target": .800,
                "direction": "gte",
                "category": "production",
                "stat": "OPS",
            },
            {
                "key": "iso",
                "label": "ISO >= .180",
                "description": "Sustained power production",
                "target": .180,
                "direction": "gte",
                "category": "power",
                "stat": "ISO",
            },
            {
                "key": "games_pace",
                "label": "Games pace >= 140",
                "description": "Full-season health",
                "target": 140,
                "direction": "gte",
                "category": "health",
                "stat": "games_pace",
            },
        ],
    },
    {
        "name": "Colton Cowser",
        "playerId": "681297",
        "position": "OF",
        "narrative": "Contact and power development",
        "benchmarks": [
            {
                "key": "k_pct",
                "label": "K% <= 22%",
                "description": "Improved contact ability",
                "target": 22.0,
                "direction": "lte",
                "category": "contact",
                "stat": "K%",
            },
            {
                "key": "hard_pct",
                "label": "Hard% >= 38%",
                "description": "Quality of contact",
                "target": 38.0,
                "direction": "gte",
                "category": "power",
                "stat": "Hard%",
            },
            {
                "key": "wrc_plus",
                "label": "wRC+ >= 110",
                "description": "Above-average regular",
                "target": 110,
                "direction": "gte",
                "category": "production",
                "stat": "wRC+",
            },
        ],
    },
    {
        "name": "Pete Alonso",
        "playerId": "624413",
        "position": "1B",
        "narrative": "Worth the free agent investment?",
        "benchmarks": [
            {
                "key": "hr_pace",
                "label": "HR pace >= 30",
                "description": "On pace for 30+ home runs",
                "target": 30,
                "direction": "gte",
                "category": "power",
                "stat": "hr_pace",
            },
            {
                "key": "exit_velo",
                "label": "Exit velo >= 91 mph",
                "description": "No physical decline",
                "target": 91.0,
                "direction": "gte",
                "category": "power",
                "stat": "EV",
            },
            {
                "key": "slg",
                "label": "SLG >= .470",
                "description": "Power production in the lineup",
                "target": .470,
                "direction": "gte",
                "category": "power",
                "stat": "SLG",
            },
        ],
    },
    {
        "name": "Jackson Holliday",
        "playerId": "696137",
        "position": "2B",
        "narrative": "Can the #1 prospect make the adjustment?",
        "benchmarks": [
            {
                "key": "k_pct",
                "label": "K% <= 25%",
                "description": "Improved contact from 2024",
                "target": 25.0,
                "direction": "lte",
                "category": "contact",
                "stat": "K%",
            },
            {
                "key": "bb_pct",
                "label": "BB% >= 9%",
                "description": "MLB-level plate discipline",
                "target": 9.0,
                "direction": "gte",
                "category": "discipline",
                "stat": "BB%",
            },
            {
                "key": "avg",
                "label": "AVG >= .250",
                "description": "Basic hitting threshold",
                "target": .250,
                "direction": "gte",
                "category": "contact",
                "stat": "AVG",
            },
        ],
    },
]

PITCHERS = [
    {
        "name": "Kyle Bradish",
        "playerId": "669062",
        "position": "SP",
        "narrative": "Can the ace return from injury?",
        "benchmarks": [
            {
                "key": "era",
                "label": "ERA <= 3.50",
                "description": "Ace-level production",
                "target": 3.50,
                "direction": "lte",
                "category": "production",
                "stat": "ERA",
            },
            {
                "key": "k_per_9",
                "label": "K/9 >= 9.0",
                "description": "Swing-and-miss stuff intact",
                "target": 9.0,
                "direction": "gte",
                "category": "power",
                "stat": "K/9",
            },
            {
                "key": "ip_pace",
                "label": "IP pace >= 160",
                "description": "Full-season health",
                "target": 160,
                "direction": "gte",
                "category": "health",
                "stat": "ip_pace",
            },
        ],
    },
    {
        "name": "Trevor Rogers",
        "playerId": "669432",
        "position": "SP",
        "narrative": "Can he be a reliable mid-rotation arm?",
        "benchmarks": [
            {
                "key": "era",
                "label": "ERA <= 4.00",
                "description": "Solid starter threshold",
                "target": 4.00,
                "direction": "lte",
                "category": "production",
                "stat": "ERA",
            },
            {
                "key": "whip",
                "label": "WHIP <= 1.25",
                "description": "Limiting baserunners",
                "target": 1.25,
                "direction": "lte",
                "category": "contact",
                "stat": "WHIP",
            },
            {
                "key": "k_pct",
                "label": "K% >= 22%",
                "description": "Adequate strikeout rate",
                "target": 22.0,
                "direction": "gte",
                "category": "power",
                "stat": "K%",
            },
        ],
    },
    {
        "name": "Shane Baz",
        "playerId": "669358",
        "position": "SP",
        "narrative": "Can he stay healthy and produce?",
        "benchmarks": [
            {
                "key": "era",
                "label": "ERA <= 3.75",
                "description": "Above-average starter",
                "target": 3.75,
                "direction": "lte",
                "category": "production",
                "stat": "ERA",
            },
            {
                "key": "fip",
                "label": "FIP <= 3.75",
                "description": "Skills match results",
                "target": 3.75,
                "direction": "lte",
                "category": "production",
                "stat": "FIP",
            },
            {
                "key": "ip_pace",
                "label": "IP pace >= 140",
                "description": "Health indicator",
                "target": 140,
                "direction": "gte",
                "category": "health",
                "stat": "ip_pace",
            },
        ],
    },
    {
        "name": "Ryan Helsley",
        "playerId": "664854",
        "position": "CL",
        "narrative": "Elite closer production?",
        "benchmarks": [
            {
                "key": "era",
                "label": "ERA <= 2.50",
                "description": "Dominant reliever threshold",
                "target": 2.50,
                "direction": "lte",
                "category": "production",
                "stat": "ERA",
            },
            {
                "key": "k_per_9",
                "label": "K/9 >= 11.0",
                "description": "Elite swing-and-miss",
                "target": 11.0,
                "direction": "gte",
                "category": "power",
                "stat": "K/9",
            },
            {
                "key": "sv_pace",
                "label": "SV pace >= 35",
                "description": "Closer workload",
                "target": 35,
                "direction": "gte",
                "category": "production",
                "stat": "sv_pace",
            },
        ],
    },
]

BULLPEN_DEF = {
    "name": "Team Bullpen",
    "playerId": "bullpen",
    "position": "RP",
    "narrative": "Can the pen hold leads?",
    "benchmarks": [
        {
            "key": "era",
            "label": "ERA <= 3.75",
            "description": "Solid relief corps",
            "target": 3.75,
            "direction": "lte",
            "category": "production",
        },
        {
            "key": "k_per_9",
            "label": "K/9 >= 9.5",
            "description": "Swing-and-miss from the pen",
            "target": 9.5,
            "direction": "gte",
            "category": "power",
        },
        {
            "key": "whip",
            "label": "WHIP <= 1.25",
            "description": "Limiting baserunners in leverage",
            "target": 1.25,
            "direction": "lte",
            "category": "contact",
        },
    ],
}

PLAYERS = BATTERS + PITCHERS


def fetch_stats(season: int):
    """Fetch FanGraphs batting and pitching stats for the season."""
    print(f"Fetching FanGraphs batting stats for {season}...")
    batting_df = pybaseball.batting_stats(season, qual=0)
    print(f"  Got {len(batting_df)} batter rows")

    print(f"Fetching FanGraphs pitching stats for {season}...")
    pitching_df = pybaseball.pitching_stats(season, qual=0)
    print(f"  Got {len(pitching_df)} pitcher rows")

    return batting_df, pitching_df


def find_player_row(df, name: str):
    """Find a player row by name. Returns None if not found."""
    matches = df[df["Name"] == name]
    if len(matches) == 0:
        # Try last-name match as fallback
        last_name = name.split()[-1]
        matches = df[df["Name"].str.contains(last_name, case=False, na=False)]
        if len(matches) == 1:
            print(f"  Fuzzy match: '{name}' -> '{matches.iloc[0]['Name']}'")
            return matches.iloc[0]
        print(f"  WARNING: Player '{name}' not found in FanGraphs data")
        return None
    return matches.iloc[0]


def get_stat_value(row, stat_key: str, team_games: int | None = None):
    """Extract a stat value from a player row. Returns None if unavailable."""
    if row is None:
        return None

    if stat_key == "hr_pace":
        g = row.get("G")
        hr = row.get("HR")
        if g and g > 0 and hr is not None:
            return round((hr / g) * 162, 1)
        return None

    if stat_key == "games_pace":
        g = row.get("G")
        if g is not None and team_games and team_games > 0:
            return round((g / team_games) * 162, 0)
        return None

    if stat_key == "ip_pace":
        ip = row.get("IP")
        if ip is not None and team_games and team_games > 0:
            return round((float(ip) / team_games) * 162, 1)
        return None

    if stat_key == "sv_pace":
        sv = row.get("SV")
        if sv is not None and team_games and team_games > 0:
            return round((float(sv) / team_games) * 162, 1)
        return None

    val = row.get(stat_key)
    if val is None:
        return None
    val = float(val)
    if val != val:  # NaN check
        return None

    # pybaseball returns BB%, K%, Barrel%, Hard% as 0-1 decimals; convert to percentages
    if stat_key in ("BB%", "K%", "Barrel%", "Hard%"):
        val = val * 100

    return val


PACE_RAW_KEYS = {
    "hr_pace": "HR",
    "ip_pace": "IP",
    "games_pace": "G",
    "sv_pace": "SV",
}


def get_raw_value(row, stat_key: str):
    """For pace-based keys, return the raw counting stat (e.g. actual HR, IP)."""
    raw_key = PACE_RAW_KEYS.get(stat_key)
    if raw_key is None or row is None:
        return None
    val = row.get(raw_key)
    if val is None:
        return None
    return float(round(float(val), 1))


def evaluate_benchmark(current, target: float, direction: str) -> bool:
    """Evaluate whether a benchmark is met."""
    if current is None:
        return False
    if direction == "gte":
        return bool(current >= target)
    if direction == "lte":
        return bool(current <= target)
    return False


def estimate_team_games(batting_df, season: int) -> int:
    """Estimate how many games the team has played so far."""
    # Use max games played by any qualifying Orioles batter in our list
    max_g = 0
    for player_def in BATTERS:
        row = find_player_row(batting_df, player_def["name"])
        if row is not None:
            g = row.get("G")
            if g and g > max_g:
                max_g = int(g)
    # Fall back to a reasonable estimate if we can't find any
    return max_g if max_g > 0 else 162


def aggregate_bullpen(pitching_df: "pd.DataFrame") -> dict | None:
    """Aggregate bullpen stats for BAL relievers."""
    bal = pitching_df[pitching_df["Team"] == "BAL"].copy()
    if len(bal) == 0:
        print("  WARNING: No BAL pitchers found for bullpen aggregation")
        return None

    # Relievers = more Relief-IP than Start-IP (or no starts)
    bal["_relief_ip"] = bal["Relief-IP"].fillna(0).astype(float)
    bal["_start_ip"] = bal["Start-IP"].fillna(0).astype(float)
    relievers = bal[bal["_relief_ip"] > bal["_start_ip"]]

    if len(relievers) == 0:
        print("  WARNING: No BAL relievers found")
        return None

    total_ip = float(relievers["IP"].sum())
    total_er = float(relievers["ER"].sum())
    total_so = float(relievers["SO"].sum())
    total_bb = float(relievers["BB"].sum())
    total_h = float(relievers["H"].sum())

    if total_ip <= 0:
        return None

    print(f"  Bullpen: {len(relievers)} relievers, {total_ip:.1f} IP")

    return {
        "era": float(round(total_er / total_ip * 9, 2)),
        "k_per_9": float(round(total_so / total_ip * 9, 2)),
        "whip": float(round((total_bb + total_h) / total_ip, 2)),
    }


def build_benchmarks(season: int) -> dict:
    """Build the full benchmarks JSON structure."""
    batting_df, pitching_df = fetch_stats(season)
    team_games = estimate_team_games(batting_df, season)
    print(f"  Estimated team games played: {team_games}")

    pitcher_names = {p["name"] for p in PITCHERS}

    players_output = []
    for player_def in PLAYERS:
        df = pitching_df if player_def["name"] in pitcher_names else batting_df
        row = find_player_row(df, player_def["name"])
        benchmarks = []

        for bm in player_def["benchmarks"]:
            current = get_stat_value(row, bm["stat"], team_games)

            # Round appropriately and ensure native Python float
            if current is not None:
                if bm["stat"] in ("OBP", "SLG", "OPS", "AVG", "ISO"):
                    current = float(round(current, 3))
                elif bm["stat"] in ("BB%", "K%", "Barrel%", "Hard%"):
                    current = float(round(current, 1))
                elif bm["stat"] in ("EV", "ERA", "FIP", "WHIP", "K/9"):
                    current = float(round(current, 2))
                elif bm["stat"] in ("wRC+",):
                    current = float(round(current, 0))
                else:
                    current = float(round(current, 1))

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
    bullpen_stats = aggregate_bullpen(pitching_df)
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
    print(f"\nResults: {total_met} / {total} benchmarks met")

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "season": season,
        "players": players_output,
    }


def upload_to_s3(data: dict, bucket: str, key: str):
    """Upload JSON to S3."""
    s3 = boto3.client("s3")
    body = json.dumps(data, indent=2)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    print(f"Uploaded to s3://{bucket}/{key}")


def main():
    parser = argparse.ArgumentParser(description="Core player benchmarks pipeline")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="Season year (default: current year)")
    parser.add_argument("--upload", action="store_true",
                        help="Upload result to S3")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path (default: output/benchmarks/core-benchmarks-latest.json)")
    args = parser.parse_args()

    data = build_benchmarks(args.season)

    # Write local file
    output_path = Path(args.output) if args.output else OUTPUT_DIR / "core-benchmarks-latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Wrote {output_path}")

    # Print summary
    for p in data["players"]:
        met = sum(1 for b in p["benchmarks"] if b["met"])
        status = f"{met}/{len(p['benchmarks'])}"
        print(f"  {p['name']:20s} {status}  ", end="")
        for b in p["benchmarks"]:
            icon = "+" if b["met"] else "-"
            val = b["current"] if b["current"] is not None else "N/A"
            print(f"[{icon} {b['key']}={val}] ", end="")
        print()

    if args.upload:
        upload_to_s3(data, PLAYER_STATS_BUCKET, "benchmarks/core-benchmarks-latest.json")


if __name__ == "__main__":
    main()
