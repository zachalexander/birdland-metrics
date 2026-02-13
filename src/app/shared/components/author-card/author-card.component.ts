import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Author } from '../../models/content.models';

@Component({
  selector: 'app-author-card',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './author-card.component.html',
  styleUrl: './author-card.component.css',
})
export class AuthorCardComponent {
  author = input.required<Author>();
}
