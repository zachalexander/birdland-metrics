import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, DatePipe } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { SeoService } from '../../core/services/seo.service';
import { BlogPost } from '../../shared/models/content.models';
import { PlayoffOdds, TeamProjection, RecentGame } from '../../shared/models/mlb.models';
import { RouterLink } from '@angular/router';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { PlayoffOddsComponent } from './components/playoff-odds/playoff-odds.component';
import { StandingsTableComponent } from './components/standings-table/standings-table.component';
import { RecentGamesComponent } from './components/recent-games/recent-games.component';
import { WinDistributionComponent } from '../../visualizations/win-distribution/win-distribution.component';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    DatePipe,
    RouterLink,
    ArticleCardComponent,
    PlayoffOddsComponent,
    StandingsTableComponent,
    RecentGamesComponent,
    WinDistributionComponent,
    NewsletterCtaComponent,
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
  modelsUpdated = signal<string | null>(null);
  dashboardLoading = signal(true);

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

  private async loadDashboard(): Promise<void> {
    try {
      const [oddsResult, projections, gamesResult] = await Promise.all([
        this.mlbData.getPlayoffOdds().catch(() => ({ updated: '', odds: [] as PlayoffOdds[] })),
        this.mlbData.getProjections().catch(() => [] as TeamProjection[]),
        this.mlbData.getRecentGames().catch(() => ({ gameType: 'R' as const, games: [] as RecentGame[] })),
      ]);

      this.allOdds.set(oddsResult.odds);
      this.oriolesOdds.set(oddsResult.odds.find(t => t.team === 'BAL') ?? null);
      if (oddsResult.updated) {
        this.modelsUpdated.set(oddsResult.updated);
      }
      this.projections.set(projections);
      this.recentGames.set(gamesResult.games.slice(0, 10));
      this.gamesType.set(gamesResult.gameType);
    } catch (err) {
      console.error('Dashboard data load failed:', err);
    } finally {
      this.dashboardLoading.set(false);
    }
  }
}
