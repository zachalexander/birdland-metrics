import {
  Component,
  AfterViewInit,
  Input,
  ElementRef,
  viewChild,
  PLATFORM_ID,
  inject,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { PlayoffRaceConfig, renderPlayoffRace } from './playoff-race.render';
import { AL_EAST } from '../../shared/models/mlb.models';

@Component({
  selector: 'app-playoff-race',
  standalone: true,
  templateUrl: './playoff-race.component.html',
  styleUrl: './playoff-race.component.css',
})
export class PlayoffRaceComponent implements AfterViewInit {
  @Input() config?: PlayoffRaceConfig;

  chartContainer = viewChild<ElementRef>('chartContainer');
  private platformId = inject(PLATFORM_ID);
  private mlbData = inject(MlbDataService);
  isBrowser = false;
  loading = true;
  error = '';

  private get resolvedConfig(): PlayoffRaceConfig {
    return this.config ?? { teams: AL_EAST };
  }

  constructor() {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }

  async ngAfterViewInit(): Promise<void> {
    if (!this.isBrowser) return;

    const cfg = this.resolvedConfig;

    try {
      const [d3, data] = await Promise.all([
        import('d3'),
        this.mlbData.getPlayoffOddsHistory(cfg.teams),
      ]);

      this.loading = false;
      const container = this.chartContainer()?.nativeElement;
      if (!container) return;

      renderPlayoffRace(container, data, cfg, d3);
    } catch {
      this.loading = false;
      this.error = 'Unable to load playoff odds data. The season may not have started yet.';
    }
  }
}
