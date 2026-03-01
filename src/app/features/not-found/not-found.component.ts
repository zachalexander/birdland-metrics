import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Meta } from '@angular/platform-browser';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="not-found">
      <h1>404</h1>
      <p>The page you're looking for doesn't exist.</p>
      <a routerLink="/" class="home-link">Back to Home</a>
    </div>
  `,
  styles: [`
    .not-found {
      text-align: center;
      padding: var(--space-3xl) var(--space-lg);
      min-height: 50vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    h1 {
      font-size: 4rem;
      font-weight: 800;
      color: var(--color-text);
      margin-bottom: var(--space-sm);
    }
    p {
      font-size: var(--text-lg);
      color: var(--color-text-secondary);
      margin-bottom: var(--space-xl);
    }
    .home-link {
      font-weight: 600;
      color: var(--color-accent);
      text-decoration: none;
    }
    .home-link:hover {
      text-decoration: underline;
    }
  `],
})
export class NotFoundComponent implements OnInit {
  private seo = inject(SeoService);
  private meta = inject(Meta);

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Page Not Found — Birdland Metrics',
      description: 'The page you are looking for does not exist.',
      path: '/404',
    });
    this.meta.updateTag({ name: 'prerender-status-code', content: '404' });
  }
}
