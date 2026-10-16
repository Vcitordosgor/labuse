// Famille 7 — ÉTAPE 5 (suite) : compléter le paiement Stripe Checkout TEST avec la carte 4242.
// Stripe Checkout met les champs carte dans des iframes imbriquées → on cible les frames.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const API = 'http://127.0.0.1:8798';
const TOKEN = process.argv[2];
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 30;
async function shot(page, nom) { const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`; await page.screenshot({ path: p }); return p; }

async function tryFillAcrossFrames(page, selectors, value) {
  for (const frame of page.frames()) {
    for (const sel of selectors) {
      try { const el = await frame.$(sel); if (el) { await el.click({ timeout: 2000 }).catch(() => {}); await el.fill(value, { timeout: 3000 }); return true; } } catch {}
    }
  }
  return false;
}

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const out = {};
  // invitation → form → bascule → payer
  await page.goto(`${API}/invitation?token=${TOKEN}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(600);
  await page.fill('#password', 'Recette-2026-Labuse!');
  await page.fill('#password2', 'Recette-2026-Labuse!');
  const cgv = await page.$('#cgv'); if (cgv) await cgv.check();
  await page.waitForTimeout(300);
  await Promise.all([page.waitForLoadState('domcontentloaded'), page.click('#cta')]);
  await page.waitForTimeout(800);
  await Promise.all([
    page.waitForNavigation({ url: /checkout\.stripe\.com/, timeout: 30000 }).catch(() => null),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForTimeout(4000);
  out.surStripe = /checkout\.stripe\.com/.test(page.url());
  const bodyTxt = (await page.innerText('body').catch(() => '')).toUpperCase();
  out.bandeauTest = /TEST MODE|ENVIRONNEMENT DE TEST|MODE TEST/.test(bodyTxt);
  if (!out.surStripe || !out.bandeauTest) { out.STOP = 'TEST non confirmé — aucune carte'; console.log(JSON.stringify(out, null, 2)); await browser.close(); return; }

  // attendre le chargement des iframes carte
  await page.waitForTimeout(2500);
  out.frames = page.frames().length;
  out.fCard = await tryFillAcrossFrames(page, ['input[name="cardNumber"]', 'input[autocomplete="cc-number"]'], '4242424242424242');
  out.fExp = await tryFillAcrossFrames(page, ['input[name="cardExpiry"]', 'input[autocomplete="cc-exp"]'], '1234');
  out.fCvc = await tryFillAcrossFrames(page, ['input[name="cardCvc"]', 'input[autocomplete="cc-csc"]'], '123');
  out.fName = await tryFillAcrossFrames(page, ['input[name="billingName"]', 'input#billingName', 'input[autocomplete="name"]'], 'Recette Test');
  out.fCp = await tryFillAcrossFrames(page, ['input[name="billingPostalCode"]', 'input[autocomplete="postal-code"]'], '97400');
  // pays si présent
  await tryFillAcrossFrames(page, ['input[autocomplete="country"]'], 'France').catch(() => {});
  await page.waitForTimeout(600);
  await shot(page, 'paiement_carte_saisie_v2');

  // soumettre
  let submit = await page.$('.SubmitButton, button[type="submit"]');
  if (!submit) { for (const f of page.frames()) { submit = await f.$('.SubmitButton, button[type="submit"]'); if (submit) break; } }
  if (submit) { await submit.click({ timeout: 5000 }).catch(() => {}); }
  // attendre redirection vers onboarding/retour (success_url) ou port public
  await page.waitForTimeout(9000);
  out.urlApresPaiement = page.url();
  out.retourText = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
  await shot(page, 'paiement_retour_v2');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
