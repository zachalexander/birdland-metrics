import { Component, OnInit, signal, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { SeoService } from '../../core/services/seo.service';
import { BlogPost } from '../../shared/models/content.models';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';

@Component({
  selector: 'app-article-list',
  standalone: true,
  imports: [ArticleCardComponent, RouterLink],
  templateUrl: './article-list.component.html',
  styleUrl: './article-list.component.css',
})
export class ArticleListComponent implements OnInit {
  articles = signal<BlogPost[]>([]);
  category = signal('');
  loading = signal(true);

  private seo = inject(SeoService);

  constructor(
    private route: ActivatedRoute,
    private contentful: ContentfulService,
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    const cat = this.route.snapshot.paramMap.get('category') ?? '';
    this.category.set(cat);

    const displayName = cat ? cat.charAt(0).toUpperCase() + cat.slice(1) : 'All Articles';
    const pageTitle = cat ? `${displayName} — Birdland Metrics` : 'Articles — Birdland Metrics';
    const pagePath = cat ? '/category/' + cat : '/articles';

    this.title.setTitle(pageTitle);
    this.meta.updateTag({ name: 'description', content: cat ? `Articles about ${displayName} on Birdland Metrics.` : 'All articles on Birdland Metrics.' });
    this.meta.updateTag({ property: 'og:title', content: pageTitle });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + pagePath });
    this.seo.setCanonicalUrl(pagePath);
    this.seo.setJsonLd(
      this.seo.getBreadcrumbSchema([
        { name: 'Home', path: '/' },
        { name: displayName, path: pagePath },
      ]),
      this.seo.getOrganizationSchema(),
    );

    const fetch = cat
      ? this.contentful.getArticlesByCategory(cat)
      : this.contentful.getArticles(100);

    fetch
      .then((articles) => {
        this.articles.set(articles);
        this.loading.set(false);
      })
      .catch(() => this.loading.set(false));
  }
}
