import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  PlayoffOdds,
  PlayoffOddsResponse,
  TeamStanding,
  StandingsResponse,
  TeamProjection,
  ProjectionsResponse,
  EloRating,
  EloResponse,
  RecentGame,
  RecentGamesResponse,
  EloHistoryPoint,
  PlayerStatsResponse,
} from '../../shared/models/mlb.models';

@Injectable({ providedIn: 'root' })
export class MlbDataService {
  private http = inject(HttpClient);
  private eloBase = environment.s3.eloRatings;
  private predBase = environment.s3.predictions;
  private statsBase = environment.s3.playerStats;

  async getPlayoffOdds(): Promise<{ updated: string; odds: PlayoffOdds[] }> {
    const res = await firstValueFrom(
      this.http.get<PlayoffOddsResponse>(`${this.predBase}/playoff-odds-latest.json`)
    );
    return { updated: res.updated, odds: res.odds };
  }

  async getStandings(): Promise<TeamStanding[]> {
    const res = await firstValueFrom(
      this.http.get<StandingsResponse>(`${this.predBase}/standings-latest.json`)
    );
    return res.standings;
  }

  async getProjections(): Promise<TeamProjection[]> {
    const res = await firstValueFrom(
      this.http.get<ProjectionsResponse>(`${this.predBase}/projections-latest.json`)
    );
    return res.projections;
  }

  async getEloRatings(): Promise<EloRating[]> {
    const res = await firstValueFrom(
      this.http.get<EloResponse>(`${this.eloBase}/elo-latest.json`)
    );
    return res.ratings;
  }

  async getEloHistory(teams: string[], season: number): Promise<Record<string, EloHistoryPoint[]>> {
    const result: Record<string, EloHistoryPoint[]> = {};
    const teamSet = new Set(teams);
    for (const team of teams) {
      result[team] = [];
    }

    // Fetch baseline ELO from prior season
    try {
      const baselineCsv = await firstValueFrom(
        this.http.get(`${this.eloBase}/elo_rating_end_of_${season - 1}.csv`, { responseType: 'text' })
      );
      const baseRows = baselineCsv.replace(/\r/g, '').trim().split('\n').map(r => r.split(','));
      const bHeader = baseRows[0];
      const bTeamIdx = bHeader.indexOf('team');
      const bEloIdx = bHeader.indexOf('elo');
      for (const row of baseRows.slice(1)) {
        const team = row[bTeamIdx];
        if (teamSet.has(team)) {
          result[team].push({ date: `${season}-03-01`, elo: parseFloat(row[bEloIdx]) });
        }
      }
    } catch {
      // No baseline available
    }

    // Fetch full history CSV and filter by season + teams
    // CSV columns: date,home_team,away_team,home_score,away_score,home_elo_before,away_elo_before,home_elo_after,away_elo_after
    const seasonPrefix = `${season}-`;
    try {
      const gameCsv = await firstValueFrom(
        this.http.get(`${this.eloBase}/elo-ratings-full-history.csv`, { responseType: 'text' })
      );
      const rows = gameCsv.replace(/\r/g, '').trim().split('\n');
      const header = rows[0].split(',');
      const dateIdx = header.indexOf('date');
      const homeTeamIdx = header.indexOf('home_team');
      const awayTeamIdx = header.indexOf('away_team');
      const homeEloPostIdx = header.indexOf('home_elo_after');
      const awayEloPostIdx = header.indexOf('away_elo_after');

      for (let i = rows.length - 1; i >= 1; i--) {
        const cols = rows[i].split(',');
        const date = cols[dateIdx];
        if (!date.startsWith(seasonPrefix)) {
          // Full history is chronological; once we pass the season, stop
          if (date < seasonPrefix) break;
          continue;
        }
        const homeTeam = cols[homeTeamIdx];
        const awayTeam = cols[awayTeamIdx];
        if (teamSet.has(homeTeam)) {
          result[homeTeam].push({ date, elo: parseFloat(cols[homeEloPostIdx]) });
        }
        if (teamSet.has(awayTeam)) {
          result[awayTeam].push({ date, elo: parseFloat(cols[awayEloPostIdx]) });
        }
      }

      // Reverse since we iterated backwards
      for (const team of teams) {
        result[team].sort((a, b) => a.date.localeCompare(b.date));
      }
    } catch {
      // Full history CSV not available
    }

    return result;
  }

  async getRecentGames(): Promise<{ gameType: 'R' | 'S'; games: RecentGame[] }> {
    const res = await firstValueFrom(
      this.http.get<RecentGamesResponse>(`${this.predBase}/recent-games-latest.json`)
    );
    return { gameType: res.game_type ?? 'R', games: res.games };
  }

  async getPlayerStats(): Promise<PlayerStatsResponse> {
    return firstValueFrom(
      this.http.get<PlayerStatsResponse>(`${this.statsBase}/player-stats-latest.json`)
    );
  }
}
