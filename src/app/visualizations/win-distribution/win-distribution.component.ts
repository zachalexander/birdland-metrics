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
import { isPlatformBrowser } from '@angular/common';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { TEAM_NAMES, TeamProjection } from '../../shared/models/mlb.models';
import { TEAM_COLORS, VizColorTheme } from '../viz-utils';
import { WinDistributionConfig, renderWinDistribution } from './win-dist.render';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';

@Component({
  selector: 'app-win-distribution',
  standalone: true,
  imports: [ShareButtonsComponent],
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
  isBrowser = false;
  loading = true;
  error = '';

  selectedTeam = signal('BAL');
  teamOptions = signal<{ abbr: string; name: string }[]>([]);

  private loadedProjections: TeamProjection[] = [];
  private d3Module: typeof import('d3') | null = null;
  private themeHandler?: () => void;

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
    if (this.isBrowser) {
      this.themeHandler = () => this.renderChart();
      window.addEventListener('theme-changed', this.themeHandler);
    }

    if (!this.config) {
      this.seo.setPageMeta({
        title: 'Win Distribution — Birdland Metrics',
        description: 'Projected win distribution curves for MLB teams.',
        path: '/visualizations/win-distribution',
      });
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, projections] = await Promise.all([
        import('d3'),
        this.projections
          ? Promise.resolve(this.projections)
          : this.mlbData.getProjections(),
      ]);

      this.d3Module = d3;
      this.loadedProjections = projections;
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
