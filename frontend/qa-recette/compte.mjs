// Famille 7 — Compte client. LECTURE SEULE, DESKTOP.
// Les pages du parcours compte (login/reset/invitation/onboarding/cgv/flash) sont rendues
// SERVEUR par l'API (origine 8798) ; le proxy dev du front (5998) ne les couvre pas.
// On teste donc : (a) l'AccountMenu + Signaler DANS l'app (5998), (b) les pages compte sur l'API.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const FRONT = 'http://localhost:5998/socle/';
const API = 'http://127.0.0.1:8798';
const FAM = '07-compte';
const DIR = `/Users/openclaw/Desktop/labuse-recette/docs/audit-2026-10/recette-generale-1/captures/${FAM}`;
mkdirSync(DIR, { recursive: true });
let cpt = 0;
async function shot(page, nom) {
  const safe = String(nom).replace(/[^a-zA-Z0-9_-]/g, '_');
  const p = `${DIR}/${String(++cpt).padStart(3, '0')}_${safe}.png`;
  await page.screenshot({ path: p });
  return p;
}
const BRUIT = [/\/moi\/prefs-carte/, /favicon/];
const estBruit = (u) => BRUIT.some((re) => re.test(u));

async function run() {
  const browser = await chromium.launch({ channel: 'chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const J = { console: [], http: [], pageerr: [] };
  const hook = (p) => {
    p.on('console', (m) => { const t = m.text(); if (m.type() === 'error' && !/Failed to load resource/i.test(t) && !estBruit(t)) J.console.push(t); });
    p.on('pageerror', (e) => J.pageerr.push(String(e)));
    p.on('response', (r) => { if (r.status() >= 400 && !estBruit(r.url())) J.http.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
  };
  hook(page);
  const out = {};

  // ÉTAPE 0 — l'app : AccountMenu (menu compte) + bouton Signaler
  try {
    await page.goto(FRONT, { waitUntil: 'domcontentloaded', timeout: 45000 });
    try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
    await page.waitForTimeout(1500);
    // ouvre le menu compte
    const btn = await page.$('[data-account-btn]');
    out.accountBtn = !!btn;
    if (btn) { await btn.click(); await page.waitForTimeout(600); }
    const menu = await page.$('[data-account-menu]');
    out.accountMenu = !!menu;
    out.menuText = menu ? (await menu.innerText()).replace(/\s+/g, ' ').slice(0, 300) : null;
    out.hasLogout = !!(await page.$('a[href="/logout"]'));
    out.hasMotdepasse = !!(await page.$('[data-account-motdepasse]'));
    await shot(page, 'app_menu_compte');
    // ferme le menu
    await page.keyboard.press('Escape').catch(() => {});
    await page.mouse.click(5, 400).catch(() => {});
    await page.waitForTimeout(300);
    // bouton Signaler
    const sig = await page.$('text=Signaler');
    out.hasSignaler = !!sig;
    if (sig) { await sig.click().catch(() => {}); await page.waitForTimeout(800); await shot(page, 'app_signaler_ouvert'); }
  } catch (e) { out.etape0_err = String(e).slice(0, 200); }

  // ÉTAPE 1 — /login (sur l'API) : auth désactivée → 302 vers l'app. On capture la page servie.
  const p2 = await context.newPage(); hook(p2);
  try {
    const resp = await p2.goto(API + '/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
    out.loginStatus = resp ? resp.status() : null;
    out.loginUrlFinal = p2.url();
    await p2.waitForTimeout(800);
    await shot(p2, 'login_api');
  } catch (e) { out.login_err = String(e).slice(0, 200); }

  // ÉTAPE 2 — /reset (formulaire mot de passe oublié)
  try {
    await p2.goto(API + '/reset', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p2.waitForTimeout(600);
    out.resetFormEmail = !!(await p2.$('#email'));
    out.resetTitle = (await p2.title());
    await shot(p2, 'reset_formulaire');
    // soumet pour un email VALIDE de test (ne change pas le mot de passe, pose juste un token)
    await p2.fill('#email', 'integral-7@labuse.test');
    await Promise.all([
      p2.waitForLoadState('domcontentloaded'),
      p2.click('button[type="submit"]'),
    ]);
    await p2.waitForTimeout(800);
    out.resetConfirmText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 260);
    await shot(p2, 'reset_demande_confirmee');
  } catch (e) { out.reset_err = String(e).slice(0, 200); }

  // ÉTAPE 2b — email INVALIDE / inexistant (anti-énumération : même réponse)
  try {
    await p2.goto(API + '/reset', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p2.fill('#email', 'inconnu-recette@nulle-part.test');
    await Promise.all([p2.waitForLoadState('domcontentloaded'), p2.click('button[type="submit"]')]);
    await p2.waitForTimeout(600);
    out.resetInconnuText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 220);
    await shot(p2, 'reset_email_inconnu');
  } catch (e) { out.reset2_err = String(e).slice(0, 200); }

  // ÉTAPE 3 — /invitation sans token (refus propre, pas de cul-de-sac)
  try {
    const r = await p2.goto(API + '/invitation', { waitUntil: 'domcontentloaded', timeout: 30000 });
    out.invitationStatus = r ? r.status() : null;
    await p2.waitForTimeout(400);
    out.invitationText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 200);
    out.invitationHasLogin = !!(await p2.$('a[href="/login"]'));
    await shot(p2, 'invitation_sans_token');
  } catch (e) { out.invit_err = String(e).slice(0, 200); }

  // ÉTAPE 4 — /cgv (page légale liée au parcours)
  try {
    const r = await p2.goto(API + '/cgv', { waitUntil: 'domcontentloaded', timeout: 30000 });
    out.cgvStatus = r ? r.status() : null;
    await p2.waitForTimeout(400);
    await shot(p2, 'cgv');
  } catch (e) { out.cgv_err = String(e).slice(0, 200); }

  // ÉTAPE 5 — /flash (offre self-service)
  try {
    const r = await p2.goto(API + '/flash', { waitUntil: 'domcontentloaded', timeout: 30000 });
    out.flashStatus = r ? r.status() : null;
    await p2.waitForTimeout(500);
    out.flashText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 220);
    await shot(p2, 'flash');
  } catch (e) { out.flash_err = String(e).slice(0, 200); }

  // ÉTAPE 6 — /onboarding/retour?ok=1 (page succès post-paiement) et ok=0 (interrompu)
  try {
    await p2.goto(API + '/onboarding/retour?ok=1', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p2.waitForTimeout(400);
    out.retourOkText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 200);
    await shot(p2, 'onboarding_retour_ok');
    await p2.goto(API + '/onboarding/retour?ok=0', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p2.waitForTimeout(400);
    out.retourKoText = (await p2.innerText('body')).replace(/\s+/g, ' ').slice(0, 200);
    await shot(p2, 'onboarding_retour_interrompu');
  } catch (e) { out.retour_err = String(e).slice(0, 200); }

  out.journal = { console: J.console.slice(0, 15), http: J.http.slice(0, 20), pageerr: J.pageerr.slice(0, 10) };
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
