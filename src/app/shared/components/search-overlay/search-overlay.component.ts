import {
  Component,
  OnInit,
  OnDestroy,
  Output,
  EventEmitter,
  ElementRef,
  viewChild,
  inject,
  PLATFORM_ID,
  ChangeDetectorRef,
  NgZone,
  HostListener,
} from '@angular/core';
import { isPlatformBrowser, DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { ContentfulService } from '../../../core/services/contentful.service';
import { BlogPost } from '../../models/content.models';

@Component({
  selector: 'app-search-overlay',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './search-overlay.component.html',
  styleUrl: './search-overlay.component.css',
})
export class SearchOverlayComponent implements OnInit, OnDestroy {
  searchInput = viewChild<ElementRef<HTMLInputElement>>('searchInput');

  private platformId = inject(PLATFORM_ID);
  private contentful = inject(ContentfulService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);
  private elRef = inject(ElementRef);

  @Output() expandedChange = new EventEmitter<boolean>();
  expanded = false;
  query = '';
  results: BlogPost[] = [];
  loading = false;
  searched = false;

  private allArticles: BlogPost[] = [];
  private allLoaded = false;
  private prefetchPromise: Promise<void> | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private keyHandler?: (e: KeyboardEvent) => void;

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.keyHandler = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && this.expanded) {
          this.collapse();
        }
      };
      document.addEventListener('keydown', this.keyHandler);
    }
  }

  ngOnDestroy(): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    if (this.keyHandler && isPlatformBrowser(this.platformId)) {
      document.removeEventListener('keydown', this.keyHandler);
    }
  }

  expand(): void {
    if (this.expanded) return;
    this.expanded = true;
    this.expandedChange.emit(true);
    this.prefetchArticles();
    setTimeout(() => this.searchInput()?.nativeElement.focus(), 30);
  }

  collapse(): void {
    this.expanded = false;
    this.expandedChange.emit(false);
    this.query = '';
    this.results = [];
    this.searched = false;
    this.loading = false;
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.expanded && !this.elRef.nativeElement.contains(event.target)) {
      this.collapse();
    }
  }

  onInput(event: Event): void {
    this.query = (event.target as HTMLInputElement).value;
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    const q = this.query;
    if (!q.trim()) {
      this.results = [];
      this.searched = false;
      this.loading = false;
      return;
    }
    this.loading = true;
    this.searched = true;
    this.debounceTimer = setTimeout(() => this.doSearch(q), 300);
  }

  selectResult(post: BlogPost): void {
    this.collapse();
    this.router.navigate(['/articles', post.slug]);
  }

  private async doSearch(q: string): Promise<void> {
    try {
      if (this.prefetchPromise) {
        await this.prefetchPromise;
      }
      const local = this.filterLocal(q);
      let results: BlogPost[];
      if (local.length > 0) {
        results = local;
      } else {
        results = await this.contentful.searchArticles(q);
      }
      if (this.query === q) {
        this.zone.run(() => {
          this.results = results;
          this.loading = false;
          this.cdr.markForCheck();
        });
      }
    } catch {
      if (this.query === q) {
        this.zone.run(() => {
          this.results = [];
          this.loading = false;
          this.cdr.markForCheck();
        });
      }
    }
  }

  private prefetchArticles(): void {
    if (this.allLoaded || this.prefetchPromise) return;
    this.prefetchPromise = this.contentful.getArticles(100)
      .then(articles => {
        this.allArticles = articles;
        this.allLoaded = true;
      })
      .catch(() => {});
  }

  private filterLocal(q: string): BlogPost[] {
    if (!this.allArticles.length) return [];
    const lower = q.toLowerCase();
    return this.allArticles.filter(a =>
      a.title.toLowerCase().includes(lower) ||
      a.excerpt.toLowerCase().includes(lower) ||
      a.tags.some(t => t.toLowerCase().includes(lower))
    );
  }
}
