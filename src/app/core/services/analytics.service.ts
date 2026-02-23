import { Injectable, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

declare const gtag: (...args: any[]) => void;

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private router = inject(Router);
  private document = inject(DOCUMENT);

  init(): void {
    if (!this.document.defaultView) return; // skip on server

    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => {
        gtag('event', 'page_view', { page_path: e.urlAfterRedirects });
      });
  }
}
