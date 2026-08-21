// M137-W — capture équipements OSM (sport) sur Saint-Paul, à l'échelle rue. argv[2] = nom de fichier.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const OUT = new URL('./captures', import.meta.url).pathname;
const FILE = process.argv[2] || 'sport.png';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 140)) } };
const openCouches = async () => { if (await page.locator('[data-layer="parcelles"]').isVisible().catch(() => false)) return; const t = page.locator('[data-couches-toggle]').first(); if (await t.count()) { await t.click(); await page.waitForTimeout(500); } };
const pickCommune = async (n) => { await page.locator('[data-commune-select]').click(); await page.waitForTimeout(500); await page.getByRole('button', { name: n, exact: true }).click(); await page.waitForTimeout(3000); };

await page.goto('http://localhost:5173/socle/', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);
await openCouches();
await soft(async () => { await page.locator('[data-layer="equipements"]').click(); await page.waitForTimeout(400); }, 'OSM on');
await soft(() => pickCommune('Saint-Paul'), 'commune');
await soft(async () => { for (let i = 0; i < 2; i++) { await page.mouse.move(880, 500); await page.mouse.wheel(0, -500); await page.waitForTimeout(700); } await page.waitForTimeout(1500); }, 'zoom');
await page.screenshot({ path: `${OUT}/${FILE}`, fullPage: false });
await b.close();
console.log('capture', FILE);
