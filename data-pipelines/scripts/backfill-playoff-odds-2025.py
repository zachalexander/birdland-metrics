#!/usr/bin/env python3
"""
Backfill 2025 playoff odds history from ELO full history CSV.

Reconstructs weekly snapshots of AL playoff odds for every Monday of the 2025
season using Monte Carlo simulation. For each snapshot date:
  - Computes actual W-L records from games completed before that date
  - Uses each team's most recent post-game ELO as of that date
  - Builds remaining schedule (games after that date)
  - Runs 1,000 Monte Carlo sims
  - Computes AL playoff odds (3 div winners + 3 WC = top 6 in AL)

Output: JSON array uploaded to s3://mlb-predictions-2026/playoff-odds-history-2025.json

Requirements:
  - Python 3.10+
  - pip install numpy boto3 pandas

Usage:
  python backfill-playoff-odds-2025.py
  python backfill-playoff-odds-2025.py --upload
  python backfill-playoff-odds-2025.py --sims 5000 --upload
"""

import argparse
import io
import json
import logging
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

# Add the shared mlb_common layer to the path
LAYER_PATH = Path(__file__).resolve().parent.parent / "layers" / "mlb-pipeline-common" / "python"
sys.path.insert(0, str(LAYER_PATH))

from mlb_common.team_codes import TEAM_LEAGUE, TEAM_DIVISION
from mlb_common.elo import expected_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ELO_BUCKET = "mlb-elo-ratings-output"
ELO_HISTORY_KEY = "elo-ratings-full-history.csv"
ELO_BASELINE_KEY = "elo_rating_end_of_2024.csv"
PREDICTIONS_BUCKET = "mlb-predictions-2026"
OUTPUT_KEY = "playoff-odds-history-2025.json"

HFA = 55
SIM_COUNT = 1000
SEASON_PREFIX = "2025-"

# Monday snapshot dates: late March through end of September 2025
SEASON_START = date(2025, 3, 24)
SEASON_END = date(2025, 9, 29)


def get_monday_dates(start: date, end: date) -> list[date]:
    """Generate every Monday between start and end (inclusive)."""
    current = start
    # Advance to first Monday on or after start
    while current.weekday() != 0:
        current += timedelta(days=1)
    dates = []
    while current <= end:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def load_elo_history(s3) -> pd.DataFrame:
    """Load the full ELO history CSV from S3."""
    obj = s3.get_object(Bucket=ELO_BUCKET, Key=ELO_HISTORY_KEY)
    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    # Filter to 2025 season
    df = df[df["date"].str.startswith(SEASON_PREFIX)].copy()
    df["date"] = pd.to_datetime(df["date"])
    logger.info(f"Loaded {len(df)} games from 2025 ELO history")
    return df


def load_baseline_elo(s3) -> dict[str, float]:
    """Load end-of-2024 ELO ratings as baseline."""
    obj = s3.get_object(Bucket=ELO_BUCKET, Key=ELO_BASELINE_KEY)
    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    baseline = {}
    for _, row in df.iterrows():
        baseline[row["team"]] = float(row["elo"])
    logger.info(f"Loaded baseline ELO for {len(baseline)} teams")
    return baseline


def compute_snapshot(
    snapshot_date: date,
    elo_history: pd.DataFrame,
    baseline_elo: dict[str, float],
    sim_count: int,
) -> list[dict]:
    """
    Compute playoff odds for a single snapshot date.

    Uses the ELO history as both results (games before snapshot) and schedule
    (games on or after snapshot — since 2025 is complete, all games exist in history).

    Returns list of dicts: {date, team, playoff_pct, division_pct, wildcard_pct}
    """
    snap_dt = pd.Timestamp(snapshot_date)

    # Games completed before snapshot date
    completed = elo_history[elo_history["date"] < snap_dt]
    # "Remaining" games are those on or after snapshot — we know results but simulate them
    remaining = elo_history[elo_history["date"] >= snap_dt]

    # Actual W-L from completed games
    actual_wins = defaultdict(int)
    for _, row in completed.iterrows():
        home, away = row["home_team"], row["away_team"]
        if row["home_score"] > row["away_score"]:
            actual_wins[home] += 1
        else:
            actual_wins[away] += 1

    # Most recent ELO as of snapshot date
    current_elo = dict(baseline_elo)  # start with baseline
    if len(completed) > 0:
        for _, row in completed.iterrows():
            current_elo[row["home_team"]] = float(row["home_elo_after"])
            current_elo[row["away_team"]] = float(row["away_elo_after"])

    # All teams in history
    all_teams = sorted(set(elo_history["home_team"]) | set(elo_history["away_team"]))
    al_teams = [t for t in all_teams if TEAM_LEAGUE.get(t) == "AL"]
    team_idx = {team: i for i, team in enumerate(all_teams)}

    # AL division groupings
    al_divisions = {}
    for t in al_teams:
        div = TEAM_DIVISION.get(t, "Unknown")
        al_divisions.setdefault(div, []).append(t)

    # Build simulation matrix
    sim_matrix = np.zeros((sim_count, len(all_teams)))

    # Seed with actual wins
    for team, idx in team_idx.items():
        sim_matrix[:, idx] = actual_wins.get(team, 0)

    # Simulate remaining games using ELO-based probabilities
    for _, row in remaining.iterrows():
        home, away = row["home_team"], row["away_team"]
        if home not in current_elo or away not in current_elo:
            continue

        p_home_win = expected_score(current_elo[home], current_elo[away], hfa=HFA)
        draws = np.random.rand(sim_count)
        home_wins = draws < p_home_win
        sim_matrix[:, team_idx[home]] += home_wins.astype(int)
        sim_matrix[:, team_idx[away]] += (~home_wins).astype(int)

    # Compute playoff odds
    playoff_count = defaultdict(int)
    division_count = defaultdict(int)
    wildcard_count = defaultdict(int)

    for sim_idx in range(sim_count):
        al_wins = {t: sim_matrix[sim_idx, team_idx[t]] for t in al_teams}

        # Division winners
        div_winners = set()
        for div, div_teams in al_divisions.items():
            winner = max(div_teams, key=lambda t: al_wins[t])
            div_winners.add(winner)
            division_count[winner] += 1

        # Wild cards: next 3 best
        remaining_teams = [(t, al_wins[t]) for t in al_teams if t not in div_winners]
        remaining_teams.sort(key=lambda x: x[1], reverse=True)
        wc_teams = {t for t, _ in remaining_teams[:3]}
        for t in wc_teams:
            wildcard_count[t] += 1

        for t in div_winners | wc_teams:
            playoff_count[t] += 1

    # Build results
    date_str = snapshot_date.isoformat()
    results = []
    for t in al_teams:
        results.append({
            "date": date_str,
            "team": t,
            "playoff_pct": round(100 * playoff_count[t] / sim_count, 1),
            "division_pct": round(100 * division_count[t] / sim_count, 1),
            "wildcard_pct": round(100 * wildcard_count[t] / sim_count, 1),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Backfill 2025 playoff odds history")
    parser.add_argument("--upload", action="store_true", help="Upload result to S3")
    parser.add_argument("--sims", type=int, default=SIM_COUNT, help="Simulations per snapshot")
    parser.add_argument("--output", type=str, default=None, help="Local output file path")
    args = parser.parse_args()

    s3 = boto3.client("s3")

    logger.info("Loading data from S3...")
    elo_history = load_elo_history(s3)
    baseline_elo = load_baseline_elo(s3)

    monday_dates = get_monday_dates(SEASON_START, SEASON_END)
    logger.info(f"Will compute {len(monday_dates)} weekly snapshots")

    all_results = []
    for i, snap_date in enumerate(monday_dates):
        logger.info(f"Snapshot {i+1}/{len(monday_dates)}: {snap_date}")
        results = compute_snapshot(snap_date, elo_history, baseline_elo, args.sims)
        all_results.extend(results)

        # Log BAL odds for this snapshot
        bal = next((r for r in results if r["team"] == "BAL"), None)
        if bal:
            logger.info(f"  BAL: {bal['playoff_pct']}% playoff, {bal['division_pct']}% div")

    logger.info(f"Total rows: {len(all_results)} ({len(monday_dates)} snapshots × {len(all_results) // len(monday_dates)} AL teams)")

    # Save locally
    output_path = args.output or "playoff-odds-history-2025.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Wrote {output_path}")

    # Upload to S3
    if args.upload:
        s3.put_object(
            Bucket=PREDICTIONS_BUCKET,
            Key=OUTPUT_KEY,
            Body=json.dumps(all_results),
            ContentType="application/json",
            CacheControl="no-cache, must-revalidate",
        )
        logger.info(f"Uploaded to s3://{PREDICTIONS_BUCKET}/{OUTPUT_KEY}")


if __name__ == "__main__":
    main()
