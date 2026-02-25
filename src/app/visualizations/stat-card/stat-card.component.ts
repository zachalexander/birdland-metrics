import { Component, OnInit, ElementRef, viewChild, inject, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { PlayoffOdds, TeamProjection, BenchmarkPlayer, PlayerBenchmark } from '../../shared/models/mlb.models';
import {
  CardType,
  ProjectionStat,
  PROJECTION_STAT_OPTIONS,
  FULL_TEAM_NAMES,
} from './stat-card.models';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './stat-card.component.html',
  styleUrl: './stat-card.component.css',
})
export class StatCardComponent implements OnInit {
  cardPreview = viewChild<ElementRef>('cardPreview');

  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  private analytics = inject(AnalyticsService);

  isBrowser = false;
  loading = signal(true);

  // Card type
  cardType = signal<CardType>('projections');

  // Projection controls
  readonly projectionStatOptions = PROJECTION_STAT_OPTIONS;
  selectedTeam = 'BAL';
  selectedProjectionStat: ProjectionStat = 'playoff_pct';
  teamOptions = signal<{ abbr: string; name: string }[]>([]);

  // Player stats controls
  playerOptions = signal<{ id: string; name: string }[]>([]);
  selectedPlayer = '';
  benchmarkOptions = signal<{ key: string; label: string }[]>([]);
  selectedBenchmark = '';

  // Custom controls
  customHeadline = '';
  customStatValue = '';
  customStatLabel = '';
  customContext = '';
  customSubtext = '';

  // Data
  private playoffOdds: PlayoffOdds[] = [];
  private projections: TeamProjection[] = [];
  private benchmarkPlayers: BenchmarkPlayer[] = [];
  private projectionsUpdated = '';
  private oddsUpdated = '';
  private benchmarksUpdated = '';
  private simulations = 0;

  // Computed card content
  cardHeadline = signal('');
  cardStatValue = signal('');
  cardStatLabel = signal('');
  cardContext = signal('');
  cardSubtext = signal('');

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Stat Card Generator — Birdland Metrics',
      description: 'Generate on-brand stat card images for social media sharing.',
      path: '/visualizations/stat-card',
    });
    this.seo.setJsonLd(this.seo.getOrganizationSchema());

    if (this.isBrowser) {
      this.loadData();
    } else {
      this.loading.set(false);
    }
  }

  private async loadData(): Promise<void> {
    try {
      const [oddsResult, projectionsResult, benchmarksResult] = await Promise.all([
        this.mlbData.getPlayoffOdds(),
        this.mlbData.getProjectionsWithMeta(),
        this.mlbData.getCoreBenchmarks(),
      ]);

      this.playoffOdds = oddsResult.odds;
      this.oddsUpdated = oddsResult.updated;
      this.simulations = (oddsResult as any).simulations ?? 10000;

      this.projections = projectionsResult.projections;
      this.projectionsUpdated = projectionsResult.updated;

      this.benchmarkPlayers = benchmarksResult.players;
      this.benchmarksUpdated = benchmarksResult.updated;

      // Build team options from odds data
      const teams = this.playoffOdds.map((o) => ({
        abbr: o.team,
        name: FULL_TEAM_NAMES[o.team] ?? o.team,
      }));
      teams.sort((a, b) => a.name.localeCompare(b.name));
      this.teamOptions.set(teams);

      // Build player options
      const players = this.benchmarkPlayers.map((p) => ({
        id: p.playerId,
        name: p.name,
      }));
      this.playerOptions.set(players);
      if (players.length > 0) {
        this.selectedPlayer = players[0].id;
        this.updateBenchmarkOptions();
      }

      this.updateCardContent();
    } catch (e) {
      console.error('Failed to load stat card data:', e);
    } finally {
      this.loading.set(false);
    }
  }

  setCardType(type: CardType): void {
    if (this.cardType() === type) return;
    this.cardType.set(type);
    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'type_change',
      value: type,
    });
    this.updateCardContent();
  }

  onTeamChange(): void {
    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'team_change',
      value: this.selectedTeam,
    });
    this.updateCardContent();
  }

  onProjectionStatChange(): void {
    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'stat_change',
      value: this.selectedProjectionStat,
    });
    this.updateCardContent();
  }

  onPlayerChange(): void {
    this.updateBenchmarkOptions();
    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'player_change',
      value: this.selectedPlayer,
    });
    this.updateCardContent();
  }

  onBenchmarkChange(): void {
    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'benchmark_change',
      value: this.selectedBenchmark,
    });
    this.updateCardContent();
  }

  onCustomFieldChange(): void {
    this.updateCardContent();
  }

  private updateBenchmarkOptions(): void {
    const player = this.benchmarkPlayers.find((p) => p.playerId === this.selectedPlayer);
    if (!player) return;
    const opts = player.benchmarks.map((b) => ({ key: b.key, label: b.label }));
    this.benchmarkOptions.set(opts);
    if (opts.length > 0 && !opts.find((o) => o.key === this.selectedBenchmark)) {
      this.selectedBenchmark = opts[0].key;
    }
  }

  updateCardContent(): void {
    const type = this.cardType();

    if (type === 'projections') {
      this.updateProjectionCard();
    } else if (type === 'player-stats') {
      this.updatePlayerStatsCard();
    } else {
      this.updateCustomCard();
    }
  }

  private updateProjectionCard(): void {
    const odds = this.playoffOdds.find((o) => o.team === this.selectedTeam);
    const proj = this.projections.find((p) => p.team === this.selectedTeam);
    const statOpt = PROJECTION_STAT_OPTIONS.find((o) => o.key === this.selectedProjectionStat);
    const teamName = FULL_TEAM_NAMES[this.selectedTeam] ?? this.selectedTeam;

    this.cardHeadline.set(statOpt?.contextLabel ?? '');
    this.cardStatLabel.set(teamName);

    if (this.selectedProjectionStat === 'win_total') {
      const wins = proj ? proj.median_wins.toFixed(0) : '—';
      this.cardStatValue.set(wins);
      this.cardContext.set(
        proj ? `Range: ${proj.p10}–${proj.p90} wins (10th–90th percentile)` : '',
      );
      this.cardSubtext.set(this.projectionsUpdated ? `Updated ${this.projectionsUpdated}` : '');
    } else {
      const val = odds ? odds[this.selectedProjectionStat].toFixed(1) + '%' : '—';
      this.cardStatValue.set(val);
      this.cardContext.set(
        this.simulations
          ? `Based on ${this.simulations.toLocaleString()} simulated seasons`
          : '',
      );
      this.cardSubtext.set(this.oddsUpdated ? `Updated ${this.oddsUpdated}` : '');
    }
  }

  private updatePlayerStatsCard(): void {
    const player = this.benchmarkPlayers.find((p) => p.playerId === this.selectedPlayer);
    if (!player) return;

    const benchmark = player.benchmarks.find((b) => b.key === this.selectedBenchmark);
    if (!benchmark) return;

    this.cardHeadline.set(benchmark.label);
    this.cardStatValue.set(this.formatBenchmarkValue(benchmark));
    this.cardStatLabel.set(player.name);
    this.cardContext.set(
      benchmark.target != null
        ? `Target: ${this.formatTarget(benchmark)}`
        : '',
    );
    this.cardSubtext.set(this.benchmarksUpdated ? `Updated ${this.benchmarksUpdated}` : '');
  }

  private updateCustomCard(): void {
    this.cardHeadline.set(this.customHeadline || 'Headline');
    this.cardStatValue.set(this.customStatValue || '0');
    this.cardStatLabel.set(this.customStatLabel || 'Label');
    this.cardContext.set(this.customContext || '');
    this.cardSubtext.set(this.customSubtext || '');
  }

  private formatBenchmarkValue(b: PlayerBenchmark): string {
    if (b.current === null) return 'N/A';
    const v = b.current;
    switch (b.key) {
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

  private formatTarget(b: PlayerBenchmark): string {
    const dir = b.direction === 'gte' ? '≥' : '≤';
    // Format target the same way as values
    const formatted = this.formatBenchmarkValue({ ...b, current: b.target });
    return `${dir} ${formatted}`;
  }

  async downloadCard(): Promise<void> {
    const el = this.cardPreview()?.nativeElement;
    if (!el) return;

    this.analytics.trackEvent('viz_interaction', {
      viz: 'stat_card',
      action: 'download',
      value: this.cardType(),
    });
    this.analytics.trackEvent('stat_card_download', {
      card_type: this.cardType(),
    });

    try {
      // Temporarily remove scale transform so html2canvas captures at full 1200x630
      const savedTransform = el.style.transform;
      el.style.transform = 'none';

      const mod = await import('html2canvas');
      const renderFn = (mod as any).default ?? mod;
      const canvas = await renderFn(el, {
        width: 1200,
        height: 630,
        scale: 1,
        useCORS: true,
        backgroundColor: '#1a1a1f',
      });

      el.style.transform = savedTransform;

      const link = document.createElement('a');
      link.download = `birdland-stat-card-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (err) {
      console.error('Failed to generate PNG:', err);
    }
  }
}
