import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'bm-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private platformId = inject(PLATFORM_ID);

  theme = signal<ResolvedTheme>('light');

  constructor() {
    if (!isPlatformBrowser(this.platformId)) return;

    const stored = localStorage.getItem(STORAGE_KEY) as ResolvedTheme | null;
    if (stored === 'light' || stored === 'dark') {
      this.theme.set(stored);
    } else {
      // Use OS preference as initial default
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.theme.set(prefersDark ? 'dark' : 'light');
    }

    this.applyTheme();
  }

  toggle(): void {
    this.theme.set(this.theme() === 'light' ? 'dark' : 'light');

    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem(STORAGE_KEY, this.theme());
    }

    this.applyTheme();
  }

  private applyTheme(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const resolved = this.theme();
    document.documentElement.setAttribute('data-theme', resolved);

    // Dispatch custom event so D3 visualizations can re-render
    window.dispatchEvent(new CustomEvent('theme-changed', { detail: resolved }));
  }
}
