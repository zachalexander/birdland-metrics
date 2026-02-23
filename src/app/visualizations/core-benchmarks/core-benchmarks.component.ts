import { Component, input, computed, signal, inject } from '@angular/core';
import { BenchmarkPlayer, PlayerBenchmark } from '../../shared/models/mlb.models';
import { AnalyticsService } from '../../core/services/analytics.service';

@Component({
  selector: 'app-core-benchmarks',
  standalone: true,
  templateUrl: './core-benchmarks.component.html',
  styleUrl: './core-benchmarks.component.css',
})
export class CoreBenchmarksComponent {
  private analytics = inject(AnalyticsService);
  players = input.required<BenchmarkPlayer[]>();
  updated = input<string | null>(null);
  overrideStats = input<Record<string, Record<string, number | null>>>({});
  showOverride = input(false);

  formattedUpdated = computed(() => {
    const raw = this.updated();
    if (!raw) return null;
    const d = new Date(raw + 'Z');
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
    '669062': '39',  // Kyle Bradish
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
    '669062': 'assets/kyle-bradish.png',
    '669358': 'assets/shane-baz.png',
    '664854': 'assets/ryan-helsley.png',
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
    hr_pace: 'Home runs projected over a full 162-game season',
    obp: 'On-base percentage — how often a batter reaches base',
    bb_pct: 'Walk rate as a percentage of plate appearances',
    ops: 'On-base plus slugging — a combined hitting metric',
    iso: 'Isolated power — slugging minus batting average',
    games_pace: 'Games projected over a full 162-game season',
    k_pct: 'Strikeout rate as a percentage of plate appearances',
    hard_pct: 'Percentage of batted balls hit 95+ mph',
    exit_velo: 'Average speed of the ball off the bat in mph',
    slg: 'Slugging percentage — total bases per at-bat',
    avg: 'Batting average — hits per at-bat',
    era: 'Earned run average — earned runs allowed per nine innings',
    k_per_9: 'Strikeouts per nine innings pitched',
    ip_pace: 'Innings pitched projected over a full season',
    whip: 'Walks plus hits per inning pitched',
    fip: 'Fielding independent pitching — ERA estimator based on K, BB, HR',
    sv_pace: 'Saves projected over a full season',
  };

  tooltip(key: string): string | null {
    return CoreBenchmarksComponent.GLOSSARY[key] ?? null;
  }

  batters = computed(() => this.players().filter(p => p.type === 'batter'));
  pitchers = computed(() => this.players().filter(p => p.type === 'pitcher'));

  mobileFilter = signal('all');

  onMobileFilterChange(value: string): void {
    this.mobileFilter.set(value);
    this.analytics.trackEvent('viz_interaction', { viz: 'core_benchmarks', action: 'filter', value });
  }

  filteredBatters = computed(() => {
    const filter = this.mobileFilter();
    const list = this.batters();
    if (filter === 'all' || filter === 'batters') return list;
    if (filter === 'pitchers') return [];
    return list.filter(p => p.playerId === filter);
  });

  filteredPitchers = computed(() => {
    const filter = this.mobileFilter();
    const list = this.pitchers();
    if (filter === 'all' || filter === 'pitchers') return list;
    if (filter === 'batters') return [];
    return list.filter(p => p.playerId === filter);
  });

  totalBenchmarks = computed(() =>
    this.players().reduce((sum, p) => sum + p.benchmarks.length, 0)
  );

  totalMet = computed(() => {
    if (this.showOverride()) {
      const stats = this.overrideStats();
      return this.players().reduce(
        (sum, p) => sum + p.benchmarks.filter(b => {
          const val = stats[p.playerId]?.[b.key] ?? null;
          if (val === null) return false;
          return b.direction === 'gte' ? val >= b.target : val <= b.target;
        }).length,
        0
      );
    }
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
    if (!this.showOverride()) return benchmark.met;
    const val = this.overrideStats()[playerId]?.[benchmark.key] ?? null;
    if (val === null) return false;
    return benchmark.direction === 'gte' ? val >= benchmark.target : val <= benchmark.target;
  }

  playerMetCount(player: BenchmarkPlayer): number {
    return player.benchmarks.filter(b => this.isMet(player.playerId, b)).length;
  }

  formatValue(playerId: string, benchmark: PlayerBenchmark): string {
    if (!benchmark) return 'N/A';
    const v = this.showOverride()
      ? (this.overrideStats()[playerId]?.[benchmark.key] ?? null)
      : benchmark.current;

    if (v === null) return 'N/A';

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
}
