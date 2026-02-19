#!/usr/bin/env python3
"""
Backtest fade curve accuracy using Brier scores.

Runs Monte Carlo simulations at every unique game date for a season,
compares predicted playoff probabilities against actual outcomes,
and computes Brier scores + calibration metrics for each fade curve.

Usage:
  python backtest-fade-curves.py --season 2024 --sims 1000
  python backtest-fade-curves.py --season 2025 --sims 1000
"""

import argparse
import json
import logging
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (same as backfill script)
# ---------------------------------------------------------------------------

K = 6
HFA = 55
MOV_MULTIPLIER = 2.2
FADE_GAMES = 100

MODEL_DIR = Path(__file__).resolve().parent.parent / "model-2026-updates"

TEAM_LEAGUE = {
    "BAL": "AL", "BOS": "AL", "NYY": "AL", "TB": "AL", "TOR": "AL",
    "CWS": "AL", "CLE": "AL", "DET": "AL", "KC": "AL", "MIN": "AL",
    "HOU": "AL", "LAA": "AL", "ATH": "AL", "SEA": "AL", "TEX": "AL",
    "ATL": "NL", "MIA": "NL", "NYM": "NL", "PHI": "NL", "WSH": "NL",
    "CHC": "NL", "CIN": "NL", "MIL": "NL", "PIT": "NL", "STL": "NL",
    "AZ": "NL", "COL": "NL", "LAD": "NL", "SD": "NL", "SF": "NL",
}

TEAM_DIVISION = {
    "BAL": "AL East", "BOS": "AL East", "NYY": "AL East", "TB": "AL East", "TOR": "AL East",
    "CWS": "AL Central", "CLE": "AL Central", "DET": "AL Central", "KC": "AL Central", "MIN": "AL Central",
    "HOU": "AL West", "LAA": "AL West", "ATH": "AL West", "SEA": "AL West", "TEX": "AL West",
    "ATL": "NL East", "MIA": "NL East", "NYM": "NL East", "PHI": "NL East", "WSH": "NL East",
    "CHC": "NL Central", "CIN": "NL Central", "MIL": "NL Central", "PIT": "NL Central", "STL": "NL Central",
    "AZ": "NL West", "COL": "NL West", "LAD": "NL West", "SD": "NL West", "SF": "NL West",
}

# Actual AL playoff teams (ground truth for Brier scoring)
ACTUAL_PLAYOFF_TEAMS = {
    2024: {"BAL", "NYY", "CLE", "HOU", "DET", "KC"},       # DIV: BAL, CLE, HOU | WC: NYY, DET, KC
    2025: {"NYY", "TOR", "SEA", "CLE", "BOS", "HOU"},      # DIV: NYY, CLE, SEA | WC: TOR, BOS, HOU
}

SEASON_DATES = {
    2024: (date(2024, 3, 18), date(2024, 9, 30)),
    2025: (date(2025, 3, 24), date(2025, 9, 29)),
}


# ---------------------------------------------------------------------------
# ELO math
# ---------------------------------------------------------------------------

def expected_score(elo_a: float, elo_b: float, hfa: float = 0.0) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - (elo_a + hfa)) / 400.0))


MOV_CAP = None  # Global cap; set per-run before calling replay functions


def mov_mult(score_diff: int, elo_diff: float) -> float:
    raw = math.log(abs(score_diff) + 1) * (MOV_MULTIPLIER / (0.001 * abs(elo_diff) + MOV_MULTIPLIER))
    if MOV_CAP is not None:
        return min(raw, MOV_CAP)
    return raw


def elo_shift(elo: float, exp: float, actual: float, mov: float = 1.0) -> float:
    return K * mov * (actual - exp)


# ---------------------------------------------------------------------------
# Fade curves
# ---------------------------------------------------------------------------

def fade_pct(gp: int, curve: str) -> float:
    if gp >= FADE_GAMES:
        return 1.0
    t = gp / float(FADE_GAMES)
    if curve == "linear":
        return t
    elif curve == "cosine":
        return 0.5 * (1.0 - math.cos(math.pi * t))
    elif curve == "sigmoid":
        k = 10
        return 1.0 / (1.0 + math.exp(-k * (t - 0.5)))
    elif curve == "quadratic":
        return 1.0 - (1.0 - t) ** 2
    else:
        raise ValueError(f"Unknown fade curve: {curve}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_prior_season_elo(season: int) -> dict[str, float]:
    preseason_path = MODEL_DIR / f"preseason_elo_{season}.csv"
    if preseason_path.exists():
        df = pd.read_csv(preseason_path)
        return {row["team"]: float(row["preseason_elo"]) for _, row in df.iterrows()}

    path = MODEL_DIR / f"elo_rating_end_of_{season - 1}.csv"
    df = pd.read_csv(path)
    return {row["team"]: 0.6 * float(row["elo"]) + 0.4 * 1500 for _, row in df.iterrows()}


def load_schedule(season: int) -> pd.DataFrame:
    path = MODEL_DIR / f"schedule_{season}_full.csv"
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    completed = df[df["status"] == "Final"].copy()
    return completed.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Core ELO replay
# ---------------------------------------------------------------------------

def replay_elo_to_date(schedule_df, preseason_elo, cutoff_date):
    current_elo = dict(preseason_elo)
    games_played = defaultdict(int)

    before = schedule_df[schedule_df["date"] < cutoff_date]
    for _, row in before.iterrows():
        home, away = row["homeTeam"], row["awayTeam"]
        if home not in current_elo or away not in current_elo:
            continue
        h_elo, a_elo = current_elo[home], current_elo[away]
        exp_h = expected_score(h_elo, a_elo, hfa=HFA)
        score_diff = abs(row["homeScore"] - row["awayScore"])
        elo_diff = h_elo + HFA - a_elo
        m = mov_mult(score_diff, elo_diff)
        actual_h = 1.0 if row["homeScore"] > row["awayScore"] else 0.0
        shift = elo_shift(h_elo, exp_h, actual_h, m)
        current_elo[home] = h_elo + shift
        current_elo[away] = a_elo - shift
        games_played[home] += 1
        games_played[away] += 1

    return current_elo, dict(games_played)


def regress_elo(current_elo, preseason_elo, games_played, curve="linear"):
    regressed = {}
    for team, cur in current_elo.items():
        gp = games_played.get(team, 0)
        pct = fade_pct(gp, curve)
        pre = preseason_elo.get(team, cur)
        regressed[team] = pct * cur + (1.0 - pct) * pre
    return regressed


# ---------------------------------------------------------------------------
# Monte Carlo + playoff odds
# ---------------------------------------------------------------------------

def simulate_remaining(remaining_df, regressed_elo, actual_wins, sim_count):
    all_teams = sorted(regressed_elo.keys())
    team_idx = {t: i for i, t in enumerate(all_teams)}
    n = len(all_teams)
    sim_matrix = np.zeros((sim_count, n))

    for team, idx in team_idx.items():
        sim_matrix[:, idx] = actual_wins.get(team, 0)

    for _, row in remaining_df.iterrows():
        home, away = row["homeTeam"], row["awayTeam"]
        if home not in regressed_elo or away not in regressed_elo:
            continue
        p_home = expected_score(regressed_elo[home], regressed_elo[away], hfa=HFA)
        draws = np.random.rand(sim_count)
        home_wins = draws < p_home
        sim_matrix[:, team_idx[home]] += home_wins.astype(int)
        sim_matrix[:, team_idx[away]] += (~home_wins).astype(int)

    return sim_matrix, all_teams, team_idx


def compute_al_playoff_odds(sim_matrix, all_teams, team_idx, sim_count):
    al_teams = [t for t in all_teams if TEAM_LEAGUE.get(t) == "AL"]
    al_divisions = {}
    for t in al_teams:
        al_divisions.setdefault(TEAM_DIVISION.get(t, "Unknown"), []).append(t)

    playoff_count = defaultdict(int)
    for sim_idx in range(sim_count):
        al_wins = {t: sim_matrix[sim_idx, team_idx[t]] for t in al_teams}
        div_winners = set()
        for div, div_teams in al_divisions.items():
            winner = max(div_teams, key=lambda t: (al_wins[t], np.random.rand()))
            div_winners.add(winner)
        remaining = [(t, al_wins[t]) for t in al_teams if t not in div_winners]
        remaining.sort(key=lambda x: (x[1], np.random.rand()), reverse=True)
        wc_teams = {t for t, _ in remaining[:3]}
        for t in div_winners | wc_teams:
            playoff_count[t] += 1

    return {t: playoff_count[t] / sim_count for t in al_teams}


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(schedule_df, preseason_elo, season, sim_count, curve):
    """Run simulations at every unique game date, return per-snapshot predictions."""
    unique_dates = sorted(schedule_df["date"].dt.date.unique())
    al_teams = sorted(t for t in TEAM_LEAGUE if TEAM_LEAGUE[t] == "AL")
    actual_playoff = ACTUAL_PLAYOFF_TEAMS[season]

    all_predictions = []  # list of (date, {team: prob})

    for i, snap_date in enumerate(unique_dates):
        snap_ts = pd.Timestamp(snap_date)

        current_elo, games_played = replay_elo_to_date(schedule_df, preseason_elo, snap_ts)
        regressed = regress_elo(current_elo, preseason_elo, games_played, curve)

        before = schedule_df[schedule_df["date"] < snap_ts]
        actual_wins = defaultdict(int)
        for _, row in before.iterrows():
            if row["homeScore"] > row["awayScore"]:
                actual_wins[row["homeTeam"]] += 1
            else:
                actual_wins[row["awayTeam"]] += 1

        remaining = schedule_df[schedule_df["date"] >= snap_ts]
        sim_matrix, all_teams_list, team_idx = simulate_remaining(
            remaining, regressed, actual_wins, sim_count
        )
        probs = compute_al_playoff_odds(sim_matrix, all_teams_list, team_idx, sim_count)
        all_predictions.append((snap_date, probs))

        if (i + 1) % 20 == 0 or i == 0 or i == len(unique_dates) - 1:
            bal_prob = probs.get("BAL", 0)
            logger.info(
                f"  [{curve}] [{i+1}/{len(unique_dates)}] {snap_date}  "
                f"BAL: {bal_prob:.1%}"
            )

    return all_predictions, al_teams, actual_playoff


def compute_brier_scores(all_predictions, al_teams, actual_playoff):
    """Compute Brier score, log-loss, and calibration metrics."""
    brier_sum = 0.0
    log_loss_sum = 0.0
    n = 0

    # Per-team Brier scores
    team_brier = defaultdict(lambda: {"sum": 0.0, "n": 0})

    # Calibration bins (10 bins: 0-10%, 10-20%, etc.)
    cal_bins = defaultdict(lambda: {"predicted_sum": 0.0, "actual_sum": 0.0, "n": 0})

    # Weekly max change tracking
    team_trajectories = defaultdict(list)

    for snap_date, probs in all_predictions:
        for team in al_teams:
            prob = probs.get(team, 0.0)
            actual = 1.0 if team in actual_playoff else 0.0

            # Brier
            brier = (prob - actual) ** 2
            brier_sum += brier
            team_brier[team]["sum"] += brier
            team_brier[team]["n"] += 1

            # Log-loss (clamp to avoid log(0))
            p = max(min(prob, 0.999), 0.001)
            log_loss_sum += -(actual * math.log(p) + (1 - actual) * math.log(1 - p))

            # Calibration
            bin_idx = min(int(prob * 10), 9)
            cal_bins[bin_idx]["predicted_sum"] += prob
            cal_bins[bin_idx]["actual_sum"] += actual
            cal_bins[bin_idx]["n"] += 1

            team_trajectories[team].append(prob)
            n += 1

    # Max week-to-week changes per team
    max_changes = {}
    for team, traj in team_trajectories.items():
        if len(traj) < 2:
            max_changes[team] = 0.0
        else:
            changes = [abs(traj[i] - traj[i-1]) for i in range(1, len(traj))]
            max_changes[team] = max(changes)

    return {
        "brier_score": brier_sum / n,
        "log_loss": log_loss_sum / n,
        "n_predictions": n,
        "team_brier": {t: v["sum"] / v["n"] for t, v in team_brier.items()},
        "calibration": {
            k: {
                "avg_predicted": v["predicted_sum"] / v["n"],
                "avg_actual": v["actual_sum"] / v["n"],
                "count": v["n"],
            }
            for k, v in sorted(cal_bins.items())
        },
        "max_changes": max_changes,
        "avg_max_change": sum(max_changes.values()) / len(max_changes) if max_changes else 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global MOV_CAP

    parser = argparse.ArgumentParser(description="Backtest MOV cap with Brier scores")
    parser.add_argument("--season", type=int, required=True, choices=[2024, 2025])
    parser.add_argument("--sims", type=int, default=1000)
    args = parser.parse_args()

    season = args.season
    # Test: uncapped (current) vs three cap levels
    configs = [
        ("uncapped", None),
        ("cap-1.25", 1.25),
        ("cap-1.50", 1.50),
        ("cap-1.75", 1.75),
    ]

    logger.info(f"Backtesting {season} season: MOV cap comparison, {args.sims} sims/snapshot")

    preseason_elo = load_prior_season_elo(season)
    schedule_df = load_schedule(season)
    unique_dates = sorted(schedule_df["date"].dt.date.unique())
    logger.info(f"  {len(unique_dates)} unique game dates")

    results = {}
    # Track TOR trajectory for the Jun-Jul window
    tor_trajectories = {}

    for label, cap in configs:
        MOV_CAP = cap
        logger.info(f"\n{'='*60}")
        logger.info(f"Running {label} (MOV_CAP={cap})...")
        logger.info(f"{'='*60}")

        np.random.seed(42)
        predictions, al_teams, actual_playoff = run_backtest(
            schedule_df, preseason_elo, season, args.sims, "linear"
        )
        metrics = compute_brier_scores(predictions, al_teams, actual_playoff)
        results[label] = metrics

        # Extract TOR trajectory for 2025
        if season == 2025:
            tor_traj = []
            for snap_date, probs in predictions:
                tor_traj.append((snap_date, probs.get("TOR", 0)))
            tor_trajectories[label] = tor_traj

    MOV_CAP = None  # Reset

    # --- Print comparison ---
    labels = [l for l, _ in configs]
    col_w = 12

    print(f"\n{'='*80}")
    print(f"  MOV CAP BACKTEST RESULTS — {season} SEASON")
    print(f"  Actual AL playoff teams: {', '.join(sorted(ACTUAL_PLAYOFF_TEAMS[season]))}")
    print(f"  {len(unique_dates)} game dates × 15 AL teams × {args.sims} sims")
    print(f"{'='*80}\n")

    # Effective K table
    print("EFFECTIVE K BY SCORE MARGIN (with each cap)")
    print(f"{'Margin':<10}", end="")
    for l in labels:
        print(f"{l:>{col_w}}", end="")
    print()
    print("-" * (10 + col_w * len(labels)))
    for diff in [1, 2, 3, 5, 7, 9, 12, 15]:
        print(f"{diff:>2}-run    ", end="")
        for l, cap in configs:
            raw = math.log(abs(diff) + 1) * (MOV_MULTIPLIER / (0.001 * 0 + MOV_MULTIPLIER))
            capped = min(raw, cap) if cap else raw
            eff_k = K * capped
            print(f"{eff_k:>{col_w}.1f}", end="")
        print()

    # Overall metrics
    print(f"\nOVERALL METRICS (lower is better)")
    print(f"{'Metric':<20}", end="")
    for l in labels:
        print(f"{l:>{col_w}}", end="")
    print()
    print("-" * (20 + col_w * len(labels)))
    for metric, metric_label in [
        ("brier_score", "Brier Score"),
        ("log_loss", "Log Loss"),
        ("avg_max_change", "Avg Max Change"),
    ]:
        print(f"{metric_label:<20}", end="")
        vals = [results[l][metric] for l in labels]
        best = min(vals)
        for v in vals:
            marker = " *" if v == best else ""
            print(f"{v:>{col_w - len(marker)}.6f}{marker}", end="")
        print()

    # Per-team Brier
    print(f"\nPER-TEAM BRIER SCORES (lower is better)")
    print(f"{'Team':<6} {'Made it?':<9}", end="")
    for l in labels:
        print(f"{l:>{col_w}}", end="")
    print(f"{'Best':>{col_w}}")
    print("-" * (15 + col_w * (len(labels) + 1)))
    al_teams_sorted = sorted(
        results[labels[0]]["team_brier"].keys(),
        key=lambda t: results[labels[0]]["team_brier"][t],
        reverse=True,
    )
    for team in al_teams_sorted:
        made_it = "YES" if team in ACTUAL_PLAYOFF_TEAMS[season] else "no"
        print(f"{team:<6} {made_it:<9}", end="")
        vals = [results[l]["team_brier"][team] for l in labels]
        best_val = min(vals)
        best_label = labels[vals.index(best_val)]
        for v in vals:
            print(f"{v:>{col_w}.6f}", end="")
        print(f"{best_label:>{col_w}}")

    # Smoothness
    print(f"\nMAX GAME-TO-GAME CHANGE PER TEAM (smoothness — lower is better)")
    print(f"{'Team':<6}", end="")
    for l in labels:
        print(f"{l:>{col_w}}", end="")
    print()
    print("-" * (6 + col_w * len(labels)))
    for team in sorted(results[labels[0]]["max_changes"].keys()):
        print(f"{team:<6}", end="")
        for l in labels:
            v = results[l]["max_changes"][team]
            print(f"{v:>{col_w - 1}.1%} ", end="")
        print()

    # TOR Jun-Jul trajectory for 2025
    if season == 2025 and tor_trajectories:
        print(f"\nTOR PLAYOFF ODDS TRAJECTORY — JUN 22 TO JUL 7 (the hot streak)")
        print(f"{'Date':<12}", end="")
        for l in labels:
            print(f"{l:>{col_w}}", end="")
        print()
        print("-" * (12 + col_w * len(labels)))
        for i, (snap_date, _) in enumerate(tor_trajectories[labels[0]]):
            if date(2025, 6, 18) <= snap_date <= date(2025, 7, 10):
                print(f"{str(snap_date):<12}", end="")
                for l in labels:
                    prob = tor_trajectories[l][i][1]
                    print(f"{prob:>{col_w - 1}.1%} ", end="")
                print()

    # Save raw results
    output_path = f"backtest-mov-cap-{season}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nWrote detailed results to {output_path}")


if __name__ == "__main__":
    main()
