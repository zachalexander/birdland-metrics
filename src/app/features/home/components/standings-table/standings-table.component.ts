import { Component, input, computed } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { TeamProjection, PlayoffOdds, AL_EAST, TEAM_NAMES } from '../../../../shared/models/mlb.models';

@Component({
  selector: 'app-standings-table',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './standings-table.component.html',
  styleUrl: './standings-table.component.css',
})
export class StandingsTableComponent {
  projections = input.required<TeamProjection[]>();
  odds = input.required<PlayoffOdds[]>();

  divisionTeams = computed(() => {
    const all = this.projections();
    return AL_EAST
      .map(code => all.find(t => t.team === code))
      .filter((t): t is TeamProjection => !!t)
      .sort((a, b) => b.median_wins - a.median_wins);
  });

  teamName(code: string): string {
    return TEAM_NAMES[code] ?? code;
  }

  projLosses(wins: number): number {
    return 162 - Math.round(wins);
  }

  playoffPct(code: string): number {
    return this.odds().find(o => o.team === code)?.playoff_pct ?? 0;
  }

  isOrioles(code: string): boolean {
    return code === 'BAL';
  }
}
