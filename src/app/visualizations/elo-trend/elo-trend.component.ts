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
import { EloTrendConfig, renderEloTrend } from './elo-trend.render';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';

@Component({
  selector: 'app-elo-trend',
  standalone: true,
  imports: [ShareButtonsComponent],
  templateUrl: './elo-trend.component.html',
  styleUrl: './elo-trend.component.css',
})
export class EloTrendComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() config?: EloTrendConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

  private lastD3: typeof import('d3') | null = null;
  private lastData: Record<string, import('./elo-trend.render').EloTrendDataPoint[]> | null = null;
  private themeHandler?: () => void;

  private get resolvedConfig(): EloTrendConfig {
    return this.config ?? {
      teams: ['BAL'],
      season: new Date().getFullYear(),
      title: 'ELO Rating Trend',
    };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (!this.config) {
      this.seo.setPageMeta({
        title: 'ELO Trends — Birdland Metrics',
        description: 'Track ELO rating trends throughout the MLB season.',
        path: '/visualizations/elo-trends',
      });
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
    }

    if (this.isBrowser) {
      this.themeHandler = () => this.rerender();
      window.addEventListener('theme-changed', this.themeHandler);
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, data] = await Promise.all([
        import('d3'),
        this.mlbData.getEloHistory(cfg.teams, cfg.season),
      ]);

      this.loading = false;
      this.lastD3 = d3;
      this.lastData = data;
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderEloTrend(container, data, cfg, d3);
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load ELO data. The season may not have started yet.';
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
    renderEloTrend(container, this.lastData, this.resolvedConfig, this.lastD3);
  }
}
