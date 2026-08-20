import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97421000AB0118';
const NEW = 'Commerces et services à proximité';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('⚠', w, String(e).slice(0, 160)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
await soft(async () => {
  const box = page.locator('[data-omnibox]');
  await box.click(); await box.fill(IDU); await page.waitForTimeout(700);
  await box.press('Enter'); await page.waitForTimeout(3800);
}, 'recherche IDU');
await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(() => console.log('⚠ fiche non ouverte'));
// attendre la FIN du chargement de la fiche (le libellé « Chargement… » disparaît)
await page.waitForFunction(() => !document.body.innerText.includes('Chargement de la fiche'), { timeout: 20000 }).catch(() => console.log('⚠ fiche encore en chargement'));
await page.waitForTimeout(2500);
// ouvrir la recherche INTRA-fiche et filtrer sur « Commerces » (révèle la ligne amenites, tous onglets)
await soft(async () => {
  await page.locator('button[title="Rechercher dans cette fiche"]').click();
  await page.waitForTimeout(500);
  await page.locator('[data-fiche-search]').fill('Commerces');
  await page.waitForTimeout(1500);
}, 'recherche intra-fiche');
const loc = page.getByText(NEW, { exact: false });
const n = await loc.count();
const jargon = await page.getByText(/Aménités/).count();
console.log(`« ${NEW} » dans la fiche : ${n} · « Aménités » (jargon) : ${jargon}`);
if (n > 0) { await loc.first().scrollIntoViewIfNeeded(); await page.waitForTimeout(400); }
await page.screenshot({ path: `${OUT}/fiche_amenites.png` });
const aside = page.locator('aside').filter({ has: page.locator('[data-fiche-idu]') }).first();
await soft(async () => { const bx = await aside.boundingBox(); if (bx) await page.screenshot({ path: `${OUT}/fiche_amenites_zoom.png`, clip: { x: bx.x, y: Math.max(0, bx.y), width: Math.min(bx.width, 640), height: Math.min(bx.height, 1024) } }); }, 'zoom aside');
await b.close();
console.log(n > 0 && jargon === 0 ? 'OK — libellé neuf servi, zéro jargon' : 'À VÉRIFIER');
