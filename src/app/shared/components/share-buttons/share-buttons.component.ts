import { Component, inject, input, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-share-buttons',
  standalone: true,
  templateUrl: './share-buttons.component.html',
  styleUrl: './share-buttons.component.css',
})
export class ShareButtonsComponent {
  title = input.required<string>();
  slug = input.required<string>();

  copied = signal(false);

  private platformId = inject(PLATFORM_ID);

  private getUrl(): string {
    return `https://birdlandmetrics.com/articles/${this.slug()}`;
  }

  shareTwitter(): void {
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(this.getUrl())}&text=${encodeURIComponent(this.title())}`;
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  shareBluesky(): void {
    const text = `${this.title()} ${this.getUrl()}`;
    const url = `https://bsky.app/intent/compose?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank', 'noopener,width=550,height=420');
  }

  copyLink(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    navigator.clipboard.writeText(this.getUrl()).then(() => {
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    });
  }
}
