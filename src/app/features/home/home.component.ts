import { Component, OnInit, signal, computed, inject, PLATFORM_ID, effect } from '@angular/core';
import { isPlatformBrowser, DecimalPipe } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { SeoService } from '../../core/services/seo.service';
import { BlogPost } from '../../shared/models/content.models';
import { PlayoffOdds, TeamProjection, RecentGame } from '../../shared/models/mlb.models';
import { RouterLink } from '@angular/router';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { RecentGamesComponent } from './components/recent-games/recent-games.component';
import { PlayoffRaceComponent } from '../../visualizations/playoff-race/playoff-race.component';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';


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

  oddsSeason = signal<number>(2026);
  showAllTeams = signal(false);
  animatedPct = signal(0);
  animatedWins = signal(0);

  private countUpEffect = effect(() => {
    const odds = this.oriolesOdds();
    if (!odds || !isPlatformBrowser(this.platformId)) return;
    const target = odds.playoff_pct;
    this.countUp(target, 1000, v => this.animatedPct.set(v));
  });

  private countUpWinsEffect = effect(() => {
    const wins = this.oriolesWins();
    if (!wins || !isPlatformBrowser(this.platformId)) return;
    this.countUp(wins, 1000, v => this.animatedWins.set(v));
  });

  private countUp(target: number, duration: number, setter: (v: number) => void): void {
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setter(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

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

  setOddsSeason(year: number): void {
    this.oddsSeason.set(year);
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
