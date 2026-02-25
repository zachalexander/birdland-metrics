import {
  Directive,
  ElementRef,
  AfterViewInit,
  OnDestroy,
  PLATFORM_ID,
  inject,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { MlbDataService } from '../../core/services/mlb-data.service';

@Directive({
  selector: '[appVizHost]',
  standalone: true,
})
export class VizHostDirective implements AfterViewInit, OnDestroy {
  private el = inject(ElementRef);
  private platformId = inject(PLATFORM_ID);
  private mlbData = inject(MlbDataService);
  private observer: MutationObserver | null = null;

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    this.observer = new MutationObserver(() => this.scanAndRender());
    this.observer.observe(this.el.nativeElement, { childList: true, subtree: true });

    // Initial scan in case innerHTML is already set
    this.scanAndRender();
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  private async scanAndRender(): Promise<void> {
    const host: HTMLElement = this.el.nativeElement;
    const placeholders = host.querySelectorAll<HTMLElement>('.article-viz:not([data-rendered])');
    if (!placeholders.length) return;

    const d3 = await import('d3');

    for (const el of Array.from(placeholders)) {
      el.setAttribute('data-rendered', 'true');
      el.style.position = 'relative';

      const vizType = el.getAttribute('data-viz-type');
      let config: any;
      try {
        config = JSON.parse(el.getAttribute('data-viz-config') ?? '{}');
      } catch {
        config = {};
      }

      try {
        switch (vizType) {
          case 'elo-trend': {
            const { renderEloTrend } = await import('../../visualizations/elo-trend/elo-trend.render');
            const teams: string[] = config.teams ?? ['BAL'];
            const season: number = config.season ?? new Date().getFullYear();
            const data = await this.mlbData.getEloHistory(teams, season);
            renderEloTrend(el, data, { teams, season, title: config.title }, d3);
            break;
          }
          case 'win-distribution': {
            const { renderWinDistribution } = await import('../../visualizations/win-distribution/win-dist.render');
            const teams: string[] = config.teams ?? ['BAL'];
            const { updated, projections } = await this.mlbData.getProjectionsWithMeta();
            renderWinDistribution(el, projections, { teams, title: config.title, compact: config.compact, prevMedian: config.prevMedian, updated }, d3);
            break;
          }
          case 'player-stats': {
            const { renderPlayerStats } = await import('../../visualizations/player-stats/player-stats.render');
            const playerId: string = config.playerId ?? 'hendegu01';
            const metrics: string[] = config.metrics ?? ['war'];
            const data = await this.mlbData.getPlayerCareerStats(playerId);
            renderPlayerStats(el, data, { playerId, metrics, title: config.title }, d3);
            break;
          }
          default:
            console.warn(`Unknown viz type: ${vizType}`);
        }
      } catch (err) {
        console.error(`Failed to render ${vizType}:`, err);
        el.innerHTML = '<p style="color:#999;text-align:center;padding:1rem;">Visualization unavailable.</p>';
      }
    }
  }
}
