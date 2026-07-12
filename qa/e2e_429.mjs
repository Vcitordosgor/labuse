// LA BUSE — régression Phase A2 (audit UI 11/07) : UX du 429 dans la fiche.
//   node qa/e2e_429.mjs        (l'app doit tourner : `labuse api` sur :8000, socle React)
// Un 429 (rate-limit/quota) doit afficher LE message dédié « Trop de requêtes » (+ retry
// auto programmé), JAMAIS « Le serveur est peut-être périmé ». Un 500 garde l'ancien état.
// Playwright : dépendance npm du front (fallback historique /opt/node22 si absent).
const pw = await import('../frontend/node_modules/playwright/index.mjs')
  .catch(() => import('/opt/node22/lib/node_modules/playwright/index.mjs'));
const { chromium } = pw;

const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const IDU = '97415000ZZ9999';   // fictif : la réponse est interceptée, jamais servie

// ── cas 1 : GET fiche → 429 : message dédié, pas « serveur périmé » ─────────────────────
await page.route(`**/parcels/${IDU}**`, (r) => r.fulfill({
  status: 429, contentType: 'application/json',
  body: JSON.stringify({ detail: 'Trop de requêtes (max 60/min). Résolvez le défi pour continuer.' }),
}));
await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 25000 });
await page.waitForFunction(() => window.__labuse, null, { timeout: 20000 });
await page.evaluate((idu) => window.__labuse.select(idu), IDU);
const bloc429 = page.locator('[data-ratelimit-429]');
await bloc429.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
const visible429 = await bloc429.isVisible();
const texte429 = visible429 ? await bloc429.textContent() : '';
ok('1.429-message-dedie', visible429 && /Trop de requêtes/.test(texte429 || ''),
   `visible=${visible429} texte="${(texte429 || '').slice(0, 60)}"`);
ok('2.429-pas-serveur-perime', !/périmé/.test(texte429 || ''));
ok('3.429-retry-annonce', /automatique/.test(texte429 || ''));
ok('4.429-detail-serveur-affiche', /défi|60\/min/.test(texte429 || ''),
   'le detail JSON du serveur remonte dans le bloc');

// ── cas 2 : GET fiche → 500 : l'état d'erreur générique reste inchangé ──────────────────
const IDU2 = '97415000ZZ9998';
await page.route(`**/parcels/${IDU2}**`, (r) => r.fulfill({
  status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }),
}));
await page.evaluate((idu) => window.__labuse.select(idu), IDU2);
// retry react-query (1 × ~1 s) puis état d'erreur — attente EXPLICITE du texte
const generique = await page.waitForFunction(
  () => document.body.innerText.includes('Impossible de charger la fiche'),
  null, { timeout: 8000 }).then(() => true).catch(() => false);
const persistant429 = await bloc429.isVisible().catch(() => false);
ok('5.500-message-generique-conserve', generique && !persistant429,
   `generique=${generique} bloc429=${persistant429}`);

await browser.close();
console.log(fails ? `\n${fails} échec(s)` : '\nOK — UX 429 conforme');
process.exit(fails ? 1 : 0);
