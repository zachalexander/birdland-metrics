import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RecentGame, teamAbbr } from '../../../../shared/models/mlb.models';

@Component({
  selector: 'app-recent-games',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './recent-games.component.html',
  styleUrl: './recent-games.component.css',
})
export class RecentGamesComponent {
  games = input.required<RecentGame[]>();

  abbr(fullName: string): string {
    return teamAbbr(fullName);
  }

  isOriolesWin(game: RecentGame): boolean {
    return game.winning_team === 'Baltimore Orioles';
  }

  isOriolesLoss(game: RecentGame): boolean {
    return game.losing_team === 'Baltimore Orioles';
  }
}
