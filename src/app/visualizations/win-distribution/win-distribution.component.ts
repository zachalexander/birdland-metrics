import {
  Component,
  AfterViewInit,
  OnInit,
  OnDestroy,
  Input,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
  signal,
} from '@angular/core';
import { isPlatformBrowser, DecimalPipe } from '@angular/common';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { environment } from '../../../environments/environment';
import { TEAM_NAMES, TeamProjection } from '../../shared/models/mlb.models';
import { TEAM_COLORS, VizColorTheme } from '../viz-utils';
import { WinDistributionConfig, renderWinDistribution } from './win-dist.render';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';

@Component({
  selector: 'app-win-distribution',
  standalone: true,
  imports: [DecimalPipe, ShareButtonsComponent, NewsletterCtaComponent],
  templateUrl: './win-distribution.component.html',
  styleUrl: './win-distribution.component.css',
})
export class WinDistributionComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() config?: WinDistributionConfig;
  @Input() projections?: TeamProjection[];
  @Input() theme?: VizColorTheme;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  private analytics = inject(AnalyticsService);
  isBrowser = false;
  loading = true;
  error = '';

  selectedTeam = signal('BAL');
  teamOptions = signal<{ abbr: string; name: string }[]>([]);
  updatedDate = signal<string | null>(null);
  balProjection = signal<TeamProjection | null>(null);

  private loadedProjections: TeamProjection[] = [];
  private d3Module: typeof import('d3') | null = null;
  private themeHandler?: () => void;

  private get resolvedConfig(): WinDistributionConfig {
    return this.config ?? {
      teams: ['BAL'],
    };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (this.isBrowser) {
      this.themeHandler = () => this.renderChart();
      window.addEventListener('theme-changed', this.themeHandler);
    }

    if (!this.config) {
      this.seo.setPageMeta({
        title: 'Win Distribution — Birdland Metrics',
        description: 'Baltimore Orioles 2026 projected win distribution from 10,000 simulated seasons. See the full range of likely outcomes and playoff probability.',
        path: '/visualizations/win-distribution',
        image: `${environment.s3.ogImages}/win-distribution.png`,
      });
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, projectionsResult] = await Promise.all([
        import('d3'),
        this.projections
          ? Promise.resolve({ updated: '', projections: this.projections })
          : this.mlbData.getProjectionsWithMeta(),
      ]);

      this.d3Module = d3;
      this.loadedProjections = projectionsResult.projections;
      if (projectionsResult.updated) {
        const d = new Date(projectionsResult.updated + 'Z');
        const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'America/New_York' });
        const day = d.getDate();
        const year = d.getFullYear();
        const s = ['th', 'st', 'nd', 'rd'];
        const v = day % 100;
        const suffix = s[(v - 20) % 10] || s[v] || s[0];
        const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
        this.updatedDate.set(`${month} ${day}${suffix}, ${year} \u00B7 ${time} ET`);
      }
      const bal = projectionsResult.projections.find(p => p.team === 'BAL');
      if (bal) this.balProjection.set(bal);
      this.loading = false;

      // Build dropdown options from config teams
      if (cfg.teams.length > 1) {
        this.teamOptions.set(cfg.teams.map(abbr => ({
          abbr,
          name: TEAM_NAMES[abbr] ?? abbr,
        })));
        this.selectedTeam.set(cfg.teams[0]);
      }

      this.renderChart();
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load projection data.';
    }
  }

  teamColor(abbr: string): string {
    return TEAM_COLORS[abbr] ?? '#333';
  }

  onTeamChange(abbr: string): void {
    this.selectedTeam.set(abbr);
    this.analytics.trackEvent('viz_interaction', { viz: 'win_distribution', action: 'team_change', team: abbr });
    this.renderChart();
  }

  ngOnDestroy(): void {
    if (this.themeHandler && this.isBrowser) {
      window.removeEventListener('theme-changed', this.themeHandler);
    }
  }

  private renderChart(): void {
    const container = this.chartContainer()?.nativeElement;
    if (!container || !this.d3Module) return;

    const cfg = this.resolvedConfig;
    const activeTeam = cfg.teams.length > 1 ? this.selectedTeam() : cfg.teams[0];

    renderWinDistribution(container, this.loadedProjections, { ...cfg, teams: [activeTeam], theme: this.theme }, this.d3Module);
  }
}
