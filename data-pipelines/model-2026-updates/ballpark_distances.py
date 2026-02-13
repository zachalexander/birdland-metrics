"""
Ballpark distance lookup table for MLB travel/fatigue features.

Computes pairwise distances between all 30 MLB ballparks using the Haversine formula.
Includes timezone data for west-to-east travel penalty detection.

Output:
  - ballpark_distances.csv: pairwise distance matrix (30x30)
  - ballpark_info.csv: park name, lat, lon, timezone, team code
  - Travel summary stats printed to console

Usage:
  python ballpark_distances.py
"""
import csv
import math
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# All 30 MLB ballparks with lat/lon and timezone
# Note: Athletics at Sutter Health Park (Sacramento) starting 2025
BALLPARKS = {
    'AZ':  {'name': 'Chase Field',              'city': 'Phoenix, AZ',       'lat': 33.4455, 'lon': -112.0667, 'tz': 'America/Phoenix',       'tz_offset': -7},
    'ATL': {'name': 'Truist Park',              'city': 'Atlanta, GA',       'lat': 33.8907, 'lon': -84.4677,  'tz': 'America/New_York',      'tz_offset': -5},
    'BAL': {'name': 'Oriole Park at Camden Yards', 'city': 'Baltimore, MD',  'lat': 39.2838, 'lon': -76.6216,  'tz': 'America/New_York',      'tz_offset': -5},
    'BOS': {'name': 'Fenway Park',              'city': 'Boston, MA',        'lat': 42.3467, 'lon': -71.0972,  'tz': 'America/New_York',      'tz_offset': -5},
    'CHC': {'name': 'Wrigley Field',            'city': 'Chicago, IL',       'lat': 41.9484, 'lon': -87.6553,  'tz': 'America/Chicago',       'tz_offset': -6},
    'CIN': {'name': 'Great American Ball Park', 'city': 'Cincinnati, OH',    'lat': 39.0974, 'lon': -84.5082,  'tz': 'America/New_York',      'tz_offset': -5},
    'CLE': {'name': 'Progressive Field',        'city': 'Cleveland, OH',     'lat': 41.4962, 'lon': -81.6852,  'tz': 'America/New_York',      'tz_offset': -5},
    'COL': {'name': 'Coors Field',              'city': 'Denver, CO',        'lat': 39.7559, 'lon': -104.9942, 'tz': 'America/Denver',        'tz_offset': -7},
    'CWS': {'name': 'Guaranteed Rate Field',    'city': 'Chicago, IL',       'lat': 41.8299, 'lon': -87.6338,  'tz': 'America/Chicago',       'tz_offset': -6},
    'DET': {'name': 'Comerica Park',            'city': 'Detroit, MI',       'lat': 42.3390, 'lon': -83.0485,  'tz': 'America/Detroit',       'tz_offset': -5},
    'HOU': {'name': 'Minute Maid Park',         'city': 'Houston, TX',       'lat': 29.7573, 'lon': -95.3555,  'tz': 'America/Chicago',       'tz_offset': -6},
    'KC':  {'name': 'Kauffman Stadium',         'city': 'Kansas City, MO',   'lat': 39.0517, 'lon': -94.4803,  'tz': 'America/Chicago',       'tz_offset': -6},
    'LAA': {'name': 'Angel Stadium',            'city': 'Anaheim, CA',       'lat': 33.8003, 'lon': -117.8827, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'LAD': {'name': 'Dodger Stadium',           'city': 'Los Angeles, CA',   'lat': 34.0739, 'lon': -118.2400, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'MIA': {'name': 'LoanDepot Park',           'city': 'Miami, FL',         'lat': 25.7781, 'lon': -80.2196,  'tz': 'America/New_York',      'tz_offset': -5},
    'MIL': {'name': 'American Family Field',    'city': 'Milwaukee, WI',     'lat': 43.0280, 'lon': -87.9712,  'tz': 'America/Chicago',       'tz_offset': -6},
    'MIN': {'name': 'Target Field',             'city': 'Minneapolis, MN',   'lat': 44.9818, 'lon': -93.2775,  'tz': 'America/Chicago',       'tz_offset': -6},
    'NYM': {'name': 'Citi Field',               'city': 'New York, NY',      'lat': 40.7571, 'lon': -73.8458,  'tz': 'America/New_York',      'tz_offset': -5},
    'NYY': {'name': 'Yankee Stadium',           'city': 'New York, NY',      'lat': 40.8296, 'lon': -73.9262,  'tz': 'America/New_York',      'tz_offset': -5},
    'ATH': {'name': 'Sutter Health Park',       'city': 'Sacramento, CA',    'lat': 38.5802, 'lon': -121.5111, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'PHI': {'name': 'Citizens Bank Park',       'city': 'Philadelphia, PA',  'lat': 39.9061, 'lon': -75.1665,  'tz': 'America/New_York',      'tz_offset': -5},
    'PIT': {'name': 'PNC Park',                 'city': 'Pittsburgh, PA',    'lat': 40.4469, 'lon': -80.0057,  'tz': 'America/New_York',      'tz_offset': -5},
    'SD':  {'name': 'Petco Park',               'city': 'San Diego, CA',     'lat': 32.7076, 'lon': -117.1570, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'SEA': {'name': 'T-Mobile Park',            'city': 'Seattle, WA',       'lat': 47.5914, 'lon': -122.3325, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'SF':  {'name': 'Oracle Park',              'city': 'San Francisco, CA', 'lat': 37.7786, 'lon': -122.3893, 'tz': 'America/Los_Angeles',   'tz_offset': -8},
    'STL': {'name': 'Busch Stadium',            'city': 'St. Louis, MO',     'lat': 38.6226, 'lon': -90.1928,  'tz': 'America/Chicago',       'tz_offset': -6},
    'TB':  {'name': 'Tropicana Field',          'city': 'St. Petersburg, FL','lat': 27.7682, 'lon': -82.6534,  'tz': 'America/New_York',      'tz_offset': -5},
    'TEX': {'name': 'Globe Life Field',         'city': 'Arlington, TX',     'lat': 32.7512, 'lon': -97.0832,  'tz': 'America/Chicago',       'tz_offset': -6},
    'TOR': {'name': 'Rogers Centre',            'city': 'Toronto, ON',       'lat': 43.6414, 'lon': -79.3894,  'tz': 'America/Toronto',       'tz_offset': -5},
    'WSH': {'name': 'Nationals Park',           'city': 'Washington, DC',    'lat': 38.8730, 'lon': -77.0074,  'tz': 'America/New_York',      'tz_offset': -5},
}


def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def timezone_change(tz_from, tz_to):
    """Return timezone shift in hours (positive = traveling east, losing hours)."""
    return tz_to - tz_from


def main():
    teams = sorted(BALLPARKS.keys())
    n = len(teams)
    print(f'=== BALLPARK DISTANCE TABLE — {n} MLB PARKS ===\n')

    # Compute pairwise distances
    distances = {}
    for t1 in teams:
        for t2 in teams:
            if t1 == t2:
                distances[(t1, t2)] = 0.0
            else:
                p1, p2 = BALLPARKS[t1], BALLPARKS[t2]
                distances[(t1, t2)] = haversine(p1['lat'], p1['lon'], p2['lat'], p2['lon'])

    # Write ballpark info CSV
    info_path = os.path.join(OUTPUT_DIR, 'ballpark_info.csv')
    with open(info_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'team', 'ballpark', 'city', 'lat', 'lon', 'timezone', 'tz_offset_utc',
        ])
        writer.writeheader()
        for t in teams:
            p = BALLPARKS[t]
            writer.writerow({
                'team': t,
                'ballpark': p['name'],
                'city': p['city'],
                'lat': p['lat'],
                'lon': p['lon'],
                'timezone': p['tz'],
                'tz_offset_utc': p['tz_offset'],
            })
    print(f'Wrote {info_path}')

    # Write pairwise distance CSV (long format — easier to query)
    dist_path = os.path.join(OUTPUT_DIR, 'ballpark_distances.csv')
    rows = []
    for t1 in teams:
        for t2 in teams:
            if t1 >= t2:
                continue  # Skip self and duplicates
            d = distances[(t1, t2)]
            tz_shift = timezone_change(BALLPARKS[t1]['tz_offset'], BALLPARKS[t2]['tz_offset'])
            rows.append({
                'team_a': t1,
                'team_b': t2,
                'distance_miles': round(d, 1),
                'tz_shift_hours': tz_shift,
                'direction': 'east' if tz_shift > 0 else ('west' if tz_shift < 0 else 'same'),
            })
    rows.sort(key=lambda r: r['distance_miles'], reverse=True)

    with open(dist_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'team_a', 'team_b', 'distance_miles', 'tz_shift_hours', 'direction',
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {dist_path} ({len(rows)} pairs)\n')

    # Summary stats
    all_dists = [d for (t1, t2), d in distances.items() if t1 != t2]
    print(f'Distance stats (all {len(all_dists)} directional pairs):')
    print(f'  Min:  {min(all_dists):>7.1f} mi')
    print(f'  Max:  {max(all_dists):>7.1f} mi')
    print(f'  Mean: {sum(all_dists)/len(all_dists):>7.1f} mi')
    print()

    # Top 10 longest trips
    print('=== 10 LONGEST TRIPS ===')
    print(f'{"From":<5} {"To":<5} {"Miles":>8} {"TZ Shift":>9} {"Direction":>10}')
    print('-' * 40)
    for r in rows[:10]:
        print(f'{r["team_a"]:<5} {r["team_b"]:<5} {r["distance_miles"]:>8.1f} {r["tz_shift_hours"]:>+9d} {r["direction"]:>10}')

    # Top 10 shortest trips
    print(f'\n=== 10 SHORTEST TRIPS ===')
    print(f'{"From":<5} {"To":<5} {"Miles":>8} {"TZ Shift":>9} {"Direction":>10}')
    print('-' * 40)
    for r in rows[-10:]:
        print(f'{r["team_a"]:<5} {r["team_b"]:<5} {r["distance_miles"]:>8.1f} {r["tz_shift_hours"]:>+9d} {r["direction"]:>10}')

    # West-to-east trips (potential fatigue penalty)
    print(f'\n=== WEST-TO-EAST TRIPS (2+ timezone shift, 1000+ miles) ===')
    print(f'{"From":<5} {"To":<5} {"Miles":>8} {"TZ Shift":>9}')
    print('-' * 30)
    fatigue_trips = [r for r in rows if r['tz_shift_hours'] >= 2 and r['distance_miles'] >= 1000]
    fatigue_trips.sort(key=lambda r: r['distance_miles'], reverse=True)
    for r in fatigue_trips:
        print(f'{r["team_a"]:<5} {r["team_b"]:<5} {r["distance_miles"]:>8.1f} {r["tz_shift_hours"]:>+9d}')
    print(f'\n{len(fatigue_trips)} trips with 2+ TZ east shift and 1000+ miles')

    # Per-team average travel distance
    print(f'\n=== AVERAGE TRAVEL DISTANCE BY TEAM ===')
    print(f'{"Team":<5} {"Avg Miles":>10}')
    print('-' * 18)
    team_avgs = []
    for t in teams:
        dists = [distances[(t, t2)] for t2 in teams if t != t2]
        avg = sum(dists) / len(dists)
        team_avgs.append((t, avg))
    team_avgs.sort(key=lambda x: x[1], reverse=True)
    for t, avg in team_avgs:
        print(f'{t:<5} {avg:>10.1f}')


if __name__ == '__main__':
    main()
