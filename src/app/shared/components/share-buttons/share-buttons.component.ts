import { Component, inject, input, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../../../../environments/environment';
import { AnalyticsService } from '../../../core/services/analytics.service';

@Component({
  selector: 'app-share-buttons',
  standalone: true,
  templateUrl: './share-buttons.component.html',
  styleUrl: './share-buttons.component.css',
})
export class ShareButtonsComponent {
  title = input.required<string>();
  path = input.required<string>();

  copied = signal(false);
  canNativeShare = signal(false);

  private platformId = inject(PLATFORM_ID);
  private analytics = inject(AnalyticsService);

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.canNativeShare.set(!!navigator.share);
    }
  }

  private getUrl(): string {
    return environment.siteUrl + this.path();
  }

  shareTwitter(): void {
    const text = `${this.title()} via @birdlandmetrics`;
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(this.getUrl())}&text=${encodeURIComponent(text)}`;
    this.analytics.trackEvent('share', { method: 'twitter', content_id: this.path() });
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  shareBluesky(): void {
    const text = `${this.title()} via @birdlandmetrics.com ${this.getUrl()}`;
    const url = `https://bsky.app/intent/compose?text=${encodeURIComponent(text)}`;
    this.analytics.trackEvent('share', { method: 'bluesky', content_id: this.path() });
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  async nativeShare(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) return;
    this.analytics.trackEvent('share', { method: 'native', content_id: this.path() });
    try {
      await navigator.share({
        title: this.title(),
        url: this.getUrl(),
      });
    } catch {
      // User cancelled or share failed — no action needed
    }
  }

  copyLink(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.analytics.trackEvent('share', { method: 'copy_link', content_id: this.path() });
    navigator.clipboard.writeText(this.getUrl()).then(() => {
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    });
  }
}
