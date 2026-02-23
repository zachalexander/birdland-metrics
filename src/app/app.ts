import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from './shared/components/header/header.component';
import { FooterComponent } from './shared/components/footer/footer.component';
import { NewsletterCtaComponent } from './shared/components/newsletter-cta/newsletter-cta.component';
import { SeoService } from './core/services/seo.service';
import { AnalyticsService } from './core/services/analytics.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, FooterComponent, NewsletterCtaComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private seo = inject(SeoService);
  private analytics = inject(AnalyticsService);

  ngOnInit(): void {
    this.seo.setJsonLd(this.seo.getOrganizationSchema());
    this.analytics.init();
  }
}
