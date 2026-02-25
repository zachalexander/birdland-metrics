import { Component, OnInit, signal, computed, inject, PLATFORM_ID, effect } from '@angular/core';
import { isPlatformBrowser, DecimalPipe } from '@angular/common';
import { ContentfulService } from '../../core/services/contentful.service';
import { MlbDataService } from '../../core/services/mlb-data.service';
import { SeoService } from '../../core/services/seo.service';
import { AnalyticsService } from '../../core/services/analytics.service';
import { BlogPost } from '../../shared/models/content.models';
import { PlayoffOdds, TeamProjection, RecentGame, PlayoffOddsHistoryPoint, TEAM_NAMES, AL_EAST } from '../../shared/models/mlb.models';
import { TEAM_COLORS } from '../../visualizations/viz-utils';
import { RouterLink } from '@angular/router';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { RecentGamesComponent } from './components/recent-games/recent-games.component';
import { PlayoffRaceComponent } from '../../visualizations/playoff-race/playoff-race.component';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';


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
    ShareButtonsComponent,
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
  animatedWins = signal(0);
  historicalOdds = signal<PlayoffOdds[]>([]);

  private seasonChangeEffect = effect(() => {
    const season = this.oddsSeason();
    if (season === 2026) {
      this.historicalOdds.set([]);
      return;
    }
    this.mlbData.getPlayoffOddsHistory(AL_EAST, season).then(data => {
      const endOfSeason: PlayoffOdds[] = [];
      for (const team of AL_EAST) {
        const pts = data[team];
        if (!pts?.length) continue;
        const last = pts[pts.length - 1];
        endOfSeason.push({
          team,
          playoff_pct: last.playoff_pct,
          division_pct: last.division_pct ?? 0,
          wildcard_pct: last.wildcard_pct ?? 0,
        });
      }
      this.historicalOdds.set(endOfSeason);
    }).catch(() => this.historicalOdds.set([]));
  });

  filledDots = computed(() => {
    const odds = this.oriolesOdds();
    return odds ? Math.round(odds.playoff_pct) : 0;
  });

  dots = computed(() => {
    const filled = this.filledDots();
    return Array.from({ length: 100 }, (_, i) => i < filled);
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

  // [wins, losses, playoff%, division%, wildcard%]
  private static readonly HISTORICAL_RESULTS: Record<number, Record<string, [number, number, number, number, number]>> = {
    2024: {
      NYY: [94, 68, 100, 100, 0],
      BAL: [91, 71, 100, 0, 100],
      BOS: [81, 81, 0, 0, 0],
      TB:  [80, 82, 0, 0, 0],
      TOR: [74, 88, 0, 0, 0],
    },
    2025: {
      TOR: [94, 68, 100, 100, 0],
      NYY: [94, 68, 100, 0, 100],
      BOS: [89, 73, 100, 0, 100],
      TB:  [77, 85, 0, 0, 0],
      BAL: [75, 87, 0, 0, 0],
    },
  };

  sortedOdds = computed(() => {
    const season = this.oddsSeason();
    const historical = HomeComponent.HISTORICAL_RESULTS[season];
    if (historical) {
      return AL_EAST
        .filter(t => historical[t])
        .map(t => {
          const [w, l, pp, dp, wc] = historical[t];
          return {
            team: t, name: TEAM_NAMES[t] ?? t, color: TEAM_COLORS[t] ?? '#6b7280',
            playoff_pct: pp, division_pct: dp, wildcard_pct: wc, wins: w, losses: l,
          };
        })
        .sort((a, b) => (b.wins ?? 0) - (a.wins ?? 0) || b.division_pct - a.division_pct);
    }
    const odds = this.allOdds();
    const projs = this.projections();
    const projMap = new Map(projs.map(p => [p.team, p]));
    return odds
      .filter(o => AL_EAST.includes(o.team))
      .map(o => ({
        team: o.team, name: TEAM_NAMES[o.team] ?? o.team, color: TEAM_COLORS[o.team] ?? '#6b7280',
        playoff_pct: o.playoff_pct, division_pct: o.division_pct, wildcard_pct: o.wildcard_pct,
        wins: projMap.has(o.team) ? Math.round(projMap.get(o.team)!.median_wins) : null,
        losses: projMap.has(o.team) ? 162 - Math.round(projMap.get(o.team)!.median_wins) : null,
      }))
      .sort((a, b) => (b.wins ?? 0) - (a.wins ?? 0) || b.playoff_pct - a.playoff_pct);
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
  private analytics = inject(AnalyticsService);

  constructor(
    private contentful: ContentfulService,
    private mlbData: MlbDataService,
  ) {}

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Birdland Metrics — Baseball Analytics & Insights',
      description: 'Data-driven baseball analysis, visualizations, and insights.',
      path: '/',
    });
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
    }
  }

  setOddsSeason(year: number): void {
    this.oddsSeason.set(year);
    this.analytics.trackEvent('viz_interaction', { viz: 'playoff_race', action: 'season_change', value: String(year) });
  }

  setShowAllTeams(showAll: boolean): void {
    this.showAllTeams.set(showAll);
    this.analytics.trackEvent('viz_interaction', { viz: 'playoff_race', action: 'team_scope', value: showAll ? 'al_east' : 'orioles' });
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
