import {
  Component,
  AfterViewInit,
  OnInit,
  Input,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { TEAM_NAMES, TeamProjection } from '../../shared/models/mlb.models';
import { TEAM_COLORS } from '../viz-utils';
import { WinDistributionConfig, renderWinDistribution } from './win-dist.render';

@Component({
  selector: 'app-win-distribution',
  standalone: true,
  templateUrl: './win-distribution.component.html',
  styleUrl: './win-distribution.component.css',
})
export class WinDistributionComponent implements OnInit, AfterViewInit {
  @Input() config?: WinDistributionConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private title = inject(Title);
  private meta = inject(Meta);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

  selectedTeam = signal('BAL');
  teamOptions = signal<{ abbr: string; name: string }[]>([]);

  private projections: TeamProjection[] = [];
  private d3Module: typeof import('d3') | null = null;

  private get resolvedConfig(): WinDistributionConfig {
    return this.config ?? {
      teams: ['BAL'],
      title: 'Projected Win Distribution',
    };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (!this.config) {
      this.title.setTitle('Win Distribution — Birdland Metrics');
      this.meta.updateTag({ name: 'description', content: 'Projected win distribution curves for MLB teams.' });
      this.meta.updateTag({ property: 'og:title', content: 'Win Distribution — Birdland Metrics' });
      this.meta.updateTag({ property: 'og:description', content: 'Projected win distribution curves for MLB teams.' });
      this.meta.updateTag({ property: 'og:type', content: 'website' });
      this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + '/visualizations/win-distribution' });
      this.seo.setCanonicalUrl('/visualizations/win-distribution');
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, projections] = await Promise.all([
        import('d3'),
        this.mlbData.getProjections(),
      ]);

      this.d3Module = d3;
      this.projections = projections;
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
    this.renderChart();
  }

  private renderChart(): void {
    const container = this.chartContainer()?.nativeElement;
    if (!container || !this.d3Module) return;

    const cfg = this.resolvedConfig;
    const activeTeam = cfg.teams.length > 1 ? this.selectedTeam() : cfg.teams[0];

    renderWinDistribution(container, this.projections, { ...cfg, teams: [activeTeam] }, this.d3Module);
  }
}
