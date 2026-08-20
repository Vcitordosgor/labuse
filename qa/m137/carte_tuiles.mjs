import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
let tiles = 0, tile500 = 0, ok = 0;
page.on('response', (r) => {
  const u = r.url();
  if (u.includes('/map/tiles/') && u.endsWith('.pbf')) {
    tiles++;
    if (r.status() === 500) { tile500++; console.log('⚠ TUILE 500', u); }
    else if (r.status() === 200) ok++;
  }
});
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('⚠', w, String(e).slice(0, 140)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(6000);               // laisse la carte demander ses tuiles
await soft(async () => { await page.click('[data-view="cartes"]'); await page.waitForTimeout(2500); }, 'vue cartes');
await page.waitForTimeout(4000);
await page.screenshot({ path: `${OUT}/carte_chargee.png` });
console.log(`tuiles .pbf demandées=${tiles} · 200=${ok} · 500=${tile500}`);
await b.close();
if (tile500 > 0) { console.log('ÉCHEC : des tuiles lèvent encore'); process.exit(1); }
console.log('OK — la carte charge, aucune tuile 500');
