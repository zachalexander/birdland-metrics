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

  divisionPct(code: string): number {
    return this.odds().find(o => o.team === code)?.division_pct ?? 0;
  }

  wildcardPct(code: string): number {
    return this.odds().find(o => o.team === code)?.wildcard_pct ?? 0;
  }

  private static readonly TEAM_IDS: Record<string, number> = {
    BAL: 110, NYY: 147, BOS: 111, TB: 139, TOR: 141,
    CLE: 114, CWS: 145, DET: 116, KC: 118, MIN: 142,
    HOU: 117, LAA: 108, ATH: 133, SEA: 136, TEX: 140,
    ATL: 144, MIA: 146, NYM: 121, PHI: 143, WSH: 120,
    CHC: 112, CIN: 113, MIL: 158, PIT: 134, STL: 138,
    ARI: 109, COL: 115, LAD: 119, SD: 135, SF: 137,
  };

  teamLogo(code: string): string {
    const id = StandingsTableComponent.TEAM_IDS[code] ?? 0;
    return `https://www.mlbstatic.com/team-logos/${id}.svg`;
  }

  isOrioles(code: string): boolean {
    return code === 'BAL';
  }
}
