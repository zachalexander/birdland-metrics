import { Component, OnInit, signal, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { BlogPost } from '../../shared/models/content.models';
import { PlayoffOdds, TeamProjection, RecentGame } from '../../shared/models/mlb.models';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { PlayoffOddsComponent } from './components/playoff-odds/playoff-odds.component';
import { StandingsTableComponent } from './components/standings-table/standings-table.component';
import { RecentGamesComponent } from './components/recent-games/recent-games.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    ArticleCardComponent,
    PlayoffOddsComponent,
    StandingsTableComponent,
    RecentGamesComponent,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit {
  articles = signal<BlogPost[]>([]);
  loading = signal(true);

  oriolesOdds = signal<PlayoffOdds | null>(null);
  projections = signal<TeamProjection[]>([]);
  allOdds = signal<PlayoffOdds[]>([]);
  recentGames = signal<RecentGame[]>([]);
  dashboardLoading = signal(true);

  private platformId = inject(PLATFORM_ID);

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
      const [odds, projections, games] = await Promise.all([
        this.mlbData.getPlayoffOdds().catch(() => [] as PlayoffOdds[]),
        this.mlbData.getProjections().catch(() => [] as TeamProjection[]),
        this.mlbData.getRecentGames().catch(() => [] as RecentGame[]),
      ]);

      this.allOdds.set(odds);
      this.oriolesOdds.set(odds.find(t => t.team === 'BAL') ?? null);
      this.projections.set(projections);
      this.recentGames.set(games);
    } catch (err) {
      console.error('Dashboard data load failed:', err);
    } finally {
      this.dashboardLoading.set(false);
    }
  }
}
