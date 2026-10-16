// Famille 7 — ÉTAPE 5 : parcours paiement client → Stripe Checkout TEST.
// SÛRETÉ : on VÉRIFIE le bandeau TEST avant toute carte ; carte test 4242 UNIQUEMENT.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const API = 'http://127.0.0.1:8798';
const TOKEN = process.argv[2];
if (!TOKEN) { console.error('usage: node compte_paiement.mjs <token>'); process.exit(1); }
const DIR = '/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/07-compte';
mkdirSync(DIR, { recursive: true });
let cpt = 20; // continue la numérotation après compte.mjs
async function shot(page, nom) {
  const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${nom}.png`;
  await page.screenshot({ path: p });
  return p;
}

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const J = { http: [], pageerr: [] };
  page.on('response', (r) => { if (r.status() >= 400 && !/favicon|prefs-carte/.test(r.url())) J.http.push(`${r.status()} ${r.url().slice(0, 90)}`); });
  page.on('pageerror', (e) => J.pageerr.push(String(e)));
  const out = {};

  // 1) page invitation (créer son accès)
  await page.goto(`${API}/invitation?token=${TOKEN}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(800);
  out.invTitle = await page.title();
  out.invText = (await page.innerText('body')).replace(/\s+/g, ' ').slice(0, 220);
  await shot(page, 'paiement_1_invitation');

  // 2) remplir mot de passe + confirmation + CGV
  await page.fill('#password', 'Recette-2026-Labuse!');
  await page.fill('#password2', 'Recette-2026-Labuse!');
  const cgv = await page.$('#cgv'); if (cgv) await cgv.check();
  await page.waitForTimeout(400);
  await shot(page, 'paiement_2_form_rempli');

  // 3) submit → bascule /onboarding/paiement
  await Promise.all([page.waitForLoadState('domcontentloaded'), page.click('#cta')]);
  await page.waitForTimeout(1000);
  out.urlApresInvit = page.url();
  out.basculeText = (await page.innerText('body')).replace(/\s+/g, ' ').slice(0, 260);
  await shot(page, 'paiement_3_bascule');

  // 4) clic « Payer » → Stripe Checkout
  const payBtn = await page.$('button[type="submit"]');
  out.hasPayBtn = !!payBtn;
  if (payBtn) {
    await Promise.all([
      page.waitForNavigation({ url: /checkout\.stripe\.com|stripe/, timeout: 30000 }).catch(() => null),
      payBtn.click(),
    ]);
  }
  await page.waitForTimeout(3000);
  out.urlCheckout = page.url();
  out.surStripe = /checkout\.stripe\.com/.test(page.url());
  await shot(page, 'paiement_4_checkout');

  // 5) VÉRIFIER le bandeau TEST MODE avant toute carte
  if (out.surStripe) {
    const bodyTxt = (await page.innerText('body').catch(() => '')).toUpperCase();
    out.bandeauTest = /TEST MODE|MODE TEST|TEST/.test(bodyTxt);
    out.checkoutExtrait = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 300);
    // décision de sûreté : ne saisir la carte QUE si TEST confirmé
    if (out.bandeauTest) {
      try {
        // Stripe Checkout : champs cardNumber/exp/cvc (souvent en iframe ou inline hosted)
        const fillIf = async (sel, val) => { const el = await page.$(sel); if (el) { await el.fill(val); return true; } return false; };
        out.fCard = await fillIf('input[name="cardNumber"], input[autocomplete="cc-number"]', '4242 4242 4242 4242');
        out.fExp = await fillIf('input[name="cardExpiry"], input[autocomplete="cc-exp"]', '12 / 34');
        out.fCvc = await fillIf('input[name="cardCvc"], input[autocomplete="cc-csc"]', '123');
        await fillIf('input[name="billingName"], input[autocomplete="name"]', 'Recette Test');
        await fillIf('input[name="billingPostalCode"], input[autocomplete="postal-code"]', '97400');
        await shot(page, 'paiement_5_carte_saisie');
        // soumettre le paiement test
        const submit = await page.$('button[type="submit"], .SubmitButton');
        if (submit) {
          await submit.click().catch(() => {});
          await page.waitForTimeout(8000);
        }
        out.urlApresPaiement = page.url();
        out.retourText = (await page.innerText('body').catch(() => '')).replace(/\s+/g, ' ').slice(0, 260);
        await shot(page, 'paiement_6_retour');
      } catch (e) { out.carte_err = String(e).slice(0, 200); }
    } else {
      out.STOP = 'Bandeau TEST non confirmé — AUCUNE carte saisie (sûreté).';
    }
  }

  out.journal = { http: J.http.slice(0, 15), pageerr: J.pageerr.slice(0, 5) };
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
