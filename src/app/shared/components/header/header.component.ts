import { Component, inject, signal, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ContentfulService } from '../../../core/services/contentful.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css',
})
export class HeaderComponent implements OnInit {
  private contentful = inject(ContentfulService);

  menuOpen = false;
  categoriesOpen = false;
  categories = signal<string[]>([]);

  ngOnInit(): void {
    this.contentful.getCategories().then(cats => this.categories.set(cats));
  }
}
