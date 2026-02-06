import { Component, OnInit, signal } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { ContentfulService } from '../../core/services/contentful.service';
import { BlogPost } from '../../shared/models/content.models';
import { ArticleCardComponent } from '../../shared/components/article-card/article-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [ArticleCardComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit {
  articles = signal<BlogPost[]>([]);
  loading = signal(true);

  constructor(
    private contentful: ContentfulService,
    private title: Title,
    private meta: Meta,
  ) {}

  ngOnInit(): void {
    this.title.setTitle('Birdland Metrics — Baseball Analytics & Insights');
    this.meta.updateTag({ name: 'description', content: 'Data-driven baseball analysis, visualizations, and insights.' });
    this.meta.updateTag({ property: 'og:title', content: 'Birdland Metrics — Baseball Analytics & Insights' });
    this.meta.updateTag({ property: 'og:description', content: 'Data-driven baseball analysis, visualizations, and insights.' });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this.meta.updateTag({ name: 'twitter:card', content: 'summary_large_image' });

    this.contentful
      .getArticles()
      .then((articles) => {
        this.articles.set(articles);
        this.loading.set(false);
      })
      .catch(() => this.loading.set(false));
  }
}
