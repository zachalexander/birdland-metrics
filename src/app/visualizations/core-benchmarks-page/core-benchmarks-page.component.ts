import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { SeoService } from '../../core/services/seo.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { environment } from '../../../environments/environment';
import { BenchmarkPlayer } from '../../shared/models/mlb.models';
import { CoreBenchmarksComponent } from '../core-benchmarks/core-benchmarks.component';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';
import { playerBySlug } from '../core-benchmarks/player-slugs';

@Component({
  selector: 'app-core-benchmarks-page',
  standalone: true,
  imports: [CoreBenchmarksComponent, ShareButtonsComponent, RouterLink],
  templateUrl: './core-benchmarks-page.component.html',
  styleUrl: './core-benchmarks-page.component.css',
})
export class CoreBenchmarksPageComponent implements OnInit {
  benchmarkPlayers = signal<BenchmarkPlayer[]>([]);
  benchmarksUpdated = signal<string | null>(null);
  loading = signal(true);

  focusedPlayerId = signal<string | null>(null);
  focusedPlayerName = signal<string | null>(null);
  focusedPlayerSlug = signal<string | null>(null);
  focusedPlayerDescription = signal<string | null>(null);

  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);
  private mlbData = inject(MlbDataService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('playerSlug');

    if (slug) {
      const entry = playerBySlug(slug);
      if (!entry) {
        this.router.navigate(['/visualizations/core-benchmarks'], { replaceUrl: true });
        return;
      }
      this.focusedPlayerId.set(entry.id);
      this.focusedPlayerName.set(entry.name);
      this.focusedPlayerSlug.set(entry.slug);
      this.focusedPlayerDescription.set(entry.description);

      this.seo.setPageMeta({
        title: `${entry.name} — Core Benchmarks — Birdland Metrics`,
        description: `Track ${entry.name}'s key statistical benchmarks for the 2026 season.`,
        path: `/visualizations/core-benchmarks/${entry.slug}`,
        image: `${environment.s3.ogImages}/core-benchmarks-${entry.slug}.png`,
      });
    } else {
      this.seo.setPageMeta({
        title: 'Core Player Benchmarks — Birdland Metrics',
        description: 'Track key statistical benchmarks for Orioles core players throughout the 2026 season.',
        path: '/visualizations/core-benchmarks',
        image: `${environment.s3.ogImages}/core-benchmarks.png`,
      });
    }

    this.seo.setJsonLd(this.seo.getOrganizationSchema());

    if (isPlatformBrowser(this.platformId)) {
      this.loadBenchmarks();
    } else {
      this.loading.set(false);
    }
  }

  private async loadBenchmarks(): Promise<void> {
    try {
      const benchmarks = await this.mlbData.getCoreBenchmarks();

      if (benchmarks) {
        this.benchmarkPlayers.set(benchmarks.players);
        this.benchmarksUpdated.set(benchmarks.updated);
      }
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
    } finally {
      this.loading.set(false);
    }
  }
}
