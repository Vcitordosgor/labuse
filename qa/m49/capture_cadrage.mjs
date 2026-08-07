// M49 Lot C — capture de la phrase de cadrage IA (AskBar fiche + écran Copilote).
import { chromium } from 'playwright';
const BASE = 'http://127.0.0.1:8000/socle/';
const OUT = 'qa/m49/captures';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
async function go() { await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(1500); }

// 1) AskBar (fiche) : ouvrir une fiche, déplier l'IA, capturer le cadrage
await go();
await page.evaluate((idu) => window.__labuse.select(idu), '97418000AT2542');
await page.waitForTimeout(1500);
try {
  const trigger = page.locator('text=/Demander|question sur cette parcelle/i').first();
  await trigger.click();
  await page.waitForSelector('[data-avis-ia]', { timeout: 8000 });
  await page.locator('[data-avis-ia]').first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/cadrage_askbar.png` });
  console.log('✓ cadrage_askbar.png');
} catch (e) { await page.screenshot({ path: `${OUT}/cadrage_askbar_FAIL.png` }); console.log('✗ askbar', e.message); }

// 2) Copilote : ouvrir l'écran Copilote, capturer le cadrage
await go();
try {
  await page.evaluate(() => window.__labuse.setModule && window.__labuse.setModule('copilote'));
  await page.waitForTimeout(800);
  const nav = page.locator('text=Copilote').first();
  if (await nav.count()) { await nav.click(); await page.waitForTimeout(1200); }
  await page.waitForSelector('[data-avis-ia]', { timeout: 8000 });
  await page.locator('[data-avis-ia]').first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/cadrage_copilote.png` });
  console.log('✓ cadrage_copilote.png');
} catch (e) { await page.screenshot({ path: `${OUT}/cadrage_copilote_FAIL.png` }); console.log('✗ copilote', e.message); }
await b.close();
