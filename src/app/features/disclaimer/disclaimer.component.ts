import { Component, OnInit, inject } from '@angular/core';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-disclaimer',
  standalone: true,
  templateUrl: './disclaimer.component.html',
  styleUrl: './disclaimer.component.css',
})
export class DisclaimerComponent implements OnInit {
  private seo = inject(SeoService);

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Disclaimer — Birdland Metrics',
      description: 'Disclaimer and legal information for Birdland Metrics.',
      path: '/disclaimer',
    });
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
  }
}
