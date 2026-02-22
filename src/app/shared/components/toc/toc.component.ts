import { Component, input, signal, inject, PLATFORM_ID, OnInit, OnDestroy } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export interface TocHeading {
  id: string;
  text: string;
  level: number;
}

@Component({
  selector: 'app-toc',
  standalone: true,
  templateUrl: './toc.component.html',
  styleUrl: './toc.component.css',
})
export class TocComponent implements OnInit, OnDestroy {
  headings = input.required<TocHeading[]>();
  activeId = signal('');

  private platformId = inject(PLATFORM_ID);
  private observer?: IntersectionObserver;

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    // Use a small delay to let the DOM settle after innerHTML rendering
    setTimeout(() => this.observeHeadings(), 100);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  private observeHeadings(): void {
    const ids = this.headings().map(h => h.id);
    const elements = ids
      .map(id => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    if (!elements.length) return;

    this.observer = new IntersectionObserver(
      entries => {
        // Find the first visible heading (closest to top)
        for (const entry of entries) {
          if (entry.isIntersecting) {
            this.activeId.set(entry.target.id);
            return;
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0 },
    );

    for (const el of elements) {
      this.observer.observe(el);
    }
  }

  scrollTo(id: string): void {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
