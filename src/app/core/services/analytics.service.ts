import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { environment } from '../../../environments/environment';

declare const gtag: (...args: any[]) => void;

const GA_ID = 'G-Q3B51YZBGE';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private router = inject(Router);
  private document = inject(DOCUMENT);
  private platformId = inject(PLATFORM_ID);

  init(): void {
    if (!environment.production || !isPlatformBrowser(this.platformId)) return;

    this.loadGtagScript();

    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => {
        gtag('event', 'page_view', { page_path: e.urlAfterRedirects });
      });
  }

  trackEvent(name: string, params?: Record<string, string | number>): void {
    if (!environment.production || !isPlatformBrowser(this.platformId)) return;
    gtag('event', name, params);
  }

  private loadGtagScript(): void {
    const w = this.document.defaultView as any;
    w.dataLayer = w.dataLayer || [];
    w.gtag = function () { w.dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA_ID, { send_page_view: false });

    const script = this.document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
    this.document.head.appendChild(script);
  }
}
