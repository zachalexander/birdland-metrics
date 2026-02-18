#!/usr/bin/env python3
"""
generate-preseason-elo.py — Generate preseason ELO ratings with mean reversion
and WAR-based adjustments.

Three WAR source modes:

  hybrid (default for backfill):
    Combines prior-year team WAR totals with offseason transaction adjustments.
    adjusted_war = prior_year_team_war + net_transaction_war
    Best for historical backfill where projected WAR isn't available.

  team-totals (default for current season):
    Loads team-level WAR totals (projected or actual) and blends a WAR-derived
    ELO signal with mean-reverted prior-season ELO.
    - 2026: team_war_2026_projected.csv  (FanGraphs projected WAR)

  transactions (legacy):
    Uses FanGraphs fWAR addition/subtraction CSVs to compute net offseason
    WAR changes per team. Individual player WAR capped at 5.0.

All modes apply 40% mean reversion, blending, and 0.75 spread compression.

Usage:
  python3 generate-preseason-elo.py --season 2024 --war-source hybrid
  python3 generate-preseason-elo.py --season 2025 --war-source hybrid
  python3 generate-preseason-elo.py --season 2026  # defaults to team-totals
"""

import argparse
import os
import re
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "model-2026-updates")

# ---------------------------------------------------------------------------
# Team code normalization (FanGraphs → project canonical)
# ---------------------------------------------------------------------------
FG_TO_CANONICAL = {
    "ARI": "AZ",
    "CHW": "CWS",
    "KCR": "KC",
    "SDP": "SD",
    "SFG": "SF",
    "TBR": "TB",
    "WSN": "WSH",
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
# Model parameters
# ---------------------------------------------------------------------------

MEAN_ELO = 1500

# Mean reversion: regress 40% toward 1500
REVERSION_FRACTION = 0.4

# Compress spread toward the mean after blending
SPREAD_COMPRESSION = 0.75

# --- Team-totals mode ---
# Team WAR CSV file per season
TEAM_WAR_FILE = {
    2024: "team_war_2023.csv",         # Actual 2023 team WAR
    2025: "team_war_2024.csv",         # Actual 2024 team WAR
    2026: "team_war_2026_projected.csv",  # FanGraphs projected 2026 WAR
}

# ELO points per WAR above/below league average (team-totals mode)
WAR_ELO_FACTOR = 5.0

# Blend weight: how much of preseason ELO comes from WAR signal vs ELO history
# 0.5 = equal weight; higher = more WAR influence
WAR_WEIGHT = 0.5

# --- Transactions mode (legacy) ---
WAR_TO_ELO = 5.5
MAX_PLAYER_WAR = 5.0
WAR_COLUMN = {
    2024: "2023 WAR",
    2025: "2024 WAR",
    2026: "2025 WAR",
}

# ---------------------------------------------------------------------------
# Trade departure extraction (transactions mode only)
# ---------------------------------------------------------------------------
_ACQUIRED_RE = re.compile(r"Acquired from ([\w\s]+?) (?:for|with|as|\()", re.IGNORECASE)


def extract_trade_departures(adds: pd.DataFrame, war_col: str) -> pd.DataFrame:
    trade_subs = []
    for _, row in adds.iterrows():
        details = row.get("Transaction Details", "")
        if not isinstance(details, str):
            continue
        m = _ACQUIRED_RE.search(details)
        if not m:
            continue
        nickname = m.group(1).strip()
        from_team = NICKNAME_TO_CANONICAL.get(nickname)
        if not from_team:
            print(f'  WARNING: Unknown trade team nickname: "{nickname}"')
            continue
        war_val = pd.to_numeric(row.get(war_col, 0), errors="coerce")
        if pd.isna(war_val):
            war_val = 0.0
        war_val = min(war_val, MAX_PLAYER_WAR)
        trade_subs.append({
            "team": from_team,
            "Name": row["Name"],
            "war": war_val,
            "Transaction Details": f'Traded to {row["team"]}',
        })

    if trade_subs:
        df = pd.DataFrame(trade_subs)
        print(f"  Extracted {len(df)} trade departures from additions file")
        return df
    return pd.DataFrame(columns=["team", "Name", "war", "Transaction Details"])


# ---------------------------------------------------------------------------
# Team-totals mode
# ---------------------------------------------------------------------------

def generate_team_totals(season: int, elo_baseline: dict[str, float]) -> pd.DataFrame:
    """Generate preseason ELO by blending mean-reverted ELO with WAR-based ELO."""

    war_file = TEAM_WAR_FILE.get(season)
    if not war_file:
        print(f"ERROR: No team WAR file mapping for season {season}", file=sys.stderr)
        sys.exit(1)

    war_path = os.path.join(MODEL_DIR, war_file)
    if not os.path.exists(war_path):
        print(f"ERROR: Team WAR file not found: {war_path}", file=sys.stderr)
        sys.exit(1)

    war_df = pd.read_csv(war_path)
    team_war = {row["team"]: float(row["total_war"]) for _, row in war_df.iterrows()}
    league_avg_war = sum(team_war.values()) / len(team_war)
    print(f"Loaded {len(team_war)} team WARs from {war_file} (league avg: {league_avg_war:.1f})")

    records = []
    for team in ALL_TEAMS:
        elo_end = elo_baseline.get(team, MEAN_ELO)

        # Mean reversion
        mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO

        # WAR-based ELO signal
        tw = team_war.get(team, league_avg_war)
        war_vs_avg = tw - league_avg_war
        war_elo = MEAN_ELO + war_vs_avg * WAR_ELO_FACTOR

        # Blend
        preseason = WAR_WEIGHT * war_elo + (1 - WAR_WEIGHT) * mean_reverted

        records.append({
            "team": team,
            "elo_end_of_season": round(elo_end, 2),
            "mean_reverted_elo": round(mean_reverted, 2),
            "total_war": round(tw, 1),
            "war_vs_avg": round(war_vs_avg, 1),
            "war_elo": round(war_elo, 2),
            "preseason_elo": round(preseason, 2),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Transaction loading (shared by transactions and hybrid modes)
# ---------------------------------------------------------------------------

def load_transaction_war(season: int) -> tuple[pd.Series, pd.Series]:
    """Load additions/subtractions CSVs and return (add_war, sub_war) per team."""

    war_col = WAR_COLUMN.get(season)
    if not war_col:
        print(f"ERROR: No WAR column mapping for season {season}", file=sys.stderr)
        sys.exit(1)

    # Load additions
    adds_path = os.path.join(MODEL_DIR, f"fwar-additions-{season}.csv")
    if not os.path.exists(adds_path):
        print(f"ERROR: Additions CSV not found: {adds_path}", file=sys.stderr)
        sys.exit(1)
    adds_raw = pd.read_csv(adds_path, encoding="utf-8-sig")
    adds_raw["team"] = adds_raw["Team"].map(lambda t: FG_TO_CANONICAL.get(t, t))
    adds_raw["war"] = pd.to_numeric(adds_raw[war_col], errors="coerce").fillna(0).clip(upper=MAX_PLAYER_WAR)
    print(f"Loaded {len(adds_raw)} addition rows from {os.path.basename(adds_path)}")

    # Load subtractions
    subs_path = os.path.join(MODEL_DIR, f"fwar-subtractions-{season}.csv")
    if not os.path.exists(subs_path):
        print(f"ERROR: Subtractions CSV not found: {subs_path}", file=sys.stderr)
        sys.exit(1)
    subs_raw = pd.read_csv(subs_path, encoding="utf-8-sig")
    subs_raw["team"] = subs_raw["Team"].map(lambda t: FG_TO_CANONICAL.get(t, t))
    subs_raw["war"] = pd.to_numeric(subs_raw[war_col], errors="coerce").fillna(0).clip(upper=MAX_PLAYER_WAR)
    print(f"Loaded {len(subs_raw)} subtraction rows from {os.path.basename(subs_path)}")

    # Extract trade departures
    print("Extracting trade departures...")
    trade_subs = extract_trade_departures(adds_raw, war_col)
    subs_all = pd.concat([subs_raw[["team", "Name", "war"]], trade_subs[["team", "Name", "war"]]], ignore_index=True)
    print(f"  {len(subs_all)} total subtraction rows (including trade departures)")

    add_war = adds_raw.groupby("team")["war"].sum()
    sub_war = subs_all.groupby("team")["war"].sum()
    return add_war, sub_war


# ---------------------------------------------------------------------------
# Hybrid mode (prior-year WAR + transaction adjustments)
# ---------------------------------------------------------------------------

def generate_hybrid(season: int, elo_baseline: dict[str, float]) -> pd.DataFrame:
    """
    Generate preseason ELO by combining prior-year team WAR totals with
    offseason transaction adjustments, then blending with mean-reverted ELO.

    adjusted_war = prior_year_team_war + (additions_war - subtractions_war)
    """

    # Load prior-year team WAR
    war_file = TEAM_WAR_FILE.get(season)
    if not war_file:
        print(f"ERROR: No team WAR file mapping for season {season}", file=sys.stderr)
        sys.exit(1)

    war_path = os.path.join(MODEL_DIR, war_file)
    if not os.path.exists(war_path):
        print(f"ERROR: Team WAR file not found: {war_path}", file=sys.stderr)
        sys.exit(1)

    war_df = pd.read_csv(war_path)
    team_war = {row["team"]: float(row["total_war"]) for _, row in war_df.iterrows()}
    base_avg = sum(team_war.values()) / len(team_war)
    print(f"Loaded {len(team_war)} team WARs from {war_file} (base avg: {base_avg:.1f})")

    # Load transaction WAR
    add_war, sub_war = load_transaction_war(season)

    # Compute adjusted WAR per team
    adjusted_war = {}
    for team in ALL_TEAMS:
        base = team_war.get(team, base_avg)
        gained = add_war.get(team, 0)
        lost = sub_war.get(team, 0)
        net_txn = gained - lost
        adjusted_war[team] = base + net_txn

    adj_avg = sum(adjusted_war.values()) / len(adjusted_war)
    print(f"  Adjusted WAR avg: {adj_avg:.1f}")

    records = []
    for team in ALL_TEAMS:
        elo_end = elo_baseline.get(team, MEAN_ELO)

        # Mean reversion
        mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO

        # WAR-based ELO signal (using adjusted WAR)
        aw = adjusted_war[team]
        base = team_war.get(team, base_avg)
        net_txn = round(aw - base, 1)
        war_vs_avg = aw - adj_avg
        war_elo = MEAN_ELO + war_vs_avg * WAR_ELO_FACTOR

        # Blend
        preseason = WAR_WEIGHT * war_elo + (1 - WAR_WEIGHT) * mean_reverted

        records.append({
            "team": team,
            "elo_end_of_season": round(elo_end, 2),
            "mean_reverted_elo": round(mean_reverted, 2),
            "base_war": round(base, 1),
            "net_txn_war": net_txn,
            "adjusted_war": round(aw, 1),
            "war_vs_avg": round(war_vs_avg, 1),
            "war_elo": round(war_elo, 2),
            "preseason_elo": round(preseason, 2),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Transactions mode (legacy)
# ---------------------------------------------------------------------------

def generate_transactions(season: int, elo_baseline: dict[str, float]) -> pd.DataFrame:
    """Generate preseason ELO using offseason transaction WAR deltas."""

    add_war, sub_war = load_transaction_war(season)

    records = []
    for team in ALL_TEAMS:
        elo_end = elo_baseline.get(team, MEAN_ELO)
        mean_reverted = (1 - REVERSION_FRACTION) * elo_end + REVERSION_FRACTION * MEAN_ELO

        gained = add_war.get(team, 0)
        lost = sub_war.get(team, 0)
        net_war = round(gained - lost, 1)
        elo_adj = round(net_war * WAR_TO_ELO, 1)
        preseason = round(mean_reverted + elo_adj, 2)

        records.append({
            "team": team,
            "elo_end_of_season": round(elo_end, 2),
            "mean_reverted_elo": round(mean_reverted, 2),
            "net_war_change": net_war,
            "elo_adjustment": elo_adj,
            "preseason_elo": preseason,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate preseason ELO with mean reversion + WAR adjustments"
    )
    parser.add_argument(
        "--season", type=int, required=True,
        help="Season year (e.g. 2024, 2025, 2026)"
    )
    parser.add_argument(
        "--war-source", choices=["hybrid", "team-totals", "transactions"],
        default=None,
        help="WAR data source: hybrid (team WAR + transactions), "
             "team-totals (projected/actual WAR only), or transactions (legacy)"
    )
    args = parser.parse_args()
    season = args.season
    # Default: hybrid for backfill seasons (2024/2025), team-totals for 2026+
    war_source = args.war_source or ("team-totals" if season >= 2026 else "hybrid")

    # --- Load ELO baseline ---
    elo_path = os.path.join(MODEL_DIR, f"elo_rating_end_of_{season - 1}.csv")
    if not os.path.exists(elo_path):
        print(f"ERROR: ELO baseline not found: {elo_path}", file=sys.stderr)
        sys.exit(1)
    elo_df = pd.read_csv(elo_path)
    elo_baseline = {row["team"]: float(row["elo"]) for _, row in elo_df.iterrows()}
    print(f"Loaded {len(elo_baseline)} team ELOs from {os.path.basename(elo_path)}")

    # --- Generate based on WAR source ---
    print(f"\nUsing WAR source: {war_source}")
    if war_source == "hybrid":
        result_df = generate_hybrid(season, elo_baseline)
    elif war_source == "team-totals":
        result_df = generate_team_totals(season, elo_baseline)
    else:
        result_df = generate_transactions(season, elo_baseline)

    # --- Compress spread toward mean ---
    mean_elo = result_df["preseason_elo"].mean()
    result_df["preseason_elo"] = round(
        mean_elo + SPREAD_COMPRESSION * (result_df["preseason_elo"] - mean_elo), 2
    )

    result_df = result_df.sort_values("preseason_elo", ascending=False)

    # --- Print summary ---
    print(f"\n{'='*80}")
    print(f"  PRESEASON ELO {season} — {war_source.upper()} mode")
    war_w = WAR_WEIGHT if war_source in ('team-totals', 'hybrid') else 'N/A'
    print(f"  Mean reversion: {REVERSION_FRACTION:.0%} | "
          f"Spread compression: {SPREAD_COMPRESSION} | "
          f"WAR weight: {war_w}")
    print(f"{'='*80}")

    if war_source == "hybrid":
        print(f"  {'Team':<6} {'End ELO':>10} {'Reverted':>10} {'Base':>7} {'Txn':>6} "
              f"{'Adj WAR':>8} {'vs Avg':>8} {'Preseason':>11}")
        print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*7} {'-'*6} "
              f"{'-'*8} {'-'*8} {'-'*11}")
        for _, row in result_df.iterrows():
            print(
                f"  {row['team']:<6} {row['elo_end_of_season']:>10.2f} "
                f"{row['mean_reverted_elo']:>10.2f} {row['base_war']:>7.1f} "
                f"{row['net_txn_war']:>+6.1f} {row['adjusted_war']:>8.1f} "
                f"{row['war_vs_avg']:>+8.1f} {row['preseason_elo']:>11.2f}"
            )
    elif war_source == "team-totals":
        print(f"  {'Team':<6} {'End ELO':>10} {'Reverted':>10} {'WAR':>7} {'vs Avg':>8} "
              f"{'WAR ELO':>9} {'Preseason':>11}")
        print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*7} {'-'*8} {'-'*9} {'-'*11}")
        for _, row in result_df.iterrows():
            print(
                f"  {row['team']:<6} {row['elo_end_of_season']:>10.2f} "
                f"{row['mean_reverted_elo']:>10.2f} {row['total_war']:>7.1f} "
                f"{row['war_vs_avg']:>+8.1f} {row['war_elo']:>9.2f} "
                f"{row['preseason_elo']:>11.2f}"
            )
    else:
        print(f"  {'Team':<6} {'End ELO':>10} {'Reverted':>10} {'Net WAR':>9} "
              f"{'Adj':>8} {'Preseason':>11}")
        print(f"  {'-'*6} {'-'*10} {'-'*10} {'-'*9} {'-'*8} {'-'*11}")
        for _, row in result_df.iterrows():
            print(
                f"  {row['team']:<6} {row['elo_end_of_season']:>10.2f} "
                f"{row['mean_reverted_elo']:>10.2f} {row['net_war_change']:>+9.1f} "
                f"{row['elo_adjustment']:>+8.1f} {row['preseason_elo']:>11.2f}"
            )

    elos = result_df["preseason_elo"]
    print(f"\n  ELO spread: {elos.max() - elos.min():.0f} points "
          f"(was {max(elo_baseline.values()) - min(elo_baseline.values()):.0f} before adjustments)")

    # --- Save output ---
    output_path = os.path.join(MODEL_DIR, f"preseason_elo_{season}.csv")
    result_df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
