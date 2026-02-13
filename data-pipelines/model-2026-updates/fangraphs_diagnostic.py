#!/usr/bin/env python3
"""
Diagnose why a team can share similar projected wins with FanGraphs but have
different playoff odds.

Primary input is the simulation matrix produced by the projections Lambda:
  - season_win_simulations.parquet (or CSV)

Optional inputs:
  - playoff-odds-latest.json
  - season win summary CSV (or projections-latest.json)
  - FanGraphs CSV for side-by-side comparison
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
COMMON_PATH = ROOT / "data-pipelines" / "layers" / "mlb-pipeline-common" / "python"
if str(COMMON_PATH) not in sys.path:
    sys.path.insert(0, str(COMMON_PATH))

from mlb_common.team_codes import TEAM_DIVISION, TEAM_LEAGUE  # noqa: E402


POSSIBLE_FG_WINS_COLS = [
    "wins",
    "projected_wins",
    "mean_wins",
    "win_total",
]
POSSIBLE_FG_PLAYOFF_COLS = [
    "playoff_pct",
    "playoff_odds",
    "make_playoffs_pct",
    "make_playoffs",
]
POSSIBLE_TEAM_COLS = ["team", "team_abbr", "abbr", "code"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze simulation-based playoff conversion at target wins."
    )
    parser.add_argument(
        "--sim-file",
        required=True,
        help="Path to season_win_simulations parquet/csv file.",
    )
    parser.add_argument(
        "--team",
        default="BAL",
        help="Target team abbreviation (default: BAL).",
    )
    parser.add_argument(
        "--target-wins",
        type=int,
        default=84,
        help="Target win total to inspect (default: 84).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=1,
        help="Window around target wins for conditional odds (default: 1 -> target +/- 1).",
    )
    parser.add_argument(
        "--odds-file",
        help="Optional playoff-odds-latest.json for comparison.",
    )
    parser.add_argument(
        "--fangraphs-file",
        help="Optional FanGraphs CSV with team/wins/playoff columns.",
    )
    parser.add_argument(
        "--output-md",
        help="Optional path to write markdown report.",
    )
    return parser.parse_args()


def load_sim_matrix(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported sim file format: {path}")

    if "sim_id" in df.columns:
        df = df.drop(columns=["sim_id"])

    missing_teams = [c for c in df.columns if c not in TEAM_LEAGUE]
    if missing_teams:
        raise ValueError(
            "Simulation file contains unknown team columns: "
            + ", ".join(sorted(missing_teams)[:10])
        )
    return df


def compute_playoff_flags(df_sim: pd.DataFrame) -> Dict[str, np.ndarray]:
    al_teams = sorted([t for t in df_sim.columns if TEAM_LEAGUE.get(t) == "AL"])
    al_divisions: Dict[str, List[str]] = {}
    for team in al_teams:
        division = TEAM_DIVISION.get(team, "Unknown")
        al_divisions.setdefault(division, []).append(team)

    n_sims = len(df_sim)
    playoff_flags = {t: np.zeros(n_sims, dtype=bool) for t in al_teams}

    for sim_idx in range(n_sims):
        al_wins = {t: float(df_sim.at[sim_idx, t]) for t in al_teams}

        division_winners = set()
        for _, div_teams in al_divisions.items():
            winner = max(div_teams, key=lambda t: al_wins[t])
            division_winners.add(winner)

        remaining = [(t, al_wins[t]) for t in al_teams if t not in division_winners]
        remaining.sort(key=lambda item: item[1], reverse=True)
        wild_cards = {t for t, _ in remaining[:3]}

        for team in division_winners | wild_cards:
            playoff_flags[team][sim_idx] = True

    return playoff_flags


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return float("nan")
    return round(100.0 * numerator / denominator, 1)


def q(series: pd.Series, p: float) -> float:
    return float(np.percentile(series.to_numpy(), p))


def conditional_playoff_pct(
    wins: pd.Series,
    playoff_flags: np.ndarray,
    lo: int,
    hi: int,
) -> Tuple[float, int]:
    mask = (wins >= lo) & (wins <= hi)
    count = int(mask.sum())
    if count == 0:
        return float("nan"), 0
    make_po = int(playoff_flags[mask.to_numpy()].sum())
    return pct(make_po, count), count


def likely_wildcard_rivals(df_sim: pd.DataFrame, team: str, k: int = 6) -> List[str]:
    al_teams = [t for t in df_sim.columns if TEAM_LEAGUE.get(t) == "AL" and t != team]
    team_median = float(df_sim[team].median())

    def key_fn(t: str) -> Tuple[float, str]:
        return (abs(float(df_sim[t].median()) - team_median), t)

    return sorted(al_teams, key=key_fn)[:k]


def load_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_odds_map(path: Path) -> Dict[str, float]:
    payload = load_json_file(path)
    rows = payload.get("odds", [])
    out = {}
    for row in rows:
        team = row.get("team")
        if not team:
            continue
        out[team] = float(row.get("playoff_pct", float("nan")))
    return out


def _find_col(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    normalized = {c.lower().strip(): c for c in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def load_fangraphs_map(path: Path) -> Dict[str, Dict[str, float]]:
    df = pd.read_csv(path)
    team_col = _find_col(df, POSSIBLE_TEAM_COLS)
    wins_col = _find_col(df, POSSIBLE_FG_WINS_COLS)
    playoff_col = _find_col(df, POSSIBLE_FG_PLAYOFF_COLS)

    if not team_col:
        raise ValueError(
            f"Could not find team column in FanGraphs file. Tried: {POSSIBLE_TEAM_COLS}"
        )
    if not wins_col and not playoff_col:
        raise ValueError(
            "Could not find wins or playoff column in FanGraphs file. "
            f"Tried wins={POSSIBLE_FG_WINS_COLS}, playoff={POSSIBLE_FG_PLAYOFF_COLS}"
        )

    out: Dict[str, Dict[str, float]] = {}
    for _, row in df.iterrows():
        team = str(row[team_col]).strip().upper()
        if team not in TEAM_LEAGUE:
            continue
        entry: Dict[str, float] = {}
        if wins_col and not pd.isna(row[wins_col]):
            entry["wins"] = float(row[wins_col])
        if playoff_col and not pd.isna(row[playoff_col]):
            playoff_raw = float(row[playoff_col])
            if playoff_raw <= 1.0:
                playoff_raw *= 100.0
            entry["playoff_pct"] = playoff_raw
        if entry:
            out[team] = entry
    return out


def build_report(
    df_sim: pd.DataFrame,
    team: str,
    target_wins: int,
    window: int,
    odds_map: Optional[Dict[str, float]] = None,
    fangraphs_map: Optional[Dict[str, Dict[str, float]]] = None,
) -> str:
    if team not in df_sim.columns:
        raise ValueError(f"Team {team} is not in the simulation matrix.")
    if TEAM_LEAGUE.get(team) != "AL":
        raise ValueError("This diagnostic currently supports AL playoff structure only.")

    playoff_flags = compute_playoff_flags(df_sim)
    team_wins = df_sim[team]
    team_playoff = playoff_flags[team]

    exact_pct, exact_n = conditional_playoff_pct(team_wins, team_playoff, target_wins, target_wins)
    win_range = (target_wins - window, target_wins + window)
    range_pct, range_n = conditional_playoff_pct(team_wins, team_playoff, win_range[0], win_range[1])
    ge_pct, ge_n = conditional_playoff_pct(team_wins, team_playoff, target_wins, 200)

    proj_playoff = pct(int(team_playoff.sum()), len(team_playoff))
    pipeline_playoff = odds_map.get(team) if odds_map else float("nan")

    lines: List[str] = []
    lines.append(f"# {team} Playoff-Odds Diagnostic")
    lines.append("")
    lines.append("## Team Distribution")
    lines.append("| Team | Mean Wins | Median | Std Dev | P10 | P90 | Unconditional Playoff% |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    lines.append(
        "| "
        + f"{team} | {team_wins.mean():.2f} | {team_wins.median():.0f} | {team_wins.std():.2f} "
        + f"| {q(team_wins, 10):.0f} | {q(team_wins, 90):.0f} | {proj_playoff:.1f}% |"
    )
    lines.append("")

    lines.append("## Conversion Around Target Wins")
    lines.append("| Scenario | Playoff% | Samples |")
    lines.append("|---|---:|---:|")
    lines.append(f"| Exactly {target_wins} wins | {exact_pct:.1f}% | {exact_n} |")
    lines.append(
        f"| Wins in [{win_range[0]}, {win_range[1]}] | {range_pct:.1f}% | {range_n} |"
    )
    lines.append(f"| Wins >= {target_wins} | {ge_pct:.1f}% | {ge_n} |")
    lines.append("")

    lines.append("## AL East Context")
    lines.append("| Team | Mean Wins | P10 | P90 | Playoff% |")
    lines.append("|---|---:|---:|---:|---:|")
    al_east = sorted(
        [t for t in df_sim.columns if TEAM_DIVISION.get(t) == "AL East"],
        key=lambda t: float(df_sim[t].mean()),
        reverse=True,
    )
    for t in al_east:
        p = pct(int(playoff_flags[t].sum()), len(playoff_flags[t]))
        lines.append(
            f"| {t} | {df_sim[t].mean():.2f} | {q(df_sim[t], 10):.0f} | {q(df_sim[t], 90):.0f} | {p:.1f}% |"
        )
    lines.append("")

    lines.append("## Closest AL Wildcard Rivals (By Median Wins)")
    lines.append("| Team | Median | P25 | P75 | Playoff% |")
    lines.append("|---|---:|---:|---:|---:|")
    for rival in likely_wildcard_rivals(df_sim, team, k=6):
        p = pct(int(playoff_flags[rival].sum()), len(playoff_flags[rival]))
        lines.append(
            f"| {rival} | {df_sim[rival].median():.0f} | {q(df_sim[rival], 25):.0f} | {q(df_sim[rival], 75):.0f} | {p:.1f}% |"
        )
    lines.append("")

    lines.append("## Around-Target Conversion Across AL")
    lines.append(f"| Team | Playoff% when wins in [{win_range[0]}, {win_range[1]}] | Samples |")
    lines.append("|---|---:|---:|")
    rows = []
    for t in sorted([c for c in df_sim.columns if TEAM_LEAGUE.get(c) == "AL"]):
        this_pct, this_n = conditional_playoff_pct(df_sim[t], playoff_flags[t], win_range[0], win_range[1])
        rows.append((t, this_pct, this_n))
    rows.sort(key=lambda item: (-item[1] if not math.isnan(item[1]) else float("inf"), -item[2], item[0]))
    for t, this_pct, this_n in rows:
        pct_str = "n/a" if math.isnan(this_pct) else f"{this_pct:.1f}%"
        lines.append(f"| {t} | {pct_str} | {this_n} |")
    lines.append("")

    lines.append("## Interpretation")
    lines.append(
        f"- If BAL has similar mean/median wins to another source but lower playoff odds, "
        "the gap usually comes from lower conversion at the target-win band because rival teams "
        "also cluster in that same win range."
    )
    lines.append(
        "- Inference: playoff odds are a joint race outcome, not a one-team win-total mapping."
    )

    if odds_map:
        lines.append("")
        lines.append("## Pipeline Odds Check")
        lines.append("| Team | Recomputed Playoff% | playoff-odds-latest.json | Delta |")
        lines.append("|---|---:|---:|---:|")
        delta = proj_playoff - pipeline_playoff
        lines.append(
            f"| {team} | {proj_playoff:.1f}% | {pipeline_playoff:.1f}% | {delta:+.1f} pts |"
        )

    if fangraphs_map and team in fangraphs_map:
        fg = fangraphs_map[team]
        fg_wins = fg.get("wins", float("nan"))
        fg_playoff = fg.get("playoff_pct", float("nan"))
        lines.append("")
        lines.append("## Side-by-Side With FanGraphs")
        lines.append("| Team | Source | Mean/Proj Wins | Playoff% |")
        lines.append("|---|---|---:|---:|")
        lines.append(f"| {team} | Birdland model | {team_wins.mean():.2f} | {proj_playoff:.1f}% |")
        wins_str = "n/a" if math.isnan(fg_wins) else f"{fg_wins:.2f}"
        po_str = "n/a" if math.isnan(fg_playoff) else f"{fg_playoff:.1f}%"
        lines.append(f"| {team} | FanGraphs input | {wins_str} | {po_str} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()

    sim_path = Path(args.sim_file)
    if not sim_path.exists():
        raise FileNotFoundError(f"Simulation file not found: {sim_path}")

    df_sim = load_sim_matrix(sim_path)
    odds_map = None
    if args.odds_file:
        odds_map = load_odds_map(Path(args.odds_file))

    fangraphs_map = None
    if args.fangraphs_file:
        fangraphs_map = load_fangraphs_map(Path(args.fangraphs_file))

    report = build_report(
        df_sim=df_sim,
        team=args.team.upper(),
        target_wins=args.target_wins,
        window=args.window,
        odds_map=odds_map,
        fangraphs_map=fangraphs_map,
    )

    print(report)

    if args.output_md:
        out_path = Path(args.output_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
