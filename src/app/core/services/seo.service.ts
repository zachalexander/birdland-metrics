import { Injectable, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';
import { environment } from '../../../environments/environment';

export interface PageMeta {
  title: string;
  description: string;
  path: string;
  type?: string;
  image?: string;
  twitterCard?: string;
  article?: { publishedTime?: string; author?: string };
}

@Injectable({ providedIn: 'root' })
export class SeoService {
  private document = inject(DOCUMENT);
  private titleService = inject(Title);
  private meta = inject(Meta);

  private readonly defaultImage = environment.siteUrl + '/og-default.png';

  getSiteUrl(): string {
    return environment.siteUrl;
  }

  setPageMeta(page: PageMeta): void {
    const url = environment.siteUrl + page.path;
    const image = page.image ?? this.defaultImage;
    const twitterCard = page.twitterCard ?? 'summary_large_image';
    const ogType = page.type ?? 'website';

    this.titleService.setTitle(page.title);
    this.meta.updateTag({ name: 'description', content: page.description });
    this.meta.updateTag({ property: 'og:title', content: page.title });
    this.meta.updateTag({ property: 'og:description', content: page.description });
    this.meta.updateTag({ property: 'og:type', content: ogType });
    this.meta.updateTag({ property: 'og:url', content: url });
    this.meta.updateTag({ property: 'og:image', content: image });
    this.meta.updateTag({ property: 'og:site_name', content: 'Birdland Metrics' });
    this.meta.updateTag({ name: 'twitter:card', content: twitterCard });
    this.meta.updateTag({ name: 'twitter:site', content: '@birdlandmetrics' });
    this.meta.updateTag({ name: 'twitter:image', content: image });

    if (page.article) {
      if (page.article.publishedTime) {
        this.meta.updateTag({ property: 'article:published_time', content: page.article.publishedTime });
      }
      if (page.article.author) {
        this.meta.updateTag({ property: 'article:author', content: page.article.author });
      }
    }

    this.setCanonicalUrl(page.path);
  }

  setCanonicalUrl(path: string): void {
    const url = environment.siteUrl + path;
    let link: HTMLLinkElement | null = this.document.querySelector('link[rel="canonical"]');
    if (link) {
      link.setAttribute('href', url);
    } else {
      link = this.document.createElement('link');
      link.setAttribute('rel', 'canonical');
      link.setAttribute('href', url);
      this.document.head.appendChild(link);
    }
  }

  setJsonLd(...schemas: object[]): void {
    // Remove previously injected JSON-LD scripts
    const existing = this.document.querySelectorAll('script[data-seo]');
    existing.forEach(el => el.remove());

    for (const schema of schemas) {
      const script = this.document.createElement('script');
      script.setAttribute('type', 'application/ld+json');
      script.setAttribute('data-seo', '');
      script.textContent = JSON.stringify(schema);
      this.document.head.appendChild(script);
    }
  }

  getOrganizationSchema(): object {
    return {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: 'Birdland Metrics',
      url: environment.siteUrl,
      logo: environment.siteUrl + '/logo.png',
      description: 'Data-driven baseball analysis, visualizations, and insights.',
    };
  }

  getBreadcrumbSchema(items: { name: string; path: string }[]): object {
    return {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: items.map((item, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: item.name,
        item: environment.siteUrl + item.path,
      })),
    };
  }
}
