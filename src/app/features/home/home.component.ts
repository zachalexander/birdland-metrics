import { Component, OnInit, signal, computed, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, DecimalPipe } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { SeoService } from '../../core/services/seo.service';
import { BlogPost } from '../../shared/models/content.models';
import { PlayoffOdds, TeamProjection, RecentGame, BenchmarkPlayer } from '../../shared/models/mlb.models';
import { RouterLink } from '@angular/router';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { RecentGamesComponent } from './components/recent-games/recent-games.component';
import { PlayoffRaceComponent } from '../../visualizations/playoff-race/playoff-race.component';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';
import { CoreBenchmarksComponent } from './components/core-benchmarks/core-benchmarks.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    DecimalPipe,
    RouterLink,
    ArticleCardComponent,
    RecentGamesComponent,
    PlayoffRaceComponent,
    NewsletterCtaComponent,
    CoreBenchmarksComponent,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit {
  articles = signal<BlogPost[]>([]);
  categories = signal<string[]>([]);
  loading = signal(true);

  oriolesOdds = signal<PlayoffOdds | null>(null);
  projections = signal<TeamProjection[]>([]);
  allOdds = signal<PlayoffOdds[]>([]);
  recentGames = signal<RecentGame[]>([]);
  gamesType = signal<'R' | 'S'>('R');
  benchmarkPlayers = signal<BenchmarkPlayer[]>([]);
  benchmarksUpdated = signal<string | null>(null);
  modelsUpdated = signal<string | null>(null);
  dashboardLoading = signal(true);

  viewing2025 = signal(false);
  oddsSeason = signal<number>(2026);
  showAllTeams = signal(false);

  /** 2025 final stats for each benchmark player, keyed by playerId → benchmarkKey → value */
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

  readonly stats2025 = HomeComponent.STATS_2025;

  oriolesWins = computed(() => {
    const bal = this.projections().find(p => p.team === 'BAL');
    return bal ? Math.round(bal.median_wins) : null;
  });

  featuredArticle = computed(() => {
    const arts = this.articles();
    return arts.find(a => a.featured) ?? arts[0] ?? null;
  });

  remainingArticles = computed(() => {
    const feat = this.featuredArticle();
    if (!feat) return this.articles();
    return this.articles().filter(a => a.slug !== feat.slug);
  });

  latestPreviewArticles = computed(() => this.remainingArticles().slice(0, 4));

  lastRunDate = computed(() => {
    const raw = this.modelsUpdated();
    if (!raw) return null;
    const d = new Date(raw + 'Z');
    const month = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'America/New_York' });
    const day = d.getDate();
    const year = d.getFullYear();
    const s = ['th', 'st', 'nd', 'rd'];
    const v = day % 100;
    const suffix = s[(v - 20) % 10] || s[v] || s[0];
    const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' });
    return `${month} ${day}${suffix}, ${year} \u00B7 ${time} ET`;
  });

  private platformId = inject(PLATFORM_ID);
  private seo = inject(SeoService);

  constructor(
    private contentful: ContentfulService,
    private mlbData: MlbDataService,
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    this.title.setTitle('Birdland Metrics — Baseball Analytics & Insights');
    this.meta.updateTag({ name: 'description', content: 'Data-driven baseball analysis, visualizations, and insights.' });
    this.meta.updateTag({ property: 'og:title', content: 'Birdland Metrics — Baseball Analytics & Insights' });
    this.meta.updateTag({ property: 'og:description', content: 'Data-driven baseball analysis, visualizations, and insights.' });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });
    this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + '/' });
    this.seo.setCanonicalUrl('/');
    this.seo.setJsonLd(this.seo.getOrganizationSchema());

    this.contentful.getCategories().then(cats => this.categories.set(cats));

    this.contentful
      .getArticles()
      .then((articles) => {
        this.articles.set(articles);
        this.loading.set(false);
      })
      .catch(() => this.loading.set(false));

    if (isPlatformBrowser(this.platformId)) {
      this.loadDashboard();
    } else {
      this.dashboardLoading.set(false);
    }
  }

  toggle2025(): void {
    this.viewing2025.set(!this.viewing2025());
  }

  setOddsSeason(year: number): void {
    this.oddsSeason.set(year);
  }

  private async loadDashboard(): Promise<void> {
    try {
      const [oddsResult, projections, gamesResult, benchmarksResult] = await Promise.all([
        this.mlbData.getPlayoffOdds().catch(() => ({ updated: '', odds: [] as PlayoffOdds[] })),
        this.mlbData.getProjections().catch(() => [] as TeamProjection[]),
        this.mlbData.getRecentGames().catch(() => ({ gameType: 'R' as const, games: [] as RecentGame[] })),
        this.mlbData.getCoreBenchmarks().catch(() => null),
      ]);

      this.allOdds.set(oddsResult.odds);
      this.oriolesOdds.set(oddsResult.odds.find(t => t.team === 'BAL') ?? null);
      if (oddsResult.updated) {
        this.modelsUpdated.set(oddsResult.updated);
      }
      this.projections.set(projections);
      this.recentGames.set(gamesResult.games.slice(0, 10));
      this.gamesType.set(gamesResult.gameType);
      if (benchmarksResult) {
        this.benchmarkPlayers.set(benchmarksResult.players);
        this.benchmarksUpdated.set(benchmarksResult.updated);
      }
    } catch (err) {
      console.error('Dashboard data load failed:', err);
    } finally {
      this.dashboardLoading.set(false);
    }
  }
}
