import { Component, OnInit, inject } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-contact',
  standalone: true,
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.css',
})
export class ContactComponent implements OnInit {
  private seo = inject(SeoService);

  constructor(
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    this.title.setTitle('Contact — Birdland Metrics');
    this.meta.updateTag({ name: 'description', content: 'Get in touch with Birdland Metrics for guest writing opportunities, questions, or feedback.' });
    this.seo.setCanonicalUrl('/contact');
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
  }
}
