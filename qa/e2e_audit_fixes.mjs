// LA BUSE — régressions front de l'audit UI 12/07 :
//  1. compteur de restitution IA jamais négatif (rAF 1er timestamp < t0 → « -9 parcelles »)
//  2. omnibox : IDU hors commune active → la fiche s'ouvre quand même (recherche île entière)
//  3. omnibox : requête sans résultat → toast (jamais de no-op muet)
//   node qa/e2e_audit_fixes.mjs        (app :8000, LABUSE_DEV_MODE=1)
const pw = await import('../frontend/node_modules/playwright/index.mjs')
  .catch(() => import('/opt/node22/lib/node_modules/playwright/index.mjs'));
const { chromium } = pw;

const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
await page.waitForTimeout(1200);

// ── 1. compteur jamais négatif (repro déterministe en headless : frames affamées) ──
await page.evaluate(() => window.__labuse.setView('ia'));
const input = page.locator('[data-porte-recherche] input');
await input.fill('les chaudes de Saint-Pierre');
await input.press('Enter');
await page.waitForSelector('[data-ia-count]', { timeout: 30000 });
let minVu = Infinity;
for (let i = 0; i < 12; i++) {                     // on échantillonne PENDANT l'animation
  const t = await page.locator('[data-ia-count]').textContent().catch(() => null);
  const v = t == null ? null : parseInt(t.replace(/[^\d-]/g, ''), 10);
  if (Number.isFinite(v)) minVu = Math.min(minVu, v);
  await page.waitForTimeout(120);
}
ok('1.compteur-jamais-negatif', minVu >= 0, `min observé pendant l'animation : ${minVu}`);

// ── 2. IDU hors commune active : la fiche s'ouvre (recherche île entière) ──
await page.evaluate(() => { window.__labuse.select(null); window.__labuse.setCommune('Saint-Pierre') });
await page.waitForTimeout(800);
const box = page.locator('[data-omnibox]');
await box.fill('97414000CV0907');                  // parcelle de SAINT-LOUIS
await box.press('Enter');
await page.waitForTimeout(3000);
const ficheOuverte = await page.evaluate(() => document.body.innerText.includes('97414000CV0907'));
ok('2.idu-hors-commune-ouvre-fiche', ficheOuverte);
await page.keyboard.press('Escape');

// ── 3. requête sans résultat → toast visible ──
await box.fill('zzz-nexiste-pas');
await box.press('Enter');
const toast = page.locator('[data-toast]');
const toastVisible = await toast.waitFor({ state: 'visible', timeout: 6000 }).then(() => true).catch(() => false);
const toastTxt = toastVisible ? await toast.textContent() : '';
ok('3.sans-resultat-toast', toastVisible && /Aucune/.test(toastTxt || ''), `« ${(toastTxt || '').slice(0, 60)} »`);

await browser.close();
console.log(fails ? `\n${fails} échec(s)` : '\nOK — régressions front audit couvertes');
process.exit(fails ? 1 : 0);
