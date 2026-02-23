import { Component, inject, input, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AnalyticsService } from '../../../core/services/analytics.service';

type CtaState = 'idle' | 'loading' | 'success' | 'error';

@Component({
  selector: 'app-newsletter-cta',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './newsletter-cta.component.html',
  styleUrl: './newsletter-cta.component.css',
})
export class NewsletterCtaComponent {
  variant = input<'inline' | 'banner'>('inline');

  state = signal<CtaState>('idle');
  errorMessage = signal('');
  email = '';
  dismissed = signal(false);
  visible = signal(false);

  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private analytics = inject(AnalyticsService);

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      if (sessionStorage.getItem('newsletter-dismissed') === '1') {
        this.dismissed.set(true);
      }
      window.addEventListener('scroll', this.onScroll, { passive: true });
    }
  }

  private onScroll = () => {
    if (window.scrollY > 400) {
      this.visible.set(true);
      window.removeEventListener('scroll', this.onScroll);
    }
  };

  dismiss(): void {
    this.dismissed.set(true);
    if (isPlatformBrowser(this.platformId)) {
      sessionStorage.setItem('newsletter-dismissed', '1');
    }
  }

  submit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const emailValue = this.email.trim();
    if (!emailValue) return;

    this.state.set('loading');
    this.errorMessage.set('');

    this.http
      .post<{ success?: boolean; error?: string }>('/api/newsletter', { email: emailValue })
      .subscribe({
        next: () => {
          this.state.set('success');
          this.analytics.trackEvent('newsletter_signup', { variant: this.variant() });
        },
        error: (err) => {
          const message = err.error?.error || 'Subscription failed. Please try again later.';
          this.errorMessage.set(message);
          this.state.set('error');
        },
      });
  }
}
