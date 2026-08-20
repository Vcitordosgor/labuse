import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('⚠', w, String(e).slice(0, 140)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3000);
await soft(async () => { await page.click('[data-filtres-toggle]'); await page.waitForTimeout(700); }, 'open filtres');
// aller au bloc Zonage et ouvrir la famille U en cliquant sur la LIGNE (pas un lien)
await soft(async () => {
  const fam = page.locator('[data-zones-fam="U"]');
  await fam.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await fam.click();                 // clic n'importe où sur la ligne → ouvre l'accordéon
  await page.waitForTimeout(900);
}, 'ouvrir accordeon U');
console.log('aria-expanded =', await page.locator('[data-zones-fam="U"]').getAttribute('aria-expanded'));
console.log('item « U seul » =', await page.locator('[data-zone-toutes="U"]').count());
console.log('nb sous-zones U =', await page.locator('[data-zone]').count());
// zoom sur le bloc zonage
const box = await page.locator('[data-zones-fam="U"]').locator('xpath=ancestor::div[contains(@class,"flex-col")][1]').boundingBox().catch(() => null);
await page.screenshot({ path: `${OUT}/accordeon_U_ouvert.png` });
if (box) await page.screenshot({ path: `${OUT}/accordeon_U_zoom.png`, clip: { x: Math.max(0, box.x - 6), y: Math.max(0, box.y - 6), width: Math.min(box.width + 12, 460), height: Math.min(box.height + 12, 640) } });
await b.close();
console.log('OK captures →', OUT);
