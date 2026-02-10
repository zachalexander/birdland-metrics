import { Component, ElementRef, AfterViewInit, input, viewChild, effect } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RecentGame, teamAbbr } from '../../../../shared/models/mlb.models';

@Component({
  selector: 'app-recent-games',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './recent-games.component.html',
  styleUrl: './recent-games.component.css',
})
export class RecentGamesComponent implements AfterViewInit {
  games = input.required<RecentGame[]>();
  gameType = input<'R' | 'S'>('R');
  gamesGrid = viewChild<ElementRef>('gamesGrid');

  canScrollLeft = false;
  canScrollRight = false;

  constructor() {
    // Re-check scroll state whenever games input changes
    effect(() => {
      this.games();
      setTimeout(() => this.updateScrollState(), 50);
    });
  }

  ngAfterViewInit(): void {
    const el = this.gamesGrid()?.nativeElement;
    if (el) {
      el.addEventListener('scroll', () => this.updateScrollState());
      this.updateScrollState();
    }
  }

  abbr(fullName: string): string {
    return teamAbbr(fullName);
  }

  isOriolesWin(game: RecentGame): boolean {
    return game.winning_team === 'Baltimore Orioles';
  }

  isOriolesLoss(game: RecentGame): boolean {
    return game.losing_team === 'Baltimore Orioles';
  }

  scrollRight(): void {
    const el = this.gamesGrid()?.nativeElement;
    if (el) {
      el.scrollBy({ left: 240, behavior: 'smooth' });
      setTimeout(() => this.updateScrollState(), 350);
    }
  }

  scrollLeft(): void {
    const el = this.gamesGrid()?.nativeElement;
    if (el) {
      el.scrollBy({ left: -240, behavior: 'smooth' });
      setTimeout(() => this.updateScrollState(), 350);
    }
  }

  private updateScrollState(): void {
    const el = this.gamesGrid()?.nativeElement;
    if (!el) return;
    this.canScrollLeft = el.scrollLeft > 0;
    this.canScrollRight = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
  }
}
