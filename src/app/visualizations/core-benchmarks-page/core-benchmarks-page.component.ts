import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { BenchmarkPlayer } from '../../shared/models/mlb.models';
import { CoreBenchmarksComponent } from '../core-benchmarks/core-benchmarks.component';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';

@Component({
  selector: 'app-core-benchmarks-page',
  standalone: true,
  imports: [CoreBenchmarksComponent, ShareButtonsComponent],
  templateUrl: './core-benchmarks-page.component.html',
  styleUrl: './core-benchmarks-page.component.css',
})
export class CoreBenchmarksPageComponent implements OnInit {
  benchmarkPlayers = signal<BenchmarkPlayer[]>([]);
  benchmarksUpdated = signal<string | null>(null);
  loading = signal(true);

  viewing2025 = signal(false);

  private static readonly STATS_2025: Record<string, Record<string, number | null>> = {
    // Gunnar Henderson: .274/.349/.438, 17 HR, 154 G
    '683002': { barrel_pct: 8.5, wrc_plus: 120, hr_pace: 17 },
    // Adley Rutschman: .220/.307/.366, 9 HR, 90 G
    '668939': { obp: 0.307, bb_pct: 11.0, wrc_plus: 91 },
    // Jordan Westburg: .265/.312/.457, 17 HR, 85 G
    '682614': { ops: 0.769, iso: 0.192, games_pace: 85 },
    // Colton Cowser: .196/.269/.385, 16 HR, 91 G
    '681297': { k_pct: 35.6, hard_pct: 39.2, wrc_plus: 83 },
    // Pete Alonso (NYM 2025): .240/.329/.467, 34 HR
    '624413': { hr_pace: 34, exit_velo: 93.5, slg: 0.467 },
    // Jackson Holliday: .242/.314/.375, 17 HR, 149 G
    '696137': { k_pct: 21.6, bb_pct: 8.6, avg: 0.242 },
    // Kyle Bradish: 2.53 ERA, 13.22 K/9, 32.0 IP
    '669062': { era: 2.53, k_per_9: 13.22, ip_pace: 32 },
    // Trevor Rogers: 1.81 ERA, 0.90 WHIP, 24.3 K%
    '669432': { era: 1.81, whip: 0.90, k_pct: 24.3 },
    // Shane Baz (TB 2025): 4.87 ERA, 4.37 FIP, 166.1 IP
    '669358': { era: 4.87, fip: 4.37, ip_pace: 166 },
    // Ryan Helsley (STL 2025): ~2.75 ERA, ~10.13 K/9, ~49 SV
    '664854': { era: 4.50, k_per_9: 10.13, sv_pace: 21 },
    // Team Bullpen
    'bullpen': { era: 4.87, k_per_9: 9.0, whip: 1.56 },
  };

  readonly stats2025 = CoreBenchmarksPageComponent.STATS_2025;

  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Core Player Benchmarks — Birdland Metrics',
      description: 'Track key statistical benchmarks for Orioles core players throughout the 2026 season.',
      path: '/visualizations/core-benchmarks',
    });
    this.seo.setJsonLd(this.seo.getOrganizationSchema());

    if (isPlatformBrowser(this.platformId)) {
      this.loadBenchmarks();
    } else {
      this.loading.set(false);
    }
  }

  toggle2025(): void {
    this.viewing2025.set(!this.viewing2025());
  }

  private async loadBenchmarks(): Promise<void> {
    try {
      const result = await this.mlbData.getCoreBenchmarks();
      if (result) {
        this.benchmarkPlayers.set(result.players);
        this.benchmarksUpdated.set(result.updated);
      }
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
    } finally {
      this.loading.set(false);
    }
  }
}
