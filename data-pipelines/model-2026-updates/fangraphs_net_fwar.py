#!/usr/bin/env python3
"""
fangraphs_net_fwar.py — Compute and chart net Projected fWAR per team
from pre-categorized FanGraphs offseason transaction exports.

Reads:  fwar-additions.csv    (players gained by each team)
        fwar-subtractions.csv (players lost by each team)
Writes: fangraphs-net-fwar-chart.png  (horizontal bar chart)
        fangraphs-net-fwar-summary.csv (per-team summary)

Usage:
    python3 fangraphs_net_fwar.py
"""
import io
import os
import re
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADDITIONS_PATH = os.path.join(SCRIPT_DIR, 'fwar-additions.csv')
SUBTRACTIONS_PATH = os.path.join(SCRIPT_DIR, 'fwar-subtractions.csv')
CHART_PATH = os.path.join(SCRIPT_DIR, 'fangraphs-net-fwar-chart.png')
SUMMARY_PATH = os.path.join(SCRIPT_DIR, 'fangraphs-net-fwar-summary.csv')

# FanGraphs abbreviations → project canonical codes
FG_TO_CANONICAL = {
    'ARI': 'AZ',
    'CHW': 'CWS',
    'KCR': 'KC',
    'SDP': 'SD',
    'SFG': 'SF',
    'TBR': 'TB',
    'WSN': 'WSH',
}

# Team nicknames (from trade descriptions) → canonical codes
NICKNAME_TO_CANONICAL = {
    'Angels': 'LAA', 'Astros': 'HOU', 'Athletics': 'ATH', 'Blue Jays': 'TOR',
    'Braves': 'ATL', 'Brewers': 'MIL', 'Cardinals': 'STL', 'Cubs': 'CHC',
    'Diamondbacks': 'AZ', 'Dodgers': 'LAD', 'Giants': 'SF', 'Guardians': 'CLE',
    'Mariners': 'SEA', 'Marlins': 'MIA', 'Mets': 'NYM', 'Nationals': 'WSH',
    'Orioles': 'BAL', 'Padres': 'SD', 'Phillies': 'PHI', 'Pirates': 'PIT',
    'Rangers': 'TEX', 'Rays': 'TB', 'Red Sox': 'BOS', 'Reds': 'CIN',
    'Rockies': 'COL', 'Royals': 'KC', 'Tigers': 'DET', 'Twins': 'MIN',
    'White Sox': 'CWS', 'Yankees': 'NYY',
}

DIVISION = {
    'BAL': 'AL East', 'BOS': 'AL East', 'NYY': 'AL East', 'TB':  'AL East', 'TOR': 'AL East',
    'CWS': 'AL Central', 'CLE': 'AL Central', 'DET': 'AL Central', 'KC':  'AL Central', 'MIN': 'AL Central',
    'HOU': 'AL West', 'LAA': 'AL West', 'ATH': 'AL West', 'SEA': 'AL West', 'TEX': 'AL West',
    'ATL': 'NL East', 'MIA': 'NL East', 'NYM': 'NL East', 'PHI': 'NL East', 'WSH': 'NL East',
    'CHC': 'NL Central', 'CIN': 'NL Central', 'MIL': 'NL Central', 'PIT': 'NL Central', 'STL': 'NL Central',
    'AZ':  'NL West', 'COL': 'NL West', 'LAD': 'NL West', 'SD':  'NL West', 'SF':  'NL West',
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_additions(path: str) -> pd.DataFrame:
    """Load the additions CSV (each row is individually quoted with doubled-quote escaping)."""
    import csv
    with open(path, 'r', encoding='cp1252') as f:
        raw = f.read()
    # Each line is wrapped in outer quotes; inner fields with commas use "" escaping.
    # Strip outer quotes, then restore inner escaped quotes to standard CSV format.
    cleaned_lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip outer quotes
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        # Replace doubled quotes "" with standard CSV quoting
        # The pattern is: ,"" becomes ," and "",  becomes ",
        line = line.replace('""', '"')
        cleaned_lines.append(line)
    df = pd.read_csv(io.StringIO('\n'.join(cleaned_lines)))
    return df


def load_subtractions(path: str) -> pd.DataFrame:
    """Load the subtractions CSV (standard CSV with BOM)."""
    df = pd.read_csv(path, encoding='utf-8-sig')
    return df


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize team codes and parse WAR columns."""
    df = df.copy()
    df['team'] = df['Team'].map(lambda t: FG_TO_CANONICAL.get(t, t))
    df['war_proj'] = pd.to_numeric(df['Proj. WAR'], errors='coerce').fillna(0)
    return df


# ---------------------------------------------------------------------------
# Trade departure extraction
# ---------------------------------------------------------------------------

_ACQUIRED_RE = re.compile(r'Acquired from ([\w\s]+?) (?:for|with)', re.IGNORECASE)


def extract_trade_departures(adds: pd.DataFrame) -> pd.DataFrame:
    """
    For each trade in the additions file, create a subtraction row for the
    team that lost the player.

    E.g. "LAA, Grayson Rodriguez, Acquired from Orioles for OF Taylor Ward, 2.1"
    → subtraction: BAL lost Grayson Rodriguez, Proj. WAR = 2.1
    """
    trade_subs = []
    for _, row in adds.iterrows():
        details = row.get('Transaction Details', '')
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
        trade_subs.append({
            'team': from_team,
            'Name': row['Name'],
            'war_proj': row['war_proj'],
            'Transaction Details': f'Traded to {row["team"]}',
        })

    if trade_subs:
        df = pd.DataFrame(trade_subs)
        print(f'  Extracted {len(df)} trade departures from additions file')
        return df
    return pd.DataFrame(columns=['team', 'Name', 'war_proj', 'Transaction Details'])


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def compute_net_fwar(adds: pd.DataFrame, subs: pd.DataFrame) -> pd.DataFrame:
    """Compute net Projected fWAR per team from additions and subtractions."""
    add_by_team = adds.groupby('team')['war_proj'].sum()
    sub_by_team = subs.groupby('team')['war_proj'].sum()

    records = []
    for team in sorted(DIVISION.keys()):
        gained = round(add_by_team.get(team, 0), 1)
        lost = round(sub_by_team.get(team, 0), 1)
        net = round(gained - lost, 1)
        records.append({
            'team': team,
            'division': DIVISION[team],
            'additions': len(adds[adds['team'] == team]),
            'subtractions': len(subs[subs['team'] == team]),
            'proj_war_gained': gained,
            'proj_war_lost': lost,
            'net_proj_war': net,
        })

    return pd.DataFrame(records).sort_values('net_proj_war', ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

def make_chart(summary: pd.DataFrame, output_path: str):
    """Create a horizontal bar chart of net Projected fWAR by team."""
    plot_df = summary.sort_values('net_proj_war', ascending=True)

    fig, ax = plt.subplots(figsize=(12, 10))

    colors = ['#2e7d32' if v >= 0 else '#c62828' for v in plot_df['net_proj_war']]

    # Highlight BAL with Orioles orange
    teams_list = plot_df['team'].tolist()
    for i, team in enumerate(teams_list):
        if team == 'BAL':
            colors[i] = '#DF4601'

    bars = ax.barh(
        plot_df['team'],
        plot_df['net_proj_war'],
        color=colors,
        edgecolor='white',
        linewidth=0.5,
        height=0.7,
    )

    # Add value labels
    for bar, val in zip(bars, plot_df['net_proj_war']):
        x_pos = bar.get_width()
        ha = 'left' if val >= 0 else 'right'
        offset = 0.15 if val >= 0 else -0.15
        ax.text(
            x_pos + offset, bar.get_y() + bar.get_height() / 2,
            f'{val:+.1f}',
            va='center', ha=ha, fontsize=8, fontweight='bold',
            color='#333333',
        )

    ax.set_xlabel('Net Projected fWAR', fontsize=12, fontweight='bold')
    ax.set_title(
        '2025\u201326 Offseason: FanGraphs Net Projections\n'
        '(Transactions through Feb 17, 2026)',
        fontsize=14, fontweight='bold', pad=15,
    )

    ax.axvline(x=0, color='#555555', linewidth=0.8, linestyle='-')
    ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', labelsize=9)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Chart saved to {output_path}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    for path, label in [(ADDITIONS_PATH, 'additions'), (SUBTRACTIONS_PATH, 'subtractions')]:
        if not os.path.exists(path):
            print(f'ERROR: {label} CSV not found at {path}', file=sys.stderr)
            sys.exit(1)

    print('Loading additions...')
    adds_raw = load_additions(ADDITIONS_PATH)
    adds = prepare(adds_raw)
    print(f'  {len(adds)} addition rows')

    print('Loading subtractions...')
    subs_raw = load_subtractions(SUBTRACTIONS_PATH)
    subs = prepare(subs_raw)
    print(f'  {len(subs)} subtraction rows')

    # Extract trade departures from the additions file
    print('Extracting trade departures...')
    trade_subs = extract_trade_departures(adds)
    subs = pd.concat([subs, trade_subs], ignore_index=True)
    print(f'  {len(subs)} total subtraction rows (including trade departures)')

    # Check for teams not in our mapping
    all_teams = set(adds['team'].unique()) | set(subs['team'].unique())
    unknown = all_teams - set(DIVISION.keys())
    if unknown:
        print(f'  WARNING: Unknown team codes: {unknown}')

    summary = compute_net_fwar(adds, subs)

    # Print console summary
    print(f'\n{"="*75}')
    print(f'  NET PROJECTED fWAR \u2014 2025-26 Offseason (FanGraphs)')
    print(f'{"="*75}')
    print(f'  {"Team":<6} {"Division":<12} {"Adds":>5} {"Subs":>5} '
          f'{"Gained":>8} {"Lost":>8} {"Net fWAR":>9}')
    print(f'  {"-"*6} {"-"*12} {"-"*5} {"-"*5} {"-"*8} {"-"*8} {"-"*9}')
    for _, row in summary.iterrows():
        team_marker = ' \u25c4' if row['team'] == 'BAL' else ''
        print(f'  {row["team"]:<6} {row["division"]:<12} {row["additions"]:>5} {row["subtractions"]:>5} '
              f'{row["proj_war_gained"]:>8.1f} {row["proj_war_lost"]:>8.1f} '
              f'{row["net_proj_war"]:>+9.1f}{team_marker}')

    # Save summary CSV
    summary.to_csv(SUMMARY_PATH, index=False)
    print(f'\nSummary CSV saved to {SUMMARY_PATH}')

    # Generate chart
    make_chart(summary, CHART_PATH)


if __name__ == '__main__':
    main()
