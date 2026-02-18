#!/usr/bin/env python3
"""
backtest-war-modes.py — Comprehensive backtest of preseason WAR approaches.

For each combination of (WAR mode, fade curve, season):
  1. Generates preseason ELOs
  2. Replays the season game-by-game
  3. For each game, predicts win probability using regressed ELO
  4. Updates raw ELO after the game (K=6)
  5. Computes accuracy metrics

Fade curves control how quickly preseason WAR influence fades:
  regressed = pct * raw_elo + (1-pct) * preseason_elo
  where pct = min(gp / fade_games, 1.0)

Metrics:
  - Brier score (lower = better calibrated probabilities)
  - Log loss (lower = better, penalizes confident wrong predictions)
  - Accuracy % (% of games where favorite won)
  - Win prediction RMSE (predicted vs actual team wins)
"""

import math
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "model-2026-updates")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
K = 6
HFA = 55
MOV_MULTIPLIER = 2.2
MEAN_ELO = 1500
REVERSION_FRACTION = 0.4
SPREAD_COMPRESSION = 0.75
WAR_ELO_FACTOR = 5.0
WAR_WEIGHT = 0.5
WAR_TO_ELO = 5.5
MAX_PLAYER_WAR = 5.0

WAR_COLUMN = {2024: "2023 WAR", 2025: "2024 WAR", 2026: "2025 WAR"}
TEAM_WAR_FILE = {
    2024: "team_war_2023.csv",
    2025: "team_war_2024.csv",
    2026: "team_war_2026_projected.csv",
}

FG_TO_CANONICAL = {
    "ARI": "AZ", "CHW": "CWS", "KCR": "KC",
    "SDP": "SD", "SFG": "SF", "TBR": "TB", "WSN": "WSH",
}
NICKNAME_TO_CANONICAL = {
    "Angels": "LAA", "Astros": "HOU", "Athletics": "ATH", "Blue Jays": "TOR",
    "Braves": "ATL", "Brewers": "MIL", "Cardinals": "STL", "Cubs": "CHC",
    "Diamondbacks": "AZ", "Dodgers": "LAD", "Giants": "SF", "Guardians": "CLE",
    "Mariners": "SEA", "Marlins": "MIA", "Mets": "NYM", "Nationals": "WSH",
    "Orioles": "BAL", "Padres": "SD", "Phillies": "PHI", "Pirates": "PIT",
    "Rangers": "TEX", "Rays": "TB", "Red Sox": "BOS", "Reds": "CIN",
    "Rockies": "COL", "Royals": "KC", "Tigers": "DET", "Twins": "MIN",
    "White Sox": "CWS", "Yankees": "NYY",
}
ALL_TEAMS = sorted({
    "ATH", "ATL", "AZ", "BAL", "BOS", "CHC", "CIN", "CLE", "COL", "CWS",
    "DET", "HOU", "KC", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY",
    "PHI", "PIT", "SD", "SEA", "SF", "STL", "TB", "TEX", "TOR", "WSH",
})

# ---------------------------------------------------------------------------
# ELO math
# ---------------------------------------------------------------------------

def expected_score(elo_a, elo_b, hfa=0.0):
    return 1.0 / (1.0 + 10.0 ** ((elo_b - (elo_a + hfa)) / 400.0))

def mov_mult(score_diff, elo_diff):
    return math.log(abs(score_diff) + 1) * (MOV_MULTIPLIER / (0.001 * abs(elo_diff) + MOV_MULTIPLIER))

# ---------------------------------------------------------------------------
# Preseason ELO generation (all modes)
# ---------------------------------------------------------------------------

_ACQUIRED_RE = re.compile(r"Acquired from ([\w\s]+?) (?:for|with|as|\()", re.IGNORECASE)

def load_elo_baseline(season):
    path = os.path.join(MODEL_DIR, f"elo_rating_end_of_{season - 1}.csv")
    df = pd.read_csv(path)
    return {row["team"]: float(row["elo"]) for _, row in df.iterrows()}

def load_team_war(season):
    war_file = TEAM_WAR_FILE.get(season)
    if not war_file:
        return None
    path = os.path.join(MODEL_DIR, war_file)
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    return {row["team"]: float(row["total_war"]) for _, row in df.iterrows()}

def load_transaction_war(season):
    war_col = WAR_COLUMN.get(season)
    if not war_col:
        return {}, {}

    adds_path = os.path.join(MODEL_DIR, f"fwar-additions-{season}.csv")
    subs_path = os.path.join(MODEL_DIR, f"fwar-subtractions-{season}.csv")

    if not os.path.exists(adds_path) or not os.path.exists(subs_path):
        return {}, {}

    adds_raw = pd.read_csv(adds_path, encoding="utf-8-sig")
    adds_raw["team"] = adds_raw["Team"].map(lambda t: FG_TO_CANONICAL.get(t, t))
    adds_raw["war"] = pd.to_numeric(adds_raw[war_col], errors="coerce").fillna(0).clip(upper=MAX_PLAYER_WAR)

    subs_raw = pd.read_csv(subs_path, encoding="utf-8-sig")
    subs_raw["team"] = subs_raw["Team"].map(lambda t: FG_TO_CANONICAL.get(t, t))
    subs_raw["war"] = pd.to_numeric(subs_raw[war_col], errors="coerce").fillna(0).clip(upper=MAX_PLAYER_WAR)

    # Extract trade departures
    trade_subs = []
    for _, row in adds_raw.iterrows():
        details = row.get("Transaction Details", "")
        if not isinstance(details, str):
            continue
        m = _ACQUIRED_RE.search(details)
        if not m:
            continue
        nickname = m.group(1).strip()
        from_team = NICKNAME_TO_CANONICAL.get(nickname)
        if not from_team:
            continue
        war_val = pd.to_numeric(row.get(war_col, 0), errors="coerce")
        if pd.isna(war_val):
            war_val = 0.0
        war_val = min(war_val, MAX_PLAYER_WAR)
        trade_subs.append({"team": from_team, "war": war_val})

    if trade_subs:
        trade_df = pd.DataFrame(trade_subs)
        subs_combined = pd.concat([subs_raw[["team", "war"]], trade_df[["team", "war"]]], ignore_index=True)
    else:
        subs_combined = subs_raw[["team", "war"]]

    add_war = adds_raw.groupby("team")["war"].sum().to_dict()
    sub_war = subs_combined.groupby("team")["war"].sum().to_dict()
    return add_war, sub_war


def generate_preseason_elo(season, mode):
    """Generate preseason ELOs for a given mode. Returns dict {team: elo}."""
    elo_baseline = load_elo_baseline(season)

    if mode == "none":
        # Pure mean reversion, no WAR at all
        result = {}
        for team in ALL_TEAMS:
            elo_end = elo_baseline.get(team, MEAN_ELO)
            result[team] = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO
        # Apply spread compression
        mean_elo = sum(result.values()) / len(result)
        for team in result:
            result[team] = mean_elo + SPREAD_COMPRESSION * (result[team] - mean_elo)
        return result

    if mode == "transactions":
        add_war, sub_war = load_transaction_war(season)
        records = {}
        for team in ALL_TEAMS:
            elo_end = elo_baseline.get(team, MEAN_ELO)
            mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO
            net = add_war.get(team, 0) - sub_war.get(team, 0)
            records[team] = mean_reverted + net * WAR_TO_ELO
        mean_elo = sum(records.values()) / len(records)
        for team in records:
            records[team] = mean_elo + SPREAD_COMPRESSION * (records[team] - mean_elo)
        return records

    if mode == "team-totals":
        team_war = load_team_war(season)
        if not team_war:
            return generate_preseason_elo(season, "none")
        league_avg = sum(team_war.values()) / len(team_war)
        records = {}
        for team in ALL_TEAMS:
            elo_end = elo_baseline.get(team, MEAN_ELO)
            mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO
            tw = team_war.get(team, league_avg)
            war_elo = MEAN_ELO + (tw - league_avg) * WAR_ELO_FACTOR
            records[team] = WAR_WEIGHT * war_elo + (1 - WAR_WEIGHT) * mean_reverted
        mean_elo = sum(records.values()) / len(records)
        for team in records:
            records[team] = mean_elo + SPREAD_COMPRESSION * (records[team] - mean_elo)
        return records

    if mode == "hybrid":
        team_war = load_team_war(season)
        if not team_war:
            return generate_preseason_elo(season, "transactions")
        add_war, sub_war = load_transaction_war(season)
        base_avg = sum(team_war.values()) / len(team_war)

        adjusted = {}
        for team in ALL_TEAMS:
            base = team_war.get(team, base_avg)
            net_txn = add_war.get(team, 0) - sub_war.get(team, 0)
            adjusted[team] = base + net_txn
        adj_avg = sum(adjusted.values()) / len(adjusted)

        records = {}
        for team in ALL_TEAMS:
            elo_end = elo_baseline.get(team, MEAN_ELO)
            mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO
            war_elo = MEAN_ELO + (adjusted[team] - adj_avg) * WAR_ELO_FACTOR
            records[team] = WAR_WEIGHT * war_elo + (1 - WAR_WEIGHT) * mean_reverted
        mean_elo = sum(records.values()) / len(records)
        for team in records:
            records[team] = mean_elo + SPREAD_COMPRESSION * (records[team] - mean_elo)
        return records

    raise ValueError(f"Unknown mode: {mode}")


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def load_schedule(season):
    path = os.path.join(MODEL_DIR, f"schedule_{season}_full.csv")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    completed = df[df["status"] == "Final"].copy()
    completed = completed.sort_values("date").reset_index(drop=True)
    return completed


def backtest_season(schedule, preseason_elo, fade_games):
    """
    Replay a season and compute prediction metrics.

    For each game:
      1. Compute regressed ELO: pct * raw + (1-pct) * preseason
      2. Predict using regressed ELO
      3. Update raw ELO using K=6

    Args:
        fade_games: Number of games at which preseason influence = 0.
                    0 = no preseason influence (pure ELO).
                    999 = preseason always active.
    """
    raw_elo = dict(preseason_elo)  # Start from preseason
    games_played = defaultdict(int)

    predictions = []  # (p_home, actual_home_win, home, away)
    team_pred_wins = defaultdict(float)
    team_actual_wins = defaultdict(int)
    team_actual_losses = defaultdict(int)

    for _, row in schedule.iterrows():
        home = row["homeTeam"]
        away = row["awayTeam"]
        h_score = row["homeScore"]
        a_score = row["awayScore"]

        if home not in raw_elo or away not in raw_elo:
            continue

        # Compute regressed ELO for prediction
        if fade_games > 0:
            gp_home = games_played[home]
            gp_away = games_played[away]
            gp_avg = (gp_home + gp_away) / 2.0
            pct = min(gp_avg / fade_games, 1.0)
            reg_home = pct * raw_elo[home] + (1 - pct) * preseason_elo[home]
            reg_away = pct * raw_elo[away] + (1 - pct) * preseason_elo[away]
        else:
            # No preseason influence
            reg_home = raw_elo[home]
            reg_away = raw_elo[away]

        # Predict
        p_home = expected_score(reg_home, reg_away, hfa=HFA)
        actual_h = 1.0 if h_score > a_score else 0.0
        predictions.append((p_home, actual_h, home, away))

        # Track predicted and actual wins
        team_pred_wins[home] += p_home
        team_pred_wins[away] += (1 - p_home)
        if h_score > a_score:
            team_actual_wins[home] += 1
            team_actual_losses[away] += 1
        else:
            team_actual_wins[away] += 1
            team_actual_losses[home] += 1

        # Update raw ELO (using raw ELO, not regressed)
        exp_h = expected_score(raw_elo[home], raw_elo[away], hfa=HFA)
        score_diff = abs(h_score - a_score)
        elo_diff = raw_elo[home] + HFA - raw_elo[away]
        m = mov_mult(score_diff, elo_diff)
        shift = K * m * (actual_h - exp_h)
        raw_elo[home] += shift
        raw_elo[away] -= shift

        games_played[home] += 1
        games_played[away] += 1

    # Compute metrics
    n = len(predictions)
    if n == 0:
        return None

    preds = np.array([(p, a) for p, a, _, _ in predictions])
    p = preds[:, 0]
    a = preds[:, 1]

    brier = np.mean((p - a) ** 2)
    # Log loss (clip to avoid log(0))
    p_clipped = np.clip(p, 1e-6, 1 - 1e-6)
    logloss = -np.mean(a * np.log(p_clipped) + (1 - a) * np.log(1 - p_clipped))
    # Accuracy (did the favorite win?)
    correct = np.sum(((p > 0.5) & (a == 1)) | ((p < 0.5) & (a == 0)))
    accuracy = 100.0 * correct / n

    # Win prediction RMSE
    win_errors = []
    for team in ALL_TEAMS:
        if team in team_actual_wins:
            pred_w = team_pred_wins.get(team, 0)
            actual_w = team_actual_wins.get(team, 0)
            win_errors.append((pred_w - actual_w) ** 2)
    win_rmse = math.sqrt(np.mean(win_errors)) if win_errors else 0

    # Early-season metrics (first 40 games per team ≈ first ~650 games)
    early_cutoff = 650
    early_p = preds[:early_cutoff, 0]
    early_a = preds[:early_cutoff, 1]
    early_brier = np.mean((early_p - early_a) ** 2) if len(early_p) > 0 else 0
    early_correct = np.sum(((early_p > 0.5) & (early_a == 1)) | ((early_p < 0.5) & (early_a == 0)))
    early_accuracy = 100.0 * early_correct / len(early_p) if len(early_p) > 0 else 0

    # Late-season metrics (last 650 games)
    late_p = preds[-650:, 0]
    late_a = preds[-650:, 1]
    late_brier = np.mean((late_p - late_a) ** 2) if len(late_p) > 0 else 0

    return {
        "n_games": n,
        "brier": brier,
        "logloss": logloss,
        "accuracy": accuracy,
        "win_rmse": win_rmse,
        "early_brier": early_brier,
        "early_accuracy": early_accuracy,
        "late_brier": late_brier,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    war_modes = ["none", "transactions", "team-totals", "hybrid"]
    fade_values = [0, 40, 60, 80, 100, 120, 162, 200, 300]
    seasons = [2024, 2025]

    # Load schedules
    schedules = {}
    for season in seasons:
        schedules[season] = load_schedule(season)
        print(f"Loaded {len(schedules[season])} games for {season}")

    # Run backtests
    results = []
    for mode in war_modes:
        for season in seasons:
            preseason = generate_preseason_elo(season, mode)
            for fade in fade_values:
                # Skip fade>0 for "none" mode with fade=0 is the pure ELO baseline
                # For "none" mode, only test a few fade values since there's no WAR
                if mode == "none" and fade > 0:
                    # For the "none" mode (mean reversion only, no WAR),
                    # still test fade curves since preseason ELO carries mean reversion info
                    pass

                metrics = backtest_season(schedules[season], preseason, fade)
                if metrics:
                    results.append({
                        "mode": mode,
                        "season": season,
                        "fade_games": fade,
                        **metrics,
                    })

    # --- Print results ---
    print(f"\n{'='*110}")
    print(f"  BACKTEST RESULTS — Game Prediction Accuracy")
    print(f"{'='*110}")

    # Group by mode and fade, average across seasons
    print(f"\n  {'Mode':<14} {'Fade':>6} {'Brier':>8} {'LogLoss':>9} {'Acc%':>7} "
          f"{'WinRMSE':>9} {'Early Br':>10} {'Early Acc':>10} {'Late Br':>9}")
    print(f"  {'-'*14} {'-'*6} {'-'*8} {'-'*9} {'-'*7} "
          f"{'-'*9} {'-'*10} {'-'*10} {'-'*9}")

    # Sort by Brier score (averaged across seasons)
    from itertools import groupby as igroupby

    # Compute averages
    avg_results = []
    for mode in war_modes:
        for fade in fade_values:
            matching = [r for r in results if r["mode"] == mode and r["fade_games"] == fade]
            if not matching:
                continue
            avg = {
                "mode": mode,
                "fade_games": fade,
                "brier": np.mean([r["brier"] for r in matching]),
                "logloss": np.mean([r["logloss"] for r in matching]),
                "accuracy": np.mean([r["accuracy"] for r in matching]),
                "win_rmse": np.mean([r["win_rmse"] for r in matching]),
                "early_brier": np.mean([r["early_brier"] for r in matching]),
                "early_accuracy": np.mean([r["early_accuracy"] for r in matching]),
                "late_brier": np.mean([r["late_brier"] for r in matching]),
            }
            avg_results.append(avg)

    avg_results.sort(key=lambda x: x["brier"])

    for r in avg_results:
        marker = " <-- BEST" if r == avg_results[0] else ""
        print(
            f"  {r['mode']:<14} {r['fade_games']:>6} {r['brier']:>8.5f} "
            f"{r['logloss']:>9.5f} {r['accuracy']:>6.1f}% "
            f"{r['win_rmse']:>9.2f} {r['early_brier']:>10.5f} "
            f"{r['early_accuracy']:>9.1f}% {r['late_brier']:>9.5f}{marker}"
        )

    # --- Best per mode ---
    print(f"\n{'='*80}")
    print(f"  BEST FADE CURVE PER MODE (by overall Brier score)")
    print(f"{'='*80}")
    for mode in war_modes:
        mode_results = [r for r in avg_results if r["mode"] == mode]
        if mode_results:
            best = min(mode_results, key=lambda x: x["brier"])
            print(f"  {mode:<14} fade={best['fade_games']:<4} Brier={best['brier']:.5f}  "
                  f"Acc={best['accuracy']:.1f}%  WinRMSE={best['win_rmse']:.2f}")

    # --- Best per mode for early season ---
    print(f"\n{'='*80}")
    print(f"  BEST FADE CURVE PER MODE (by early-season Brier, first ~650 games)")
    print(f"{'='*80}")
    for mode in war_modes:
        mode_results = [r for r in avg_results if r["mode"] == mode]
        if mode_results:
            best = min(mode_results, key=lambda x: x["early_brier"])
            print(f"  {mode:<14} fade={best['fade_games']:<4} Early Brier={best['early_brier']:.5f}  "
                  f"Early Acc={best['early_accuracy']:.1f}%")

    # --- Per-season breakdown for best configs ---
    print(f"\n{'='*80}")
    print(f"  PER-SEASON BREAKDOWN (top 5 configs by Brier)")
    print(f"{'='*80}")
    top5 = avg_results[:5]
    for r in top5:
        print(f"\n  {r['mode']} fade={r['fade_games']}:")
        for season in seasons:
            sr = [x for x in results if x["mode"] == r["mode"]
                  and x["fade_games"] == r["fade_games"] and x["season"] == season]
            if sr:
                s = sr[0]
                print(f"    {season}: Brier={s['brier']:.5f}  Acc={s['accuracy']:.1f}%  "
                      f"WinRMSE={s['win_rmse']:.2f}  Early={s['early_brier']:.5f}  "
                      f"Late={s['late_brier']:.5f}")

    # --- Fade curve analysis for best mode ---
    best_mode = avg_results[0]["mode"]
    print(f"\n{'='*80}")
    print(f"  FADE CURVE ANALYSIS — {best_mode.upper()} mode")
    print(f"{'='*80}")
    print(f"  {'Fade':>6} {'Overall Brier':>15} {'Early Brier':>13} {'Late Brier':>12} {'Win RMSE':>10}")
    mode_by_fade = sorted(
        [r for r in avg_results if r["mode"] == best_mode],
        key=lambda x: x["fade_games"]
    )
    for r in mode_by_fade:
        print(f"  {r['fade_games']:>6} {r['brier']:>15.5f} {r['early_brier']:>13.5f} "
              f"{r['late_brier']:>12.5f} {r['win_rmse']:>10.2f}")


if __name__ == "__main__":
    main()
