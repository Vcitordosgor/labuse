// ÉTAPE 5 final — remplir la carte test en attendant le chargement paresseux des iframes Stripe.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
const API = 'http://127.0.0.1:8798';
const TOKEN = process.argv[2];
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 50;
async function shot(page, nom) { const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`; await page.screenshot({ path: p }); return p; }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  const out = {};
  await page.goto(`${API}/invitation?token=${TOKEN}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(600);
  await page.fill('#password', 'Recette-2026-Labuse!');
  await page.fill('#password2', 'Recette-2026-Labuse!');
  const cgv = await page.$('#cgv'); if (cgv) await cgv.check();
  await sleep(300);
  await Promise.all([page.waitForLoadState('domcontentloaded'), page.click('#cta')]);
  await sleep(800);
  await Promise.all([page.waitForNavigation({ url: /checkout\.stripe\.com/, timeout: 30000 }).catch(() => null), page.click('button[type="submit"]')]);
  // attendre le rendu complet du formulaire de paiement
  await sleep(8000);
  out.bandeauTest = /ENVIRONNEMENT DE TEST|TEST MODE/i.test(await page.innerText('body').catch(() => ''));
  if (!out.bandeauTest) { out.STOP = 'TEST non confirmé'; console.log(JSON.stringify(out)); await browser.close(); return; }

  // Stripe Checkout : utiliser getByLabel / placeholders FR dans les iframes
  async function fillByLabelAllFrames(labels, value) {
    for (const f of page.frames()) {
      for (const lbl of labels) {
        try { const loc = f.getByLabel(lbl, { exact: false }); if (await loc.count()) { await loc.first().click({ timeout: 1500 }).catch(() => {}); await loc.first().fill(value, { timeout: 2500 }); return true; } } catch {}
        try { const ph = f.getByPlaceholder(lbl, { exact: false }); if (await ph.count()) { await ph.first().fill(value, { timeout: 2500 }); return true; } } catch {}
      }
    }
    return false;
  }
  out.card = await fillByLabelAllFrames(['Numéro de carte', 'Card number', 'carte'], '4242424242424242');
  out.exp = await fillByLabelAllFrames(['expiration', 'MM / AA', 'MM / YY', 'Expiry'], '12 / 34');
  out.cvc = await fillByLabelAllFrames(['CVC', 'Code de sécurité', 'CVV'], '123');
  // nom + CP au niveau page
  try { const n = page.getByLabel('Nom', { exact: false }); if (await n.count()) await n.first().fill('Recette Test'); } catch {}
  try { const cp = page.getByLabel('postal', { exact: false }); if (await cp.count()) await cp.first().fill('97400'); } catch {}
  await sleep(600);
  await shot(page, 'paiement_carte_final');

  // soumettre
  let clicked = false;
  try { const b = page.getByTestId('hosted-payment-submit-button'); if (await b.count()) { await b.click(); clicked = true; } } catch {}
  if (!clicked) { const b = await page.$('.SubmitButton') || await page.$('button[type="submit"]'); if (b) { await b.click().catch(() => {}); clicked = true; } }
  out.clicked = clicked;
  await page.waitForNavigation({ url: /onboarding\/retour|127\.0\.0\.1:800?0/, timeout: 25000 }).catch(() => null);
  await sleep(6000);
  out.urlFin = page.url();
  out.retourFin = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
  await shot(page, 'paiement_retour_final');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
