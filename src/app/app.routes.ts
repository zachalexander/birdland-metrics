import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'articles',
    loadComponent: () =>
      import('./features/article-list/article-list.component').then(
        (m) => m.ArticleListComponent,
      ),
  },
  {
    path: 'articles/:slug',
    loadComponent: () =>
      import('./features/article-detail/article-detail.component').then(
        (m) => m.ArticleDetailComponent,
      ),
  },
  {
    path: 'category/:category',
    loadComponent: () =>
      import('./features/article-list/article-list.component').then(
        (m) => m.ArticleListComponent,
      ),
  },
  {
    path: 'visualizations/spray-chart',
    loadComponent: () =>
      import('./visualizations/spray-chart/spray-chart.component').then(
        (m) => m.SprayChartComponent,
      ),
  },
  {
    path: 'visualizations/elo-trends',
    loadComponent: () =>
      import('./visualizations/elo-trend/elo-trend.component').then(
        (m) => m.EloTrendComponent,
      ),
  },
  {
    path: 'visualizations/playoff-race',
    loadComponent: () =>
      import('./visualizations/playoff-race/playoff-race.component').then(
        (m) => m.PlayoffRaceComponent,
      ),
  },
  {
    path: 'visualizations/win-distribution',
    loadComponent: () =>
      import('./visualizations/win-distribution/win-distribution.component').then(
        (m) => m.WinDistributionComponent,
      ),
  },
  {
    path: 'visualizations/player-stats',
    loadComponent: () =>
      import('./visualizations/player-stats/player-stats.component').then(
        (m) => m.PlayerStatsComponent,
      ),
  },
  {
    path: 'visualizations/stat-card',
    loadComponent: () =>
      import('./visualizations/stat-card/stat-card.component').then(
        (m) => m.StatCardComponent,
      ),
  },
  {
    path: 'visualizations/core-benchmarks',
    loadComponent: () =>
      import('./visualizations/core-benchmarks-page/core-benchmarks-page.component').then(
        (m) => m.CoreBenchmarksPageComponent,
      ),
  },
  {
    path: 'visualizations/core-benchmarks/:playerSlug',
    loadComponent: () =>
      import('./visualizations/core-benchmarks-page/core-benchmarks-page.component').then(
        (m) => m.CoreBenchmarksPageComponent,
      ),
  },
  {
    path: 'contact',
    loadComponent: () =>
      import('./features/contact/contact.component').then(
        (m) => m.ContactComponent,
      ),
  },
  {
    path: 'disclaimer',
    loadComponent: () =>
      import('./features/disclaimer/disclaimer.component').then(
        (m) => m.DisclaimerComponent,
      ),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
