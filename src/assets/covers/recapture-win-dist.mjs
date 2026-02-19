import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--no-sandbox'],
});

const page = await browser.newPage();

// Use 2x device scale for crisp output (reduces graininess)
await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 2 });

await page.goto('http://localhost:4200/visualizations/win-distribution', {
  waitUntil: 'networkidle0',
  timeout: 30000,
});

// Wait for the chart SVG to render
await page.waitForSelector('.chart-container svg', { timeout: 15000 });

// Hide the navbar and any other chrome
await page.evaluate(() => {
  const nav = document.querySelector('app-navbar, nav, header');
  if (nav) nav.style.display = 'none';
  // Hide team picker and title
  const picker = document.querySelector('.team-picker');
  if (picker) picker.style.display = 'none';
  const title = document.querySelector('.chart-title');
  if (title) title.style.display = 'none';
});

// Small delay for layout to settle
await new Promise(r => setTimeout(r, 500));

// Screenshot just the chart container to capture full chart including x-axis label
const chartEl = await page.$('.chart-container');
const box = await chartEl.boundingBox();

// Add some padding at the bottom to ensure x-axis label is captured
await page.screenshot({
  path: '/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/win-dist-chart-2x.png',
  clip: {
    x: box.x,
    y: box.y,
    width: box.width,
    height: box.height + 10,
  },
});

console.log(`Captured chart at ${Math.round(box.width * 2)}x${Math.round((box.height + 10) * 2)} (2x scale)`);
await browser.close();
