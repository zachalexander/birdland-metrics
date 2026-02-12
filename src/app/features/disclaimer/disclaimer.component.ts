import { Component, OnInit, inject } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-disclaimer',
  standalone: true,
  templateUrl: './disclaimer.component.html',
  styleUrl: './disclaimer.component.css',
})
export class DisclaimerComponent implements OnInit {
  private seo = inject(SeoService);

  constructor(
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    this.title.setTitle('Disclaimer — Birdland Metrics');
    this.meta.updateTag({ name: 'description', content: 'Disclaimer and legal information for Birdland Metrics.' });
    this.seo.setCanonicalUrl('/disclaimer');
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
  }
}
