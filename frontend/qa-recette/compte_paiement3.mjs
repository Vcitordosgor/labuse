// ÉTAPE 5 — compléter le paiement test. Inspecte les inputs de chaque frame, remplit, soumet.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const API = 'http://127.0.0.1:8798';
const TOKEN = process.argv[2];
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 40;
async function shot(page, nom) { const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`; await page.screenshot({ path: p }); return p; }

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const out = {};
  await page.goto(`${API}/invitation?token=${TOKEN}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(600);
  await page.fill('#password', 'Recette-2026-Labuse!');
  await page.fill('#password2', 'Recette-2026-Labuse!');
  const cgv = await page.$('#cgv'); if (cgv) await cgv.check();
  await page.waitForTimeout(300);
  await Promise.all([page.waitForLoadState('domcontentloaded'), page.click('#cta')]);
  await page.waitForTimeout(800);
  await Promise.all([page.waitForNavigation({ url: /checkout\.stripe\.com/, timeout: 30000 }).catch(() => null), page.click('button[type="submit"]')]);
  await page.waitForTimeout(5000);
  out.surStripe = /checkout\.stripe\.com/.test(page.url());
  const bt = (await page.innerText('body').catch(() => '')).toUpperCase();
  out.bandeauTest = /ENVIRONNEMENT DE TEST|TEST MODE/.test(bt);
  if (!out.surStripe || !out.bandeauTest) { out.STOP = 'TEST non confirmé'; console.log(JSON.stringify(out)); await browser.close(); return; }

  // inspecter tous les inputs de tous les frames
  const inv = [];
  for (const f of page.frames()) {
    try {
      const ins = await f.$$eval('input', (els) => els.map((e) => ({ name: e.name || '', ph: e.placeholder || '', ac: e.getAttribute('autocomplete') || '', id: e.id || '', type: e.type })));
      if (ins.length) inv.push({ url: f.url().slice(0, 50), inputs: ins });
    } catch {}
  }
  out.inventaire = inv;

  // remplir par frame/nom découverts
  async function fill(frame, names, val) {
    for (const n of names) {
      const el = await frame.$(`input[name="${n}"]`).catch(() => null);
      if (el) { await el.click().catch(() => {}); await el.fill(val).catch(() => {}); return true; }
    }
    return false;
  }
  let done = { card: false, exp: false, cvc: false };
  for (const f of page.frames()) {
    if (!done.card) done.card = await fill(f, ['cardnumber', 'cardNumber', 'number'], '4242424242424242');
    if (!done.exp) done.exp = await fill(f, ['exp-date', 'cardExpiry', 'expiry'], '12 / 34');
    if (!done.cvc) done.cvc = await fill(f, ['cvc', 'cardCvc'], '123');
  }
  out.rempli = done;
  // champs top-level (nom, CP, pays)
  for (const n of ['billingName']) { const el = await page.$(`input[name="${n}"]`); if (el) await el.fill('Recette Test').catch(() => {}); }
  for (const n of ['billingPostalCode']) { const el = await page.$(`input[name="${n}"]`); if (el) await el.fill('97400').catch(() => {}); }
  await page.waitForTimeout(500);
  await shot(page, 'paiement_carte_v3');

  const submit = await page.$('.SubmitButton') || await page.$('button[type="submit"]');
  if (submit) await submit.click({ timeout: 5000 }).catch(() => {});
  await page.waitForNavigation({ url: /onboarding\/retour|127\.0\.0\.1/, timeout: 20000 }).catch(() => null);
  await page.waitForTimeout(6000);
  out.urlFin = page.url();
  out.retourFin = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 260);
  await shot(page, 'paiement_retour_v3');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
