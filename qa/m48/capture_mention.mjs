// M48 — capture de la mention Renouvellement (filtre actif → « voie manuelle »).
import { chromium } from 'playwright';
const BASE = 'http://127.0.0.1:8000/socle/';
const OUT = 'qa/m48/captures';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
try {
  await page.getByText("Afficher l'analyse LABUSE", { exact: false }).first().click();
  await page.waitForSelector('[data-results-panel]', { timeout: 10000 });
  const panel = page.locator('[data-results-panel]');
  await panel.getByText('Ça va muter ?', { exact: false }).first().click();
  await page.waitForTimeout(300);
  await panel.getByText('Renouvellement', { exact: true }).first().click();
  await page.waitForTimeout(1500);
  await panel.getByText('voie manuelle', { exact: false }).first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/mention_renouvellement.png`, clip: { x: 0, y: 0, width: 372, height: 900 } });
  console.log('✓ mention_renouvellement.png');
} catch (e) {
  await page.screenshot({ path: `${OUT}/mention_renouvellement_FAIL.png` });
  console.log('✗', e.message);
}
await b.close();
