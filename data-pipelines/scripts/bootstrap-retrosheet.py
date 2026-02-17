#!/usr/bin/env python3
"""
Bootstrap script for Retrosheet historical player stats.

Downloads Retrosheet event files, processes them with Chadwick CLI tools
(cwdaily), and produces per-game and season-aggregate CSVs for Orioles
(or any team). Optionally uploads to S3.

Requirements:
  - Chadwick tools installed (cwdaily on PATH)
  - Python 3.10+
  - pip install pandas boto3 requests

Usage:
  python bootstrap-retrosheet.py --years 2015-2024 --team BAL
  python bootstrap-retrosheet.py --years 2024 --team BAL --upload

The information used here was obtained free of charge from and is copyrighted
by Retrosheet. Interested parties may contact Retrosheet at www.retrosheet.org.
"""

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Add the shared mlb_common layer to the path so we can use stats helpers
# ---------------------------------------------------------------------------
LAYER_PATH = Path(__file__).resolve().parent.parent / "layers" / "mlb-pipeline-common" / "python"
sys.path.insert(0, str(LAYER_PATH))

from mlb_common.stats import (
    batting_avg, obp, slg, ops, woba,
    era, whip, fip, k_per_9, bb_per_9, ip_from_outs,
)
from mlb_common.config import PLAYER_STATS_BUCKET

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RETROSHEET_URL = "https://www.retrosheet.org/events/{year}eve.zip"

# cwdaily field indices we care about (from `cwdaily -d`)
# We request fields with -n for headers, then parse by column name.
CWDAILY_BATTING_FIELDS = [
    0, 1, 4, 5,   # game_id, date, team, player_id
    11, 12, 13, 14, 15,  # G, PA, AB, R, H
    17, 18, 19,          # 2B, 3B, HR
    21, 23, 25, 27, 29,  # RBI, BB, SO, HBP, SF
    30, 31,              # SB, CS
]

CWDAILY_PITCHING_FIELDS = [
    0, 1, 4, 5,          # game_id, date, team, player_id
    36, 37,              # P_G, P_GS
    41, 42, 43,          # P_W, P_L, P_SV
    44, 45,              # P_OUT, P_TBF
    47, 48, 49,          # P_R, P_ER, P_H
    53, 55, 57, 59,      # P_HR, P_BB, P_SO, P_HP
]

# All fields we need (union of batting + pitching) — let cwdaily output all default fields
# and we'll parse the columns by name.

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data-pipelines" / "output" / "player-stats"


def parse_year_range(year_str: str) -> list[int]:
    """Parse '2015-2024' or '2024' into a list of years."""
    if "-" in year_str:
        start, end = year_str.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(year_str)]


def download_event_files(year: int, dest_dir: Path) -> Path:
    """Download and extract Retrosheet event files for a given year."""
    url = RETROSHEET_URL.format(year=year)
    print(f"  Downloading {url} ...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    year_dir = dest_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(year_dir)

    return year_dir


def run_cwdaily(year_dir: Path, year: int) -> str:
    """Run cwdaily on event files and return CSV output with headers."""
    ev_files = sorted(year_dir.glob(f"{year}*.EV*"))
    if not ev_files:
        raise FileNotFoundError(f"No event files found in {year_dir} for {year}")

    cmd = ["cwdaily", "-n", "-q", "-y", str(year)] + [str(f) for f in ev_files]
    print(f"  Running cwdaily for {year} ({len(ev_files)} event files) ...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(year_dir))
    if result.returncode != 0:
        print(f"  cwdaily stderr: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"cwdaily failed for {year}")

    return result.stdout


def parse_roster_files(year_dir: Path, team: str) -> dict[str, str]:
    """Parse .ROS roster files to build player_id → display name map."""
    names: dict[str, str] = {}
    ros_files = list(year_dir.glob(f"{team}{year_dir.name}*.ROS")) + list(year_dir.glob(f"*.ROS"))
    for ros_file in ros_files:
        with open(ros_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    player_id = row[0]
                    last_name = row[1]
                    first_name = row[2]
                    names[player_id] = f"{first_name} {last_name}"
    return names


def cwdaily_to_dataframe(csv_text: str) -> pd.DataFrame:
    """Parse cwdaily CSV output into a DataFrame."""
    df = pd.read_csv(io.StringIO(csv_text))
    return df


def extract_batting(df: pd.DataFrame, team: str, names: dict[str, str], year: int) -> pd.DataFrame:
    """Extract per-game batting lines for a team."""
    # Filter to team
    team_df = df[df["TEAM_ID"] == team].copy()
    if team_df.empty:
        return pd.DataFrame()

    # Only include players who had a plate appearance
    team_df = team_df[team_df["B_PA"] > 0].copy()

    # Format date from YYYYMMDD to YYYY-MM-DD
    team_df["date"] = team_df["GAME_ID"].str.extract(r"(\d{8})$", expand=False)
    team_df["date"] = pd.to_datetime(team_df["date"], format="%Y%m%d", errors="coerce")

    batting = pd.DataFrame({
        "player_id": team_df["PLAYER_ID"],
        "name": team_df["PLAYER_ID"].map(names).fillna(team_df["PLAYER_ID"]),
        "team": team,
        "date": team_df["date"].dt.strftime("%Y-%m-%d"),
        "season": year,
        "g": team_df["B_G"],
        "pa": team_df["B_PA"],
        "ab": team_df["B_AB"],
        "r": team_df["B_R"],
        "h": team_df["B_H"],
        "2b": team_df["B_2B"],
        "3b": team_df["B_3B"],
        "hr": team_df["B_HR"],
        "rbi": team_df["B_RBI"],
        "bb": team_df["B_BB"],
        "so": team_df["B_SO"],
        "hbp": team_df["B_HP"],
        "sf": team_df["B_SF"],
        "sb": team_df["B_SB"],
        "cs": team_df["B_CS"],
    })

    return batting.reset_index(drop=True)


def extract_pitching(df: pd.DataFrame, team: str, names: dict[str, str], year: int) -> pd.DataFrame:
    """Extract per-game pitching lines for a team."""
    team_df = df[df["TEAM_ID"] == team].copy()
    if team_df.empty:
        return pd.DataFrame()

    # Only include players who recorded outs as a pitcher
    team_df = team_df[team_df["P_OUT"] > 0].copy()
    if team_df.empty:
        return pd.DataFrame()

    team_df["date"] = team_df["GAME_ID"].str.extract(r"(\d{8})$", expand=False)
    team_df["date"] = pd.to_datetime(team_df["date"], format="%Y%m%d", errors="coerce")

    pitching = pd.DataFrame({
        "player_id": team_df["PLAYER_ID"],
        "name": team_df["PLAYER_ID"].map(names).fillna(team_df["PLAYER_ID"]),
        "team": team,
        "date": team_df["date"].dt.strftime("%Y-%m-%d"),
        "season": year,
        "ip_outs": team_df["P_OUT"],
        "h": team_df["P_H"],
        "r": team_df["P_R"],
        "er": team_df["P_ER"],
        "bb": team_df["P_BB"],
        "so": team_df["P_SO"],
        "hr": team_df["P_HR"],
        "bf": team_df["P_TBF"],
        "hbp": team_df["P_HP"],
        "w": team_df["P_W"],
        "l": team_df["P_L"],
        "sv": team_df["P_SV"],
        "gs": team_df["P_GS"],
    })

    return pitching.reset_index(drop=True)


def aggregate_batting_season(batting_daily: pd.DataFrame, year: int) -> pd.DataFrame:
    """Aggregate per-game batting to season totals with calculated stats."""
    if batting_daily.empty:
        return pd.DataFrame()

    agg = batting_daily.groupby(["player_id", "name", "team"]).agg(
        g=("g", "sum"),
        pa=("pa", "sum"),
        ab=("ab", "sum"),
        r=("r", "sum"),
        h=("h", "sum"),
        doubles=("2b", "sum"),
        triples=("3b", "sum"),
        hr=("hr", "sum"),
        rbi=("rbi", "sum"),
        bb=("bb", "sum"),
        so=("so", "sum"),
        hbp=("hbp", "sum"),
        sf=("sf", "sum"),
        sb=("sb", "sum"),
        cs=("cs", "sum"),
    ).reset_index()

    agg["season"] = year
    agg["avg"] = agg.apply(lambda r: batting_avg(r["h"], r["ab"]), axis=1)
    agg["obp"] = agg.apply(lambda r: obp(r["h"], r["bb"], r["hbp"], r["ab"], r["sf"]), axis=1)
    agg["slg"] = agg.apply(lambda r: slg(r["h"], r["doubles"], r["triples"], r["hr"], r["ab"]), axis=1)
    agg["ops"] = agg.apply(lambda r: ops(r["obp"], r["slg"]), axis=1)
    agg["woba"] = agg.apply(
        lambda r: woba(
            r["bb"], r["hbp"],
            r["h"] - r["doubles"] - r["triples"] - r["hr"],  # singles
            r["doubles"], r["triples"], r["hr"],
            r["ab"], r["sf"]
        ), axis=1
    )

    return agg


def aggregate_pitching_season(pitching_daily: pd.DataFrame, year: int) -> pd.DataFrame:
    """Aggregate per-game pitching to season totals with calculated stats."""
    if pitching_daily.empty:
        return pd.DataFrame()

    agg = pitching_daily.groupby(["player_id", "name", "team"]).agg(
        g=("ip_outs", "count"),
        gs=("gs", "sum"),
        ip_outs=("ip_outs", "sum"),
        h=("h", "sum"),
        r=("r", "sum"),
        er=("er", "sum"),
        bb=("bb", "sum"),
        so=("so", "sum"),
        hr=("hr", "sum"),
        bf=("bf", "sum"),
        hbp=("hbp", "sum"),
        w=("w", "sum"),
        l=("l", "sum"),
        sv=("sv", "sum"),
    ).reset_index()

    agg["season"] = year
    agg["ip"] = agg["ip_outs"].apply(ip_from_outs)
    agg["era"] = agg.apply(lambda r: era(r["er"], r["ip_outs"]), axis=1)
    agg["whip"] = agg.apply(lambda r: whip(r["h"], r["bb"], r["ip_outs"]), axis=1)
    agg["k_per_9"] = agg.apply(lambda r: k_per_9(r["so"], r["ip_outs"]), axis=1)
    agg["bb_per_9"] = agg.apply(lambda r: bb_per_9(r["bb"], r["ip_outs"]), axis=1)
    agg["fip"] = agg.apply(lambda r: fip(r["hr"], r["bb"], r["hbp"], r["so"], r["ip_outs"]), axis=1)

    return agg


def build_player_id_map(roster_names: dict[str, str]) -> list[dict]:
    """Build player ID map from roster data. MLB IDs added if available."""
    return [
        {"retro_id": pid, "name": name}
        for pid, name in sorted(roster_names.items())
    ]


def build_latest_json(
    batting_season: pd.DataFrame,
    pitching_season: pd.DataFrame,
    year: int,
) -> dict:
    """Build the player-stats-latest.json payload."""
    batting_records = []
    if not batting_season.empty:
        for _, r in batting_season.iterrows():
            batting_records.append({
                "player_id": r["player_id"],
                "name": r["name"],
                "team": r["team"],
                "g": int(r["g"]),
                "pa": int(r["pa"]),
                "ab": int(r["ab"]),
                "h": int(r["h"]),
                "doubles": int(r["doubles"]),
                "triples": int(r["triples"]),
                "hr": int(r["hr"]),
                "rbi": int(r["rbi"]),
                "bb": int(r["bb"]),
                "so": int(r["so"]),
                "sb": int(r["sb"]),
                "cs": int(r["cs"]),
                "avg": float(r["avg"]),
                "obp": float(r["obp"]),
                "slg": float(r["slg"]),
                "ops": float(r["ops"]),
            })

    pitching_records = []
    if not pitching_season.empty:
        for _, r in pitching_season.iterrows():
            pitching_records.append({
                "player_id": r["player_id"],
                "name": r["name"],
                "team": r["team"],
                "g": int(r["g"]),
                "gs": int(r["gs"]),
                "ip": float(r["ip"]),
                "h": int(r["h"]),
                "er": int(r["er"]),
                "bb": int(r["bb"]),
                "so": int(r["so"]),
                "hr": int(r["hr"]),
                "w": int(r["w"]),
                "l": int(r["l"]),
                "sv": int(r["sv"]),
                "era": float(r["era"]),
                "whip": float(r["whip"]),
                "k_per_9": float(r["k_per_9"]),
                "fip": float(r["fip"]),
            })

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "season": year,
        "batting": batting_records,
        "pitching": pitching_records,
    }


def upload_to_s3(output_dir: Path, bucket: str):
    """Upload all output files to S3."""
    import boto3
    s3 = boto3.client("s3")

    for fpath in sorted(output_dir.rglob("*")):
        if fpath.is_file():
            key = str(fpath.relative_to(output_dir))
            content_type = "application/json" if fpath.suffix == ".json" else "text/csv"
            print(f"  Uploading s3://{bucket}/{key} ...")
            s3.upload_file(
                str(fpath), bucket, key,
                ExtraArgs={"ContentType": content_type},
            )

    print(f"  Done — uploaded to s3://{bucket}/")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Retrosheet player stats")
    parser.add_argument("--years", default="2015-2024", help="Year or range (e.g. 2024, 2015-2024)")
    parser.add_argument("--team", default="BAL", help="Retrosheet team code (default: BAL)")
    parser.add_argument("--upload", action="store_true", help="Upload output to S3")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: data-pipelines/output/player-stats)")
    parser.add_argument("--bucket", type=str, default=PLAYER_STATS_BUCKET, help="S3 bucket name")
    args = parser.parse_args()

    years = parse_year_range(args.years)
    team = args.team.upper()
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Subdirectories
    (output_dir / "batting-daily").mkdir(exist_ok=True)
    (output_dir / "pitching-daily").mkdir(exist_ok=True)
    (output_dir / "season-totals").mkdir(exist_ok=True)

    all_roster_names: dict[str, str] = {}
    latest_batting_season = pd.DataFrame()
    latest_pitching_season = pd.DataFrame()
    latest_year = max(years)

    with tempfile.TemporaryDirectory(prefix="retrosheet_") as tmpdir:
        tmp = Path(tmpdir)

        for year in years:
            print(f"\n{'='*60}")
            print(f"Processing {year} ...")
            print(f"{'='*60}")

            # 1. Download
            try:
                year_dir = download_event_files(year, tmp)
            except requests.HTTPError as e:
                print(f"  Skipping {year}: {e}")
                continue

            # 2. Run cwdaily
            try:
                csv_text = run_cwdaily(year_dir, year)
            except (FileNotFoundError, RuntimeError) as e:
                print(f"  Skipping {year}: {e}")
                continue

            # 3. Parse roster files for player names
            roster_names = parse_roster_files(year_dir, team)
            all_roster_names.update(roster_names)

            # 4. Parse into DataFrame
            df = cwdaily_to_dataframe(csv_text)
            print(f"  cwdaily produced {len(df)} player-game rows")

            # 5. Extract batting + pitching
            batting_daily = extract_batting(df, team, roster_names, year)
            pitching_daily = extract_pitching(df, team, roster_names, year)
            print(f"  {team} batting rows: {len(batting_daily)}, pitching rows: {len(pitching_daily)}")

            # 6. Save daily CSVs
            if not batting_daily.empty:
                batting_daily.to_csv(output_dir / "batting-daily" / f"batting_daily_{year}.csv", index=False)

            if not pitching_daily.empty:
                pitching_daily.to_csv(output_dir / "pitching-daily" / f"pitching_daily_{year}.csv", index=False)

            # 7. Aggregate season totals
            batting_season = aggregate_batting_season(batting_daily, year)
            pitching_season = aggregate_pitching_season(pitching_daily, year)

            if not batting_season.empty:
                batting_season.to_csv(output_dir / "season-totals" / f"batting_season_{year}.csv", index=False)

            if not pitching_season.empty:
                pitching_season.to_csv(output_dir / "season-totals" / f"pitching_season_{year}.csv", index=False)

            # Track latest year for the JSON output
            if year == latest_year:
                latest_batting_season = batting_season
                latest_pitching_season = pitching_season

    # 8. Player ID map
    id_map = build_player_id_map(all_roster_names)
    with open(output_dir / "player-id-map.json", "w") as f:
        json.dump(id_map, f, indent=2)
    print(f"\nPlayer ID map: {len(id_map)} players")

    # 9. Build latest JSON
    latest = build_latest_json(latest_batting_season, latest_pitching_season, latest_year)
    with open(output_dir / "player-stats-latest.json", "w") as f:
        json.dump(latest, f, indent=2)
    print(f"player-stats-latest.json: {len(latest['batting'])} batters, {len(latest['pitching'])} pitchers")

    # 10. Upload to S3
    if args.upload:
        print(f"\nUploading to s3://{args.bucket}/ ...")
        upload_to_s3(output_dir, args.bucket)

    print("\nDone!")


if __name__ == "__main__":
    main()
