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
    path: 'visualizations/win-distribution',
    loadComponent: () =>
      import('./visualizations/win-distribution/win-distribution.component').then(
        (m) => m.WinDistributionComponent,
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
