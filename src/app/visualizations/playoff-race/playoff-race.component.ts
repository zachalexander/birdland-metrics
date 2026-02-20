import {
  Component,
  AfterViewInit,
  Input,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { PlayoffRaceConfig, renderPlayoffRace } from './playoff-race.render';
import { AL_EAST, TeamProjection, PlayoffOdds } from '../../shared/models/mlb.models';

@Component({
  selector: 'app-playoff-race',
  standalone: true,
  templateUrl: './playoff-race.component.html',
  styleUrl: './playoff-race.component.css',
})
export class PlayoffRaceComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  @Input() config?: PlayoffRaceConfig;
  @Input() season?: number;
  @Input() projections?: TeamProjection[];
  @Input() odds?: PlayoffOdds[];
  @Input() showAllTeams = false;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';
  private initialized = false;
  private lastData: Record<string, import('../../shared/models/mlb.models').PlayoffOddsHistoryPoint[]> | null = null;
  private lastD3: typeof import('d3') | null = null;
  private themeHandler?: () => void;

  private get resolvedConfig(): PlayoffRaceConfig {
    return this.config ?? { teams: AL_EAST };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  ngOnInit(): void {
    if (this.isBrowser) {
      this.themeHandler = () => this.rerender();
      window.addEventListener('theme-changed', this.themeHandler);
    }
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;
    this.initialized = true;
    await this.loadAndRender();
  }

  async ngOnChanges(changes: SimpleChanges): Promise<void> {
    if (!this.initialized) return;
    if (changes['season']) {
      await this.loadAndRender();
    } else if (changes['projections'] || changes['odds'] || changes['showAllTeams']) {
      await this.rerender();
    }
  }

  private async loadAndRender(): Promise<void> {
    this.loading = true;
    this.error = '';

    const cfg = this.resolvedConfig;

    try {
      const [d3, data] = await Promise.all([
        import('d3'),
        this.mlbData.getPlayoffOddsHistory(cfg.teams, this.season),
      ]);

      this.loading = false;
      this.lastData = data;
      this.lastD3 = d3;
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      // Clear previous chart
      container.innerHTML = '';

      const isHistorical = this.season != null && this.season !== 2026;
      renderPlayoffRace(container, data, cfg, d3, isHistorical ? undefined : this.projections, isHistorical ? undefined : this.odds, this.showAllTeams);
    } catch {
      this.loading = false;
      this.error = 'Unable to load playoff odds data. The season may not have started yet.';
    }
  }

  ngOnDestroy(): void {
    if (this.themeHandler && this.isBrowser) {
      window.removeEventListener('theme-changed', this.themeHandler);
    }
  }

  private async rerender(): Promise<void> {
    if (!this.lastData || !this.lastD3) return;
    const container = this.chartContainer()?.nativeElement;
    if (!container) return;
    container.innerHTML = '';
    const isHistorical = this.season != null && this.season !== 2026;
    renderPlayoffRace(container, this.lastData, this.resolvedConfig, this.lastD3, isHistorical ? undefined : this.projections, isHistorical ? undefined : this.odds, this.showAllTeams);
  }
}
