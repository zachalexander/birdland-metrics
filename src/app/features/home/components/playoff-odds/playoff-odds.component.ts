import { Component, input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { PlayoffOdds } from '../../../../shared/models/mlb.models';

@Component({
  selector: 'app-playoff-odds',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './playoff-odds.component.html',
  styleUrl: './playoff-odds.component.css',
})
export class PlayoffOddsComponent {
  odds = input.required<PlayoffOdds | null>();
}
