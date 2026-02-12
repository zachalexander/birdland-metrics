import {
  Component,
  AfterViewInit,
  OnInit,
  Input,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { EloTrendConfig, renderEloTrend } from './elo-trend.render';

@Component({
  selector: 'app-elo-trend',
  standalone: true,
  templateUrl: './elo-trend.component.html',
  styleUrl: './elo-trend.component.css',
})
export class EloTrendComponent implements OnInit, AfterViewInit {
  @Input() config?: EloTrendConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private title = inject(Title);
  private meta = inject(Meta);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

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
      this.title.setTitle('ELO Trends — Birdland Metrics');
      this.meta.updateTag({ name: 'description', content: 'Track ELO rating trends throughout the MLB season.' });
      this.meta.updateTag({ property: 'og:title', content: 'ELO Trends — Birdland Metrics' });
      this.meta.updateTag({ property: 'og:description', content: 'Track ELO rating trends throughout the MLB season.' });
      this.meta.updateTag({ property: 'og:type', content: 'website' });
      this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + '/visualizations/elo-trends' });
      this.seo.setCanonicalUrl('/visualizations/elo-trends');
      this.seo.setJsonLd(this.seo.getOrganizationSchema());
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
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderEloTrend(container, data, cfg, d3);
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load ELO data. The season may not have started yet.';
    }
  }
}
