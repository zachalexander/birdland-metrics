import { Component, OnInit, inject } from '@angular/core';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-contact',
  standalone: true,
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.css',
})
export class ContactComponent implements OnInit {
  private seo = inject(SeoService);

  ngOnInit(): void {
    this.seo.setPageMeta({
      title: 'Contact — Birdland Metrics',
      description: 'Get in touch with Birdland Metrics for guest writing opportunities, questions, or feedback.',
      path: '/contact',
    });
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
  }
}
