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
import { PlayerStatsVizConfig, renderPlayerStats } from './player-stats.render';

@Component({
  selector: 'app-player-stats',
  standalone: true,
  templateUrl: './player-stats.component.html',
  styleUrl: './player-stats.component.css',
})
export class PlayerStatsComponent implements OnInit, AfterViewInit {
  @Input() config?: PlayerStatsVizConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private title = inject(Title);
  private meta = inject(Meta);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

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
    if (!this.config) {
      this.title.setTitle('Player Stats — Birdland Metrics');
      this.meta.updateTag({ name: 'description', content: 'Explore player career statistics across MLB seasons.' });
      this.meta.updateTag({ property: 'og:title', content: 'Player Stats — Birdland Metrics' });
      this.meta.updateTag({ property: 'og:description', content: 'Explore player career statistics across MLB seasons.' });
      this.meta.updateTag({ property: 'og:type', content: 'website' });
      this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + '/visualizations/player-stats' });
      this.seo.setCanonicalUrl('/visualizations/player-stats');
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
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderPlayerStats(container, data, cfg, d3);
    } catch (e) {
      this.loading = false;
      this.error = 'Unable to load player stats data.';
    }
  }
}
