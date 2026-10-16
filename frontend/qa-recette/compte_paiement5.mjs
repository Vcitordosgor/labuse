// ÉTAPE 5 — completion : sélectionner le radio « Carte » (accordéon) PUIS remplir les champs iframe.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const API = 'http://127.0.0.1:8798';
const TOKEN = process.argv[2];
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 70;
async function shot(page, nom) { const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`; await page.screenshot({ path: p }); return p; }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  const out = {};
  await page.goto(`${API}/invitation?token=${TOKEN}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(600);
  await page.fill('#password', 'Recette-2026-Labuse!'); await page.fill('#password2', 'Recette-2026-Labuse!');
  const cgv = await page.$('#cgv'); if (cgv) await cgv.check();
  await sleep(300);
  await Promise.all([page.waitForLoadState('domcontentloaded'), page.click('#cta')]); await sleep(800);
  await Promise.all([page.waitForNavigation({ url: /checkout\.stripe\.com/, timeout: 30000 }).catch(() => null), page.click('button[type="submit"]')]);
  await sleep(6000);
  out.bandeauTest = /ENVIRONNEMENT DE TEST|TEST MODE/i.test(await page.innerText('body').catch(() => ''));
  if (!out.bandeauTest) { out.STOP = 'TEST non confirmé'; console.log(JSON.stringify(out)); await browser.close(); return; }

  // sélectionner l'accordéon « Carte »
  try { const r = page.getByText(/^Carte$/).first(); if (await r.count()) await r.click({ timeout: 4000 }); } catch {}
  try { const rad = await page.$('input[type="radio"][value="card"], #card-tab, [data-testid="card-accordion-item-button"]'); if (rad) await rad.click().catch(() => {}); } catch {}
  await sleep(2500);
  await shot(page, 'paiement_carte_accordeon_ouvert');

  // maintenant les iframes carte doivent exister
  async function fillFrames(names, val) {
    for (const f of page.frames()) {
      for (const n of names) {
        const el = await f.$(`input[name="${n}"]`).catch(() => null);
        if (el) { await el.click().catch(() => {}); await el.fill(val).catch(() => {}); return true; }
      }
    }
    return false;
  }
  out.card = await fillFrames(['number', 'cardnumber', 'cardNumber'], '4242 4242 4242 4242');
  out.exp = await fillFrames(['expiry', 'exp-date', 'cardExpiry'], '12 / 34');
  out.cvc = await fillFrames(['cvc', 'cardCvc'], '123');
  // nom / pays / cp éventuels au top-level
  for (const n of ['billingName']) { const e = await page.$(`input[name="${n}"]`); if (e) await e.fill('Recette Test').catch(() => {}); }
  for (const n of ['billingPostalCode']) { const e = await page.$(`input[name="${n}"]`); if (e) await e.fill('97400').catch(() => {}); }
  await sleep(500);
  await shot(page, 'paiement_carte_remplie');

  // soumettre
  let b = await page.$('[data-testid="hosted-payment-submit-button"]') || await page.$('.SubmitButton') || await page.$('button[type="submit"]');
  if (b) await b.click({ timeout: 5000 }).catch(() => {});
  await page.waitForNavigation({ url: /onboarding\/retour|127\.0\.0\.1:800?0/, timeout: 30000 }).catch(() => null);
  await sleep(6000);
  out.urlFin = page.url();
  out.retourFin = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 260);
  await shot(page, 'paiement_retour_succes');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
