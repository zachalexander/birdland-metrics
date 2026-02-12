import { Injectable, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class SeoService {
  private document = inject(DOCUMENT);

  getSiteUrl(): string {
    return environment.siteUrl;
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
