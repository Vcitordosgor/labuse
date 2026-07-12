// Crawl systématique du socle : 6 vues × 3 viewports + 6 fiches contrastées × 7 onglets.
//   node qa/audit/crawl_socle.mjs        (app sur :8000, LABUSE_DEV_MODE=1 conseillé)
import { BASE, VIEWPORTS, boot, bilan, chromium, collecte, setCtx, shot, state, sauveJson, pushAnomalie } from './harness.mjs';

const VUES = ['cartes', 'crm', 'sources', 'segments', 'projets', 'ia'];
const PARCELLES = [
  ['brulante', '97414000CV0907'],
  ['v0', '97412000CE0989'],
  ['public', '97401000AB0001'],
  ['copro', '97411000BH0670'],
  ['sans-bati', '97411000KE0316'],
  ['littoral', '97411000CH0485'],
];
const TABS = ['Synthèse', 'Règles', 'Risques', 'Marché', 'Proprio', 'Solaire', 'Bilan'];

const browser = await chromium.launch();
const constats = [];   // observations factuelles (≠ anomalies auto) : {vue, viewport, note}

for (const [vpName, vp] of VIEWPORTS) {
  state.viewport = vpName;
  const ctx = await browser.newContext({ viewport: vp });
  const page = await ctx.newPage();
  collecte(page);
  setCtx('boot', `chargement ${vpName}`);
  await boot(page);
  await shot(page, 'boot');

  // ── les 6 vues du Rail ──
  for (const vue of VUES) {
    setCtx(vue, `setView(${vue})`);
    await page.evaluate((v) => window.__labuse.setView(v), vue);
    await page.waitForTimeout(1800);
    await shot(page, `vue_${vue}`);
    const txt = await page.evaluate(() => document.body.innerText);
    if (txt.trim().length < 40) constats.push({ vue, viewport: vpName, note: 'page quasi vide' });
    if (/undefined|NaN|null/.test(txt)) {
      const m = txt.match(/.{0,60}(undefined|NaN)....{0,40}/);
      constats.push({ vue, viewport: vpName, note: `littéral JS visible : ${m?.[0]?.replace(/\n/g, '⏎')}` });
    }
  }

  // ── fiches contrastées × onglets ──
  await page.evaluate(() => window.__labuse.setView('cartes'));
  for (const [nom, idu] of PARCELLES) {
    setCtx(`fiche:${nom}`, `select(${idu})`);
    await page.evaluate((i) => window.__labuse.select(i), idu);
    await page.waitForTimeout(2000);
    const err = await page.getByText('Impossible de charger la fiche').isVisible().catch(() => false);
    if (err) { pushAnomalie('fiche.erreur', `${nom} ${idu} : fiche en erreur`); continue; }
    for (const tab of TABS) {
      setCtx(`fiche:${nom}`, `onglet ${tab}`);
      const btn = page.locator(`[data-fiche] button, button`).filter({ hasText: new RegExp(`^${tab}$`) }).first();
      const ok = await btn.click({ timeout: 3000 }).then(() => true).catch(() => false);
      if (!ok) { constats.push({ vue: `fiche:${nom}`, viewport: vpName, note: `onglet ${tab} introuvable/inclickable` }); continue; }
      await page.waitForTimeout(900);
      await shot(page, `fiche_${nom}_${tab.normalize('NFD').replace(/[^\w]/g, '')}`);
      const txt = await page.evaluate(() => document.body.innerText);
      if (/undefined|NaN €|NaN %|NaN m/.test(txt)) {
        const m = txt.match(/.{0,60}(undefined|NaN).{0,40}/);
        constats.push({ vue: `fiche:${nom}:${tab}`, viewport: vpName, note: `littéral JS : ${m?.[0]?.replace(/\n/g, '⏎')}` });
      }
    }
    setCtx(`fiche:${nom}`, 'fermeture (Escape)');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    const encore = await page.evaluate(() => !!document.querySelector('[data-fiche]'));
    if (encore) constats.push({ vue: `fiche:${nom}`, viewport: vpName, note: 'Escape ne ferme pas la fiche' });
    await page.evaluate(() => window.__labuse.select(null));
    await page.waitForTimeout(300);
  }

  await ctx.close();
}

sauveJson('crawl_socle_constats', constats);
bilan('crawl_socle');
console.log(`constats manuels : ${constats.length}`);
for (const c of constats.slice(0, 40)) console.log(` · [${c.viewport}] ${c.vue} — ${c.note}`);
await browser.close();
