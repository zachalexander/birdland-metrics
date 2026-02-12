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
const angularApp = new AngularNodeAppEngine();

const SITE_URL = 'https://birdlandmetrics.com';

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
