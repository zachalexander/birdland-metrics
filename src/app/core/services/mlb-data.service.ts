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
} from '../../shared/models/mlb.models';

@Injectable({ providedIn: 'root' })
export class MlbDataService {
  private http = inject(HttpClient);
  private eloBase = environment.s3.eloRatings;
  private predBase = environment.s3.predictions;

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

  async getRecentGames(): Promise<{ gameType: 'R' | 'S'; games: RecentGame[] }> {
    const res = await firstValueFrom(
      this.http.get<RecentGamesResponse>(`${this.predBase}/recent-games-latest.json`)
    );
    return { gameType: res.game_type ?? 'R', games: res.games };
  }
}
