// Captures complémentaires : .eml ouvert (étape 7), flash checkout test (étape 5 bis).
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const API = 'http://127.0.0.1:8798';
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 60;
async function shot(page, nom) { const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`; await page.screenshot({ path: p }); return p; }
const EML = process.argv[2];
async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const page = await context.newPage();
  const out = {};
  // 1) .eml dry-run ouvert dans le navigateur (preuve lisible)
  if (EML) {
    await page.goto('file://' + EML, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(400);
    await shot(page, 'eml_dryrun_ouvert');
  }
  // 2) Flash : POST idu + cgv → checkout test (79€ one-shot)
  const IDU = '97415000DT0397';
  await page.goto(`${API}/flash?idu=${IDU}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(600);
  await shot(page, 'flash_parcelle');
  // cocher CGV + payer si présent
  const cgv = await page.$('input[name="cgv"], #cgv'); if (cgv) await cgv.check().catch(() => {});
  await page.waitForTimeout(300);
  const pay = await page.$('button[type="submit"]');
  if (pay) {
    await Promise.all([page.waitForNavigation({ url: /checkout\.stripe\.com/, timeout: 30000 }).catch(() => null), pay.click()]);
    await page.waitForTimeout(4000);
  }
  out.flashSurStripe = /checkout\.stripe\.com/.test(page.url());
  const bt = (await page.innerText('body').catch(() => '')).toUpperCase();
  out.flashTest = /ENVIRONNEMENT DE TEST|TEST MODE/.test(bt);
  out.flashExtrait = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 240);
  await shot(page, 'flash_checkout_test');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
