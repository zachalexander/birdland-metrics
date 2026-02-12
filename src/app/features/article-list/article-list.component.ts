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

    const displayName = cat.charAt(0).toUpperCase() + cat.slice(1);
    this.title.setTitle(`${displayName} — Birdland Metrics`);
    this.meta.updateTag({ name: 'description', content: `Articles about ${displayName} on Birdland Metrics.` });
    this.meta.updateTag({ property: 'og:title', content: `${displayName} — Birdland Metrics` });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this.meta.updateTag({ property: 'og:url', content: this.seo.getSiteUrl() + '/category/' + cat });
    this.seo.setCanonicalUrl('/category/' + cat);
    this.seo.setJsonLd(
      this.seo.getBreadcrumbSchema([
        { name: 'Home', path: '/' },
        { name: displayName, path: '/category/' + cat },
      ]),
      this.seo.getOrganizationSchema(),
    );

    this.contentful
      .getArticlesByCategory(cat)
      .then((articles) => {
        this.articles.set(articles);
        this.loading.set(false);
      })
      .catch(() => this.loading.set(false));
  }
}
