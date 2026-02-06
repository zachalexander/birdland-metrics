import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/home/home.component').then((m) => m.HomeComponent),
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
    path: '**',
    redirectTo: '',
  },
];
