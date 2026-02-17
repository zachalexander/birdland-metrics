#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
offseason-war-analysis.py — Summarize offseason WAR net gain/loss per team.

Reads the transaction CSV produced by preseason_adjustment.py and outputs:
  1. A JSON summary with per-team WAR gained/lost/net + division rollups
  2. A console table sorted by net WAR

Usage:
    python3 offseason-war-analysis.py                         # defaults
    python3 offseason-war-analysis.py --season 2026           # explicit season
    python3 offseason-war-analysis.py --csv path/to/file.csv  # custom CSV path
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

# Add mlb_common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', 'layers', 'mlb-pipeline-common', 'python'))
from mlb_common.team_codes import TEAM_DIVISION, TEAM_LEAGUE


def load_transactions(csv_path):
    """Load and validate the offseason transactions CSV."""
    df = pd.read_csv(csv_path)
    required = {'player_name', 'from_team', 'to_team', 'type', 'war'}
    missing = required - set(df.columns)
    if missing:
        print(f"ERROR: CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    # Check for blended WAR columns (produced by Marcel projection pipeline)
    has_blended = all(c in df.columns for c in ('war_historical', 'war_projected', 'war_blended'))
    if has_blended:
        print("  Found blended WAR columns (historical/projected/blended)")
    else:
        print("  Using single WAR column (no projection data)")
    return df, has_blended


def build_team_summary(df, has_blended):
    """
    Aggregate WAR gained and lost per team from the transaction DataFrame.

    Returns a dict keyed by team abbreviation with gained/lost/net totals
    and lists of individual player moves. When has_blended is True, also
    aggregates historical, projected, and blended WAR separately.
    """
    war_cols = ['war']
    if has_blended:
        war_cols = ['war', 'war_historical', 'war_projected', 'war_blended']

    teams = {}

    # Initialize all 30 teams so every team appears even with zero activity
    for team in TEAM_DIVISION:
        entry = {
            'team': team,
            'division': TEAM_DIVISION[team],
            'league': TEAM_LEAGUE[team],
            'war_gained': 0.0,
            'war_lost': 0.0,
            'net_war': 0.0,
            'players_gained': [],
            'players_lost': [],
        }
        if has_blended:
            for suffix in ('historical', 'projected', 'blended'):
                entry[f'war_gained_{suffix}'] = 0.0
                entry[f'war_lost_{suffix}'] = 0.0
                entry[f'net_war_{suffix}'] = 0.0
        teams[team] = entry

    for _, row in df.iterrows():
        war = float(row['war']) if pd.notna(row['war']) else 0.0
        to_team = row['to_team'] if pd.notna(row['to_team']) else None
        from_team = row['from_team'] if pd.notna(row['from_team']) else None
        txn_type = row['type'] if pd.notna(row['type']) else ''

        # Extract per-metric WAR values
        war_values = {'war': war}
        if has_blended:
            for suffix in ('historical', 'projected', 'blended'):
                col = f'war_{suffix}'
                war_values[col] = float(row[col]) if pd.notna(row[col]) else 0.0

        player_entry = {
            'name': row['player_name'],
            'war': round(war, 2),
            'type': txn_type,
        }
        if has_blended:
            player_entry['war_historical'] = round(war_values['war_historical'], 2)
            player_entry['war_projected'] = round(war_values['war_projected'], 2)
            player_entry['war_blended'] = round(war_values['war_blended'], 2)

        if to_team and to_team in teams:
            teams[to_team]['war_gained'] += war
            if has_blended:
                for suffix in ('historical', 'projected', 'blended'):
                    teams[to_team][f'war_gained_{suffix}'] += war_values[f'war_{suffix}']
            gain_entry = dict(player_entry)
            gain_entry['from_team'] = from_team
            teams[to_team]['players_gained'].append(gain_entry)

        if from_team and from_team in teams:
            teams[from_team]['war_lost'] += war
            if has_blended:
                for suffix in ('historical', 'projected', 'blended'):
                    teams[from_team][f'war_lost_{suffix}'] += war_values[f'war_{suffix}']
            loss_entry = dict(player_entry)
            loss_entry['to_team'] = to_team
            teams[from_team]['players_lost'].append(loss_entry)

    # Compute net and round
    for t in teams.values():
        t['war_gained'] = round(t['war_gained'], 1)
        t['war_lost'] = round(t['war_lost'], 1)
        t['net_war'] = round(t['war_gained'] - t['war_lost'], 1)
        if has_blended:
            for suffix in ('historical', 'projected', 'blended'):
                t[f'war_gained_{suffix}'] = round(t[f'war_gained_{suffix}'], 1)
                t[f'war_lost_{suffix}'] = round(t[f'war_lost_{suffix}'], 1)
                t[f'net_war_{suffix}'] = round(
                    t[f'war_gained_{suffix}'] - t[f'war_lost_{suffix}'], 1)
        # Sort players by WAR descending
        t['players_gained'].sort(key=lambda p: p['war'], reverse=True)
        t['players_lost'].sort(key=lambda p: p['war'], reverse=True)

    return teams


def build_division_summary(teams):
    """Compute average net WAR and best/worst team per division."""
    div_teams = defaultdict(list)
    for t in teams.values():
        div_teams[t['division']].append(t)

    summary = []
    for div in sorted(div_teams):
        members = div_teams[div]
        nets = [m['net_war'] for m in members]
        avg = round(sum(nets) / len(nets), 1)
        best = max(members, key=lambda m: m['net_war'])
        worst = min(members, key=lambda m: m['net_war'])
        summary.append({
            'division': div,
            'avg_net_war': avg,
            'best': best['team'],
            'best_net_war': best['net_war'],
            'worst': worst['team'],
            'worst_net_war': worst['net_war'],
        })

    summary.sort(key=lambda d: d['avg_net_war'], reverse=True)
    return summary


def print_console_summary(teams, div_summary, season, has_blended):
    """Print a readable summary table to stdout."""
    sorted_teams = sorted(teams.values(), key=lambda t: t['net_war'], reverse=True)

    if has_blended:
        print(f"\n{'='*90}")
        print(f"  OFFSEASON WAR ANALYSIS — {season} (Blended: Historical + Marcel Projection)")
        print(f"{'='*90}")
        print(f"  {'Team':<6} {'Division':<12} {'Net Hist':>9} {'Net Proj':>9} {'Net Blend':>10}")
        print(f"  {'-'*6} {'-'*12} {'-'*9} {'-'*9} {'-'*10}")
        for t in sorted_teams:
            print(f"  {t['team']:<6} {t['division']:<12} "
                  f"{t['net_war_historical']:>+9.1f} "
                  f"{t['net_war_projected']:>+9.1f} "
                  f"{t['net_war_blended']:>+10.1f}")
    else:
        print(f"\n{'='*70}")
        print(f"  OFFSEASON WAR ANALYSIS — {season}")
        print(f"{'='*70}")
        print(f"  {'Team':<6} {'Division':<12} {'Gained':>8} {'Lost':>8} {'Net':>8}")
        print(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*8} {'-'*8}")
        for t in sorted_teams:
            net_str = f"{t['net_war']:+.1f}"
            print(f"  {t['team']:<6} {t['division']:<12} {t['war_gained']:>8.1f} {t['war_lost']:>8.1f} {net_str:>8}")

    print(f"\n{'='*70}")
    print(f"  DIVISION SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Division':<14} {'Avg Net':>8} {'Best':<6} {'Net':>6}  {'Worst':<6} {'Net':>6}")
    print(f"  {'-'*14} {'-'*8} {'-'*6} {'-'*6}  {'-'*6} {'-'*6}")
    for d in div_summary:
        print(f"  {d['division']:<14} {d['avg_net_war']:>+8.1f} {d['best']:<6} {d['best_net_war']:>+6.1f}"
              f"  {d['worst']:<6} {d['worst_net_war']:>+6.1f}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze offseason WAR changes per team')
    parser.add_argument('--season', type=int, default=2026, help='Season year (default: 2026)')
    parser.add_argument('--csv', type=str, default=None,
                        help='Path to offseason_transactions CSV (default: auto-detect)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON path (default: offseason-war-summary-{season}.json)')
    args = parser.parse_args()

    # Locate the transaction CSV
    if args.csv:
        csv_path = args.csv
    else:
        csv_path = os.path.join(os.path.dirname(__file__),
                                '..', 'model-2026-updates',
                                f'offseason_transactions_{args.season}.csv')

    if not os.path.exists(csv_path):
        print(f"ERROR: Transaction CSV not found at {csv_path}", file=sys.stderr)
        print("Run preseason_adjustment.py first, or use --csv to specify the path.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading transactions from {csv_path}")
    df, has_blended = load_transactions(csv_path)
    print(f"  {len(df)} transactions loaded")

    teams = build_team_summary(df, has_blended)
    div_summary = build_division_summary(teams)
    print_console_summary(teams, div_summary, args.season, has_blended)

    # Build output JSON
    sorted_teams = sorted(teams.values(), key=lambda t: t['net_war'], reverse=True)
    output = {
        'season': args.season,
        'updated': datetime.now(timezone.utc).isoformat(),
        'transaction_count': len(df),
        'teams': sorted_teams,
        'division_summary': div_summary,
    }

    output_path = args.output or os.path.join(
        os.path.dirname(__file__), '..', 'model-2026-updates',
        f'offseason-war-summary-{args.season}.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Saved JSON summary to {output_path}")


if __name__ == '__main__':
    main()
