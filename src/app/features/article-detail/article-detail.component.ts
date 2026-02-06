import { Component, OnInit, signal, inject } from '@angular/core';
import { DatePipe, DOCUMENT } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Meta, Title } from '@angular/platform-browser';
import { documentToHtmlString } from '@contentful/rich-text-html-renderer';
import { ContentfulService } from '../../core/services/contentful.service';
import { BlogPost } from '../../shared/models/content.models';

@Component({
  selector: 'app-article-detail',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './article-detail.component.html',
  styleUrl: './article-detail.component.css',
})
export class ArticleDetailComponent implements OnInit {
  article = signal<BlogPost | null>(null);
  bodyHtml = signal('');
  loading = signal(true);
  notFound = signal(false);

  private document = inject(DOCUMENT);

  constructor(
    private route: ActivatedRoute,
    private contentful: ContentfulService,
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) {
      this.notFound.set(true);
      this.loading.set(false);
      return;
    }

    this.contentful
      .getArticleBySlug(slug)
      .then((article) => {
        if (!article) {
          this.notFound.set(true);
          this.loading.set(false);
          return;
        }

        this.article.set(article);
        this.bodyHtml.set(documentToHtmlString(article.content));
        this.loading.set(false);
        this.setMeta(article);
        this.addJsonLd(article);
      })
      .catch(() => {
        this.loading.set(false);
        this.notFound.set(true);
      });
  }

  private setMeta(article: BlogPost): void {
    this.title.setTitle(`${article.title} — Birdland Metrics`);
    this.meta.updateTag({ name: 'description', content: article.excerpt });
    this.meta.updateTag({ property: 'og:title', content: article.title });
    this.meta.updateTag({ property: 'og:description', content: article.excerpt });
    this.meta.updateTag({ property: 'og:type', content: 'article' });
    this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });
    if (article.coverImage) {
      this.meta.updateTag({ property: 'og:image', content: article.coverImage.url });
      this.meta.updateTag({ name: 'twitter:image', content: article.coverImage.url });
    }
  }

  private addJsonLd(article: BlogPost): void {
    const jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'BlogPosting',
      headline: article.title,
      description: article.excerpt,
      datePublished: article.publishedAt,
      ...(article.coverImage && { image: article.coverImage.url }),
    };

    const script = this.document.createElement('script');
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify(jsonLd);
    this.document.head.appendChild(script);
  }
}
