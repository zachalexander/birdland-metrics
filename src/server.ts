import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { join } from 'node:path';
import { createClient } from 'contentful';

const browserDistFolder = join(import.meta.dirname, '../browser');

const app = express();
app.use(express.json());
const angularApp = new AngularNodeAppEngine();

const SITE_URL = 'https://birdlandmetrics.com';
const ELO_S3_BASE = 'https://mlb-elo-ratings-output.s3.amazonaws.com';

// In-memory cache for parsed ELO CSV data
const eloCache = new Map<string, { data: string[][]; fetchedAt: number }>();
const ELO_CACHE_TTL = 60 * 60 * 1000; // 1 hour

async function fetchEloCsv(fileName: string): Promise<string[][]> {
  const cached = eloCache.get(fileName);
  if (cached && Date.now() - cached.fetchedAt < ELO_CACHE_TTL) {
    return cached.data;
  }
  const res = await fetch(`${ELO_S3_BASE}/${fileName}`);
  if (!res.ok) throw new Error(`S3 fetch failed: ${res.status}`);
  const text = await res.text();
  const rows = text.replace(/\r/g, '').trim().split('\n').map(line => line.split(','));
  eloCache.set(fileName, { data: rows, fetchedAt: Date.now() });
  return rows;
}

/**
 * ELO history API — returns per-game ELO for requested teams and season
 */
app.get('/api/elo-history', async (req, res) => {
  const teamParam = req.query['team'] as string | undefined;
  const seasonParam = req.query['season'] as string | undefined;

  if (!teamParam || !seasonParam) {
    res.status(400).json({ error: 'Missing required query params: team, season' });
    return;
  }

  const teams = teamParam.split(',').map(t => t.trim().toUpperCase());
  const season = parseInt(seasonParam, 10);
  if (isNaN(season)) {
    res.status(400).json({ error: 'Invalid season parameter' });
    return;
  }

  try {
    const teamSet = new Set(teams);
    const result: Record<string, { date: string; elo: number }[]> = {};
    for (const team of teams) {
      result[team] = [];
    }

    // Try to get starting ELO from prior season's end-of-year file
    try {
      const baselineRows = await fetchEloCsv(`elo_rating_end_of_${season - 1}.csv`);
      const baseHeader = baselineRows[0];
      const bTeamIdx = baseHeader.indexOf('team');
      const bEloIdx = baseHeader.indexOf('elo');
      for (const row of baselineRows.slice(1)) {
        const team = row[bTeamIdx];
        if (teamSet.has(team)) {
          result[team].push({ date: `${season}-03-01`, elo: parseFloat(row[bEloIdx]) });
        }
      }
    } catch {
      // No baseline available — skip
    }

    // Fetch full history CSV and filter by season
    // CSV columns: date,home_team,away_team,home_score,away_score,home_elo_before,away_elo_before,home_elo_after,away_elo_after
    try {
      const gameRows = await fetchEloCsv('elo-ratings-full-history.csv');
      const header = gameRows[0];
      const dateIdx = header.indexOf('date');
      const homeTeamIdx = header.indexOf('home_team');
      const awayTeamIdx = header.indexOf('away_team');
      const homeEloPostIdx = header.indexOf('home_elo_after');
      const awayEloPostIdx = header.indexOf('away_elo_after');
      const seasonPrefix = `${season}-`;

      for (const row of gameRows.slice(1)) {
        const date = row[dateIdx];
        if (!date.startsWith(seasonPrefix)) continue;
        const homeTeam = row[homeTeamIdx];
        const awayTeam = row[awayTeamIdx];
        if (teamSet.has(homeTeam)) {
          result[homeTeam].push({ date, elo: parseFloat(row[homeEloPostIdx]) });
        }
        if (teamSet.has(awayTeam)) {
          result[awayTeam].push({ date, elo: parseFloat(row[awayEloPostIdx]) });
        }
      }
    } catch {
      // Full history not available
    }

    res.set('Cache-Control', 'public, max-age=300');
    res.json({ teams: result });
  } catch (err) {
    console.error('ELO history fetch failed:', err);
    res.status(500).json({ error: 'Failed to fetch ELO history' });
  }
});

/**
 * Newsletter subscription — proxies to Buttondown API
 */
app.post('/api/newsletter', async (req, res) => {
  const { email } = req.body;
  if (!email || typeof email !== 'string') {
    res.status(400).json({ error: 'Email is required' });
    return;
  }

  const apiKey = process.env['BUTTONDOWN_API_KEY'];
  if (!apiKey) {
    console.error('BUTTONDOWN_API_KEY not set');
    res.status(500).json({ error: 'Newsletter service is not configured' });
    return;
  }

  try {
    const response = await fetch('https://api.buttondown.email/v1/subscribers', {
      method: 'POST',
      headers: {
        'Authorization': `Token ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email_address: email, type: 'regular' }),
    });

    if (response.ok) {
      res.json({ success: true });
      return;
    }

    const body = await response.json().catch(() => ({}));
    if (response.status === 400) {
      res.status(400).json({ error: 'This email is already subscribed.' });
      return;
    }

    console.error('Buttondown API error:', response.status, body);
    res.status(500).json({ error: 'Subscription failed. Please try again later.' });
  } catch (err) {
    console.error('Newsletter subscription failed:', err);
    res.status(500).json({ error: 'Subscription failed. Please try again later.' });
  }
});

/**
 * Dynamic sitemap.xml — queries Contentful for all articles
 */
app.get('/sitemap.xml', async (_req, res) => {
  try {
    const client = createClient({
      space: 'btpj5jq8xkdj',
      accessToken: '4fhLNRRGeWU2PoYE9z32gVJcjHQ_YR83KCOxFPwN9rE',
    });

    const entries = await client.getEntries({
      content_type: 'article',
      select: ['fields.slug', 'fields.tags', 'sys.updatedAt'],
      limit: 1000,
    });

    const categories = new Set<string>();
    const articles: { slug: string; updatedAt: string }[] = [];

    for (const entry of entries.items) {
      const fields = entry.fields as Record<string, unknown>;
      const slug = fields['slug'] as string;
      const tags = (fields['tags'] as string[]) ?? [];
      tags.forEach(t => categories.add(t));
      articles.push({ slug, updatedAt: entry.sys.updatedAt.split('T')[0] });
    }

    const urls = [
      `  <url><loc>${SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>`,
      `  <url><loc>${SITE_URL}/disclaimer</loc><changefreq>yearly</changefreq><priority>0.3</priority></url>`,
      `  <url><loc>${SITE_URL}/visualizations/spray-chart</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>`,
      `  <url><loc>${SITE_URL}/visualizations/elo-trends</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>`,
      `  <url><loc>${SITE_URL}/visualizations/win-distribution</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>`,
      ...[...categories].map(
        cat => `  <url><loc>${SITE_URL}/category/${cat}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>`
      ),
      ...articles.map(
        a => `  <url><loc>${SITE_URL}/articles/${a.slug}</loc><lastmod>${a.updatedAt}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>`
      ),
    ];

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>`;

    res.set('Content-Type', 'application/xml');
    res.set('Cache-Control', 'public, max-age=3600');
    res.send(xml);
  } catch (err) {
    console.error('Sitemap generation failed:', err);
    res.status(500).send('Sitemap generation failed');
  }
});

/**
 * Serve static files from /browser
 */
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

/**
 * Handle all other requests by rendering the Angular application.
 */
app.use((req, res, next) => {
  angularApp
    .handle(req)
    .then((response) =>
      response ? writeResponseToNodeResponse(response, res) : next(),
    )
    .catch(next);
});

/**
 * Start the server if this module is the main entry point, or it is ran via PM2.
 * The server listens on the port defined by the `PORT` environment variable, or defaults to 4000.
 */
if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = process.env['PORT'] || 4000;
  app.listen(port, (error) => {
    if (error) {
      throw error;
    }

    console.log(`Node Express server listening on http://localhost:${port}`);
  });
}

/**
 * Request handler used by the Angular CLI (for dev-server and during build) or Firebase Cloud Functions.
 */
export const reqHandler = createNodeRequestHandler(app);
