import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--no-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 2 });

await page.goto('http://localhost:4200', {
  waitUntil: 'networkidle0',
  timeout: 30000,
});

// Wait for the race section to load
await page.waitForSelector('.section-card-race', { timeout: 15000 });

// Click the 2025 toggle
await page.evaluate(() => {
  const buttons = document.querySelectorAll('.seg-btn');
  for (const btn of buttons) {
    if (btn.textContent.trim() === '2025') {
      btn.click();
      break;
    }
  }
});

// Small delay for data to load
await new Promise(r => setTimeout(r, 1500));

// Click the AL East toggle
await page.evaluate(() => {
  const buttons = document.querySelectorAll('.seg-btn');
  for (const btn of buttons) {
    if (btn.textContent.trim() === 'AL East') {
      btn.click();
      break;
    }
  }
});

// Wait for chart to re-render
await new Promise(r => setTimeout(r, 2000));

// Hide navbar
await page.evaluate(() => {
  const nav = document.querySelector('app-navbar, nav, header');
  if (nav) nav.style.display = 'none';
});

// Screenshot the race section
const raceSection = await page.$('.section-card-race');
const box = await raceSection.boundingBox();

await page.screenshot({
  path: '/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/race-tracker-2x.png',
  clip: {
    x: box.x,
    y: box.y,
    width: box.width,
    height: box.height,
  },
});

console.log(`Captured race tracker at ${Math.round(box.width * 2)}x${Math.round(box.height * 2)} (2x scale)`);
await browser.close();
