import { Component, OnInit, signal, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, Meta, SafeHtml, Title } from '@angular/platform-browser';
import { documentToHtmlString } from '@contentful/rich-text-html-renderer';
import { BLOCKS, INLINES } from '@contentful/rich-text-types';
import { ContentfulService } from '../../core/services/contentful.service';
import { SeoService } from '../../core/services/seo.service';
import { BlogPost } from '../../shared/models/content.models';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';
import { VizHostDirective } from '../../shared/directives/viz-host.directive';
import { NewsletterCtaComponent } from '../../shared/components/newsletter-cta/newsletter-cta.component';
import { ShareButtonsComponent } from '../../shared/components/share-buttons/share-buttons.component';
import { AuthorCardComponent } from '../../shared/components/author-card/author-card.component';

@Component({
  selector: 'app-article-detail',
  standalone: true,
  imports: [DatePipe, RouterLink, ArticleCardComponent, VizHostDirective, NewsletterCtaComponent, ShareButtonsComponent, AuthorCardComponent],
  templateUrl: './article-detail.component.html',
  styleUrl: './article-detail.component.css',
})
export class ArticleDetailComponent implements OnInit {
  article = signal<BlogPost | null>(null);
  bodyHtml = signal<SafeHtml>('');
  loading = signal(true);
  notFound = signal(false);
  relatedArticles = signal<BlogPost[]>([]);

  private seo = inject(SeoService);
  private sanitizer = inject(DomSanitizer);

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
        const renderVizEntry = (node: any): string => {
          const entry = node.data?.target;
          if (!entry?.sys?.contentType?.sys?.id) return '';
          if (entry.sys.contentType.sys.id === 'visualization') {
            const vizType = entry.fields?.vizType ?? '';
            const config = entry.fields?.config ?? {};
            const safeConfig = JSON.stringify(config).replace(/'/g, '&#39;');
            return `<div class="article-viz" data-viz-type="${vizType}" data-viz-config='${safeConfig}'></div>`;
          }
          return '';
        };
        const rawHtml = documentToHtmlString(article.content, {
          renderNode: {
            [BLOCKS.EMBEDDED_ENTRY]: renderVizEntry,
            [INLINES.EMBEDDED_ENTRY]: renderVizEntry,
          },
        });
        this.bodyHtml.set(this.sanitizer.bypassSecurityTrustHtml(rawHtml));
        this.loading.set(false);
        this.setMeta(article);
        this.addJsonLd(article);

        if (article.tags.length) {
          this.contentful.getRelatedArticles(article.slug, article.tags).then((related) => {
            this.relatedArticles.set(related);
          });
        }
      })
      .catch(() => {
        this.loading.set(false);
        this.notFound.set(true);
      });
  }

  private setMeta(article: BlogPost): void {
    const articleUrl = this.seo.getSiteUrl() + '/articles/' + article.slug;
    this.title.setTitle(`${article.title} — Birdland Metrics`);
    this.meta.updateTag({ name: 'description', content: article.excerpt });
    this.meta.updateTag({ property: 'og:title', content: article.title });
    this.meta.updateTag({ property: 'og:description', content: article.excerpt });
    this.meta.updateTag({ property: 'og:type', content: 'article' });
    this.meta.updateTag({ property: 'og:url', content: articleUrl });
    this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });
    this.meta.updateTag({ name: 'twitter:site', content: '@birdlandmetrics' });
    if (article.coverImage) {
      this.meta.updateTag({ property: 'og:image', content: article.coverImage.url });
      this.meta.updateTag({ name: 'twitter:image', content: article.coverImage.url });
    }
    this.seo.setCanonicalUrl('/articles/' + article.slug);
  }

  private addJsonLd(article: BlogPost): void {
    const siteUrl = this.seo.getSiteUrl();

    const blogPosting: Record<string, unknown> = {
      '@context': 'https://schema.org',
      '@type': 'BlogPosting',
      headline: article.title,
      description: article.excerpt,
      datePublished: article.publishedAt,
      url: siteUrl + '/articles/' + article.slug,
      ...(article.coverImage && { image: article.coverImage.url }),
      ...(article.author && {
        author: {
          '@type': 'Person',
          name: article.author.name,
        },
      }),
      publisher: {
        '@type': 'Organization',
        name: 'Birdland Metrics',
        logo: { '@type': 'ImageObject', url: siteUrl + '/logo.png' },
      },
    };

    const breadcrumbItems: { name: string; path: string }[] = [
      { name: 'Home', path: '/' },
    ];
    if (article.tags.length) {
      breadcrumbItems.push({ name: article.tags[0], path: '/category/' + article.tags[0] });
    }
    breadcrumbItems.push({ name: article.title, path: '/articles/' + article.slug });

    this.seo.setJsonLd(
      blogPosting,
      this.seo.getBreadcrumbSchema(breadcrumbItems),
      this.seo.getOrganizationSchema(),
    );
  }
}
