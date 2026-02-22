import { Component, inject, input, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../../../../environments/environment';

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
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  shareBluesky(): void {
    const text = `${this.title()} via @birdlandmetrics.com ${this.getUrl()}`;
    const url = `https://bsky.app/intent/compose?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  async nativeShare(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) return;
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
    navigator.clipboard.writeText(this.getUrl()).then(() => {
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    });
  }
}
