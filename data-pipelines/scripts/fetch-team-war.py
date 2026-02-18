#!/usr/bin/env python3
"""
fetch-team-war.py
-----------------
Fetches team-level WAR totals (batting + pitching) from FanGraphs via pybaseball
for the 2023 and 2024 MLB seasons.

Outputs CSV files to model-2026-updates/ with columns:
  team, batting_war, pitching_war, total_war
"""

import os
import pandas as pd
from pybaseball import batting_stats, pitching_stats

# --- Configuration -----------------------------------------------------------

SEASONS = [2023, 2024]

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "model-2026-updates"
)

# FanGraphs abbreviation -> canonical abbreviation
TEAM_RENAME = {
    "ARI": "AZ",
    "CHW": "CWS",
    "KCR": "KC",
    "SDP": "SD",
    "SFG": "SF",
    "TBR": "TB",
    "WSN": "WSH",
    "OAK": "ATH",
}

# All 30 canonical team codes (for validation)
ALL_TEAMS = sorted([
    "AZ", "ATL", "BAL", "BOS", "CHC", "CWS", "CIN", "CLE", "COL", "DET",
    "HOU", "KC", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY", "ATH",
    "PHI", "PIT", "SD", "SEA", "SF", "STL", "TB", "TEX", "TOR", "WSH",
])


def fetch_team_war(season: int) -> pd.DataFrame:
    """Fetch batting and pitching WAR, aggregate by team, return merged DataFrame."""

    print(f"\n{'='*60}")
    print(f"Fetching data for {season} season...")
    print(f"{'='*60}")

    # --- Batting WAR ---------------------------------------------------------
    print(f"  Fetching batting stats (qual=0)...")
    bat = batting_stats(season, qual=0)
    # Exclude multi-team summary rows
    bat = bat[bat["Team"] != "- - -"].copy()
    bat["Team"] = bat["Team"].replace(TEAM_RENAME)

    batting_war = (
        bat.groupby("Team")["WAR"]
        .sum()
        .round(1)
        .reset_index()
        .rename(columns={"WAR": "batting_war", "Team": "team"})
    )
    print(f"  -> {len(batting_war)} teams found in batting data")

    # --- Pitching WAR --------------------------------------------------------
    print(f"  Fetching pitching stats (qual=0)...")
    pit = pitching_stats(season, qual=0)
    pit = pit[pit["Team"] != "- - -"].copy()
    pit["Team"] = pit["Team"].replace(TEAM_RENAME)

    pitching_war = (
        pit.groupby("Team")["WAR"]
        .sum()
        .round(1)
        .reset_index()
        .rename(columns={"WAR": "pitching_war", "Team": "team"})
    )
    print(f"  -> {len(pitching_war)} teams found in pitching data")

    # --- Merge ---------------------------------------------------------------
    merged = pd.merge(batting_war, pitching_war, on="team", how="outer")
    merged["batting_war"] = merged["batting_war"].fillna(0.0)
    merged["pitching_war"] = merged["pitching_war"].fillna(0.0)
    merged["total_war"] = (merged["batting_war"] + merged["pitching_war"]).round(1)
    merged = merged.sort_values("total_war", ascending=False).reset_index(drop=True)

    # --- Validation ----------------------------------------------------------
    missing = set(ALL_TEAMS) - set(merged["team"])
    extra = set(merged["team"]) - set(ALL_TEAMS)
    if missing:
        print(f"  WARNING: Missing teams: {missing}")
    if extra:
        print(f"  WARNING: Unexpected teams: {extra}")
    assert len(merged) == 30, f"Expected 30 teams, got {len(merged)}"

    return merged


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for season in SEASONS:
        df = fetch_team_war(season)

        outpath = os.path.join(OUTPUT_DIR, f"team_war_{season}.csv")
        df.to_csv(outpath, index=False)
        print(f"\n  Saved: {outpath}")

        # Pretty-print the table
        print(f"\n  {'Rank':<5} {'Team':<6} {'Bat WAR':>8} {'Pit WAR':>8} {'Total':>8}")
        print(f"  {'-'*5} {'-'*6} {'-'*8} {'-'*8} {'-'*8}")
        for i, row in df.iterrows():
            print(
                f"  {i+1:<5} {row['team']:<6} {row['batting_war']:>8.1f} "
                f"{row['pitching_war']:>8.1f} {row['total_war']:>8.1f}"
            )

    print(f"\nDone. Files written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
