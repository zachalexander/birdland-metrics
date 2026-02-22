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
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { PlayerStatsVizConfig, renderPlayerStats } from './player-stats.render';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';

@Component({
  selector: 'app-player-stats',
  standalone: true,
  imports: [ShareButtonsComponent],
  templateUrl: './player-stats.component.html',
  styleUrl: './player-stats.component.css',
})
export class PlayerStatsComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() config?: PlayerStatsVizConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

  private lastD3: typeof import('d3') | null = null;
  private lastData: import('../../shared/models/mlb.models').PlayerSeasonStats[] | null = null;
  private themeHandler?: () => void;

  private get resolvedConfig(): PlayerStatsVizConfig {
    return this.config ?? {
      playerId: 'hendegu01',
      metrics: ['war', 'wrc_plus'],
      title: 'Player Career Stats',
    };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (this.isBrowser) {
      this.themeHandler = () => this.rerender();
      window.addEventListener('theme-changed', this.themeHandler);
    }

    if (!this.config) {
      this.seo.setPageMeta({
        title: 'Player Stats — Birdland Metrics',
        description: 'Explore player career statistics across MLB seasons.',
        path: '/visualizations/player-stats',
      });
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, data] = await Promise.all([
        import('d3'),
        this.mlbData.getPlayerCareerStats(cfg.playerId),
      ]);

      this.loading = false;
      this.lastD3 = d3;
      this.lastData = data;
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderPlayerStats(container, data, cfg, d3);
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load player stats data.';
    }
  }

  ngOnDestroy(): void {
    if (this.themeHandler && this.isBrowser) {
      window.removeEventListener('theme-changed', this.themeHandler);
    }
  }

  private rerender(): void {
    if (!this.lastD3 || !this.lastData) return;
    const container = this.chartContainer()?.nativeElement;
    if (!container) return;
    container.innerHTML = '';
    renderPlayerStats(container, this.lastData, this.resolvedConfig, this.lastD3);
  }
}
