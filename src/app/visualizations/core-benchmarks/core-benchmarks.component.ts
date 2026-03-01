import { Component, input, computed, signal, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BenchmarkPlayer, PlayerBenchmark } from '../../shared/models/mlb.models';
import { AnalyticsService } from '../../core/services/analytics.service';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';
import { slugForPlayerId } from './player-slugs';

@Component({
  selector: 'app-core-benchmarks',
  standalone: true,
  imports: [ShareButtonsComponent, RouterLink],
  templateUrl: './core-benchmarks.component.html',
  styleUrl: './core-benchmarks.component.css',
})
export class CoreBenchmarksComponent {
  private analytics = inject(AnalyticsService);
  players = input.required<BenchmarkPlayer[]>();
  updated = input<string | null>(null);
  focusedPlayerId = input<string | null>(null);

  formattedUpdated = computed(() => {
    const raw = this.updated();
    if (!raw) return null;
    const d = new Date(raw.endsWith('Z') ? raw : raw + 'Z');
    const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'America/New_York' });
    const day = d.getDate();
    const year = d.getFullYear();
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
    return `${month} ${day}, ${year} at ${time} ET`;
  });

  private static readonly JERSEY_NUMBERS: Record<string, string> = {
    '683002': '2',   // Gunnar Henderson
    '668939': '35',  // Adley Rutschman
    '682614': '11',  // Jordan Westburg
    '681297': '17',  // Colton Cowser
    '624413': '25',  // Pete Alonso
    '696137': '7',   // Jackson Holliday
    '680694': '39',  // Kyle Bradish
    '669432': '28',  // Trevor Rogers
    '669358': '34',  // Shane Baz
    '664854': '21',  // Ryan Helsley
    'bullpen': 'BP',  // Team Bullpen
  };

  private static readonly AVATARS: Record<string, string> = {
    '683002': 'assets/gunnar-henderson.png',
    '668939': 'assets/adley-rutschman.png',
    '682614': 'assets/jordan-westburg.png',
    '681297': 'assets/colton-cowser.png',
    '624413': 'assets/pete-alonso.png',
    '696137': 'assets/jackson-holliday.png',
    '669432': 'assets/trevor-rogers.png',
    '680694': 'assets/kyle-bradish.png',
    '669358': 'assets/shane-baz.png',
    '664854': 'assets/ryan-helsley.png',
  };

  private static readonly STATS_2025: Record<string, Record<string, number | null>> = {
    // Gunnar Henderson: .274/.349/.438, 17 HR, 154 G
    '683002': { barrel_pct: 8.5, wrc_plus: 120, hr_pace: 17 },
    // Adley Rutschman: .220/.307/.366, 9 HR, 90 G
    '668939': { obp: 0.307, bb_pct: 11.0, wrc_plus: 91 },
    // Jordan Westburg: .265/.312/.457, 17 HR, 85 G, 115 wRC+
    '682614': { slg: 0.457, games_pace: 85, wrc_plus: 115 },
    // Colton Cowser: .196/.269/.385, 16 HR, 91 G, 14.1% Barrel
    '681297': { k_pct: 35.6, barrel_pct: 14.1, wrc_plus: 83 },
    // Pete Alonso (NYM 2025): .264/.329/.524, 38 HR, 18.9% Barrel
    '624413': { hr_pace: 38, barrel_pct: 18.9, slg: 0.524 },
    // Jackson Holliday: .242/.314/.375, 17 HR, 149 G
    '696137': { k_pct: 21.6, bb_pct: 8.6, obp: 0.314 },
    // Kyle Bradish: 2.53 ERA, 13.22 K/9, 32.0 IP
    '680694': { era: 2.53, k_per_9: 13.22, ip_pace: 32 },
    // Trevor Rogers: 1.81 ERA, 0.90 WHIP, 109 IP
    '669432': { era: 1.81, whip: 0.90, ip_pace: 109 },
    // Shane Baz (TB 2025): 4.87 ERA, 4.37 FIP, 166.1 IP
    '669358': { era: 4.87, fip: 4.37, ip_pace: 166 },
    // Ryan Helsley (STL 2025): 4.50 ERA, 10.13 K/9, 21 SV
    '664854': { era: 4.50, k_per_9: 10.13, sv_pace: 21 },
    // Team Bullpen
    'bullpen': { era: 4.87, k_per_9: 9.0, whip: 1.56 },
  };

  private static readonly INJURIES: Record<string, { diagnosis: string; returnDate: string }> = {
    '682614': { diagnosis: 'Partial UCL tear', returnDate: 'Back ~May' },
    '696137': { diagnosis: 'Broken hamate', returnDate: 'Back ~mid-April' },
  };

  isInjured(playerId: string): boolean {
    return playerId in CoreBenchmarksComponent.INJURIES;
  }

  injuryInfo(playerId: string): { diagnosis: string; returnDate: string } | null {
    return CoreBenchmarksComponent.INJURIES[playerId] ?? null;
  }

  private static readonly GLOSSARY: Record<string, string> = {
    barrel_pct: 'Percentage of batted balls with ideal exit velocity and launch angle',
    wrc_plus: 'Weighted runs created, adjusted for park and league (100 = average)',
    hr_pace: 'Total home runs hit this season',
    obp: 'On-base percentage — how often a batter reaches base',
    bb_pct: 'Walk rate as a percentage of plate appearances',
    ops: 'On-base plus slugging — a combined hitting metric',
    iso: 'Isolated power — slugging minus batting average',
    games_pace: 'Total games played this season',
    k_pct: 'Strikeout rate as a percentage of plate appearances',
    hard_pct: 'Percentage of batted balls hit 95+ mph',
    exit_velo: 'Average speed of the ball off the bat in mph',
    slg: 'Slugging percentage — total bases per at-bat',
    avg: 'Batting average — hits per at-bat',
    era: 'Earned run average — earned runs allowed per nine innings',
    k_per_9: 'Strikeouts per nine innings pitched',
    ip_pace: 'Total innings pitched this season',
    whip: 'Walks plus hits per inning pitched',
    fip: 'Fielding independent pitching — ERA estimator based on K, BB, HR',
    sv_pace: 'Total saves recorded this season',
  };

  tooltip(key: string): string | null {
    return CoreBenchmarksComponent.GLOSSARY[key] ?? null;
  }

  private isCorePlayers(playerId: string): boolean {
    return playerId in CoreBenchmarksComponent.JERSEY_NUMBERS;
  }

  batters = computed(() => this.players().filter(p => p.type === 'batter' && this.isCorePlayers(p.playerId)));
  pitchers = computed(() => this.players().filter(p => p.type === 'pitcher' && this.isCorePlayers(p.playerId)));

  mobileFilter = signal('all');

  onMobileFilterChange(value: string): void {
    this.mobileFilter.set(value);
    this.analytics.trackEvent('viz_interaction', { viz: 'core_benchmarks', action: 'filter', value });
  }

  filteredBatters = computed(() => {
    const focused = this.focusedPlayerId();
    if (focused) return this.batters().filter(p => p.playerId === focused);
    const filter = this.mobileFilter();
    const list = this.batters();
    if (filter === 'all' || filter === 'batters') return list;
    if (filter === 'pitchers') return [];
    return list.filter(p => p.playerId === filter);
  });

  filteredPitchers = computed(() => {
    const focused = this.focusedPlayerId();
    if (focused) return this.pitchers().filter(p => p.playerId === focused);
    const filter = this.mobileFilter();
    const list = this.pitchers();
    if (filter === 'all' || filter === 'pitchers') return list;
    if (filter === 'batters') return [];
    return list.filter(p => p.playerId === filter);
  });

  playerSharePath(playerId: string): string {
    const slug = slugForPlayerId(playerId);
    return slug ? `/visualizations/core-benchmarks/${slug}` : '/visualizations/core-benchmarks';
  }

  totalBenchmarks = computed(() =>
    this.players().reduce((sum, p) => sum + p.benchmarks.length, 0)
  );

  totalMet = computed(() => {
    return this.players().reduce(
      (sum, p) => sum + p.benchmarks.filter(b => b.met).length,
      0
    );
  });

  progressPct = computed(() => {
    const total = this.totalBenchmarks();
    return total > 0 ? Math.round((this.totalMet() / total) * 100) : 0;
  });

  jerseyNumber(playerId: string): string {
    return CoreBenchmarksComponent.JERSEY_NUMBERS[playerId] ?? '';
  }

  avatarUrl(playerId: string): string | null {
    return CoreBenchmarksComponent.AVATARS[playerId] ?? null;
  }

  isMet(playerId: string, benchmark: PlayerBenchmark): boolean {
    if (!benchmark) return false;
    return benchmark.met;
  }

  playerMetCount(player: BenchmarkPlayer): number {
    return player.benchmarks.filter(b => this.isMet(player.playerId, b)).length;
  }

  formatValue(playerId: string, benchmark: PlayerBenchmark): string {
    if (!benchmark) return '--';
    const v = benchmark.current;

    if (v === null) return '--';

    switch (benchmark.key) {
      case 'obp':
      case 'slg':
      case 'ops':
      case 'avg':
      case 'iso':
        return v.toFixed(3);
      case 'barrel_pct':
      case 'hard_pct':
      case 'bb_pct':
      case 'k_pct':
        return v.toFixed(1) + '%';
      case 'exit_velo':
        return v.toFixed(1) + ' mph';
      case 'era':
      case 'fip':
      case 'whip':
        return v.toFixed(2);
      case 'k_per_9':
        return v.toFixed(1);
      case 'wrc_plus':
        return v.toFixed(0);
      case 'hr_pace':
      case 'games_pace':
      case 'ip_pace':
      case 'sv_pace':
        return v.toFixed(0);
      default:
        return String(v);
    }
  }

  format2025Value(playerId: string, benchmark: PlayerBenchmark): string | null {
    const v = CoreBenchmarksComponent.STATS_2025[playerId]?.[benchmark.key] ?? null;
    if (v === null) return null;

    switch (benchmark.key) {
      case 'obp':
      case 'slg':
      case 'ops':
      case 'avg':
      case 'iso':
        return v.toFixed(3);
      case 'barrel_pct':
      case 'hard_pct':
      case 'bb_pct':
      case 'k_pct':
        return v.toFixed(1) + '%';
      case 'exit_velo':
        return v.toFixed(1) + ' mph';
      case 'era':
      case 'fip':
      case 'whip':
        return v.toFixed(2);
      case 'k_per_9':
        return v.toFixed(1);
      case 'wrc_plus':
      case 'hr_pace':
      case 'games_pace':
      case 'ip_pace':
      case 'sv_pace':
        return v.toFixed(0);
      default:
        return String(v);
    }
  }

  was2025Met(playerId: string, benchmark: PlayerBenchmark): boolean {
    const v = CoreBenchmarksComponent.STATS_2025[playerId]?.[benchmark.key] ?? null;
    if (v === null) return false;
    return benchmark.direction === 'gte' ? v >= benchmark.target : v <= benchmark.target;
  }

  private static readonly ACTUAL_LABELS: Record<string, string> = {
    hr_pace: 'HR',
    ip_pace: 'IP',
    games_pace: 'G',
    sv_pace: 'SV',
  };

  formatActual(benchmark: PlayerBenchmark): string | null {
    if (!benchmark?.actual) return null;
    const label = CoreBenchmarksComponent.ACTUAL_LABELS[benchmark.key];
    if (!label) return null;
    const val = Number.isInteger(benchmark.actual)
      ? benchmark.actual.toFixed(0)
      : benchmark.actual.toFixed(1);
    return `${val} ${label}`;
  }

  formatRosProjected(benchmark: PlayerBenchmark): string | null {
    const v = benchmark.rosProjected;
    if (v === null || v === undefined) return null;

    switch (benchmark.key) {
      case 'obp':
      case 'slg':
      case 'ops':
      case 'avg':
      case 'iso':
        return v.toFixed(3);
      case 'barrel_pct':
      case 'hard_pct':
      case 'bb_pct':
      case 'k_pct':
        return v.toFixed(1) + '%';
      case 'exit_velo':
        return v.toFixed(1) + ' mph';
      case 'era':
      case 'fip':
      case 'whip':
        return v.toFixed(2);
      case 'k_per_9':
        return v.toFixed(1);
      case 'wrc_plus':
      case 'hr_pace':
      case 'games_pace':
      case 'ip_pace':
      case 'sv_pace':
        return v.toFixed(0);
      default:
        return String(v);
    }
  }

  isRosProjectionMet(benchmark: PlayerBenchmark): boolean | null {
    const v = benchmark.rosProjected;
    if (v === null || v === undefined) return null;
    return benchmark.direction === 'gte' ? v >= benchmark.target : v <= benchmark.target;
  }
}
