import { Component, inject, OnInit, OnDestroy, PLATFORM_ID, HostBinding, ChangeDetectorRef } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router, NavigationEnd, RouterLink } from '@angular/router';
import { filter } from 'rxjs/operators';
import { Subscription } from 'rxjs';
import { ThemeToggleComponent } from '../theme-toggle/theme-toggle.component';
import { SearchOverlayComponent } from '../search-overlay/search-overlay.component';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, ThemeToggleComponent, SearchOverlayComponent],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css',
})
export class HeaderComponent implements OnInit, OnDestroy {
  private router = inject(Router);
  private platformId = inject(PLATFORM_ID);
  private cdr = inject(ChangeDetectorRef);
  private routeSub?: Subscription;
  private scrollHandler?: () => void;

  searchExpanded = false;

  private isHome = false;
  private scrolled = false;

  @HostBinding('class.header-dark')
  get headerDark(): boolean {
    return this.isHome && !this.scrolled;
  }

  ngOnInit(): void {
    this.isHome = this.router.url === '/' || this.router.url === '';
    this.routeSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => {
        this.isHome = e.urlAfterRedirects === '/' || e.urlAfterRedirects === '';
      });

    if (isPlatformBrowser(this.platformId)) {
      this.scrollHandler = () => {
        const wasScrolled = this.scrolled;
        this.scrolled = window.scrollY > 10;
        if (wasScrolled !== this.scrolled) {
          this.cdr.markForCheck();
        }
      };
      window.addEventListener('scroll', this.scrollHandler, { passive: true });
      this.scrollHandler();
    }
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
    if (this.scrollHandler && isPlatformBrowser(this.platformId)) {
      window.removeEventListener('scroll', this.scrollHandler);
    }
  }
}
