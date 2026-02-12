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

      this.loading = false;
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderWinDistribution(container, projections, cfg, d3);
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load projection data.';
    }
  }
}
