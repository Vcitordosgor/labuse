// VUES & POLISH — E2E des 7 items (mandat 12/07/2026, décision produit « plateforme »).
// Usage : BASE=http://127.0.0.1:8020/socle/ node qa/vues/e2e.mjs
const pw = await import('../../frontend/node_modules/playwright/index.mjs');
const { chromium } = pw;
const BASE = process.env.BASE || 'http://127.0.0.1:8020/socle/';
let failed = 0;
const ok = (nom, cond, detail = '') => {
  console.log(`${cond ? '✓' : '✗'} ${nom}${cond ? '' : ` — ${detail}`}`);
  if (!cond) failed++;
};
const browser = await chromium.launch();
async function page(hash = '') {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await p.goto(BASE + hash, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await p.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
  await p.waitForTimeout(1200);
  return { ctx, p };
}

// ── 1 · renommage + route (alias legacy) ──
{
  const { ctx, p } = await page('#f=1&pg=segments');
  await p.waitForTimeout(1200);
  ok('1 · alias #pg=segments → page Vues', await p.locator('[data-seg-page] h1').textContent() === 'Vues');
  ok('1 · URL réécrite en pg=vues', /pg=vues/.test(p.url()));
  ok('1 · Rail dit « Vues », plus « Segments »', /Vues/.test(await p.locator('nav').textContent() || '')
    && !/Segments/.test(await p.locator('nav').textContent() || ''));

  // ── 2 · hiérarchie de la galerie ──
  const heroBox = await p.locator('[data-vues-hero]').boundingBox();
  const fonciereBox = await p.locator('[data-vue-fonciere]').boundingBox();
  const modelesBox = await p.locator('[data-vues-modeles]').boundingBox();
  ok('2 · ordre héros → Foncier → Modèles', !!heroBox && !!fonciereBox && !!modelesBox
    && heroBox.y < fonciereBox.y && fonciereBox.y < modelesBox.y);
  ok('2 · héros : NL intégrée + vue vierge', await p.locator('[data-vues-hero] [data-seg-nl-input]').count() === 1
    && await p.locator('[data-vues-builder-vierge]').count() === 1);
  ok('2 · copy Foncier (signal sourcé et daté)', /chaque signal sourcé et daté/.test(
    await p.locator('[data-vue-fonciere]').textContent() || ''));
  ok('2 · les 5 modèles restent', await p.locator('[data-vues-modeles] [data-seg-preset]').count() === 5);
  await p.locator('[data-vue-fonciere]').click();
  await p.waitForTimeout(2000);
  ok('2 · tuile Foncier → carte, analyse allumée', await p.locator('[data-verdict-off]').count() === 1);
  await ctx.close();
}

// ── 3 · chips du copilote EXÉCUTÉES (API réelle : traduction + restitution > 0) ──
{
  const { ctx, p } = await page();
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(800);
  const chips = await p.locator('[data-porte-recherche] .flex-wrap button').allTextContents();
  ok('3 · 6 exemples signaux différenciants', chips.length === 6 && chips.some((c) => /procédure collective/.test(c)),
    JSON.stringify(chips));
  await p.locator('[data-porte-recherche] .flex-wrap button', { hasText: 'procédure collective' }).first().click();
  await p.locator('[data-ia-restitution]').waitFor({ timeout: 60000 });
  await p.waitForTimeout(2500);
  const count = await p.locator('[data-ia-count]').textContent();
  ok('3 · chip exécutée → restitution > 0 résultats', (count || '0').trim() !== '0', `count=${count}`);
  ok('3 · traduction réelle (pas de badge stub)', await p.locator('[data-ia-badge-stub]').count() === 0);
  await ctx.close();
}

// ── 4 · Sources : fraîcheur prouvée ──
{
  const { ctx, p } = await page();
  await p.evaluate(() => window.__labuse.setView('sources'));
  await p.waitForTimeout(2000);
  const body = await p.locator('[data-sources-page]').textContent() || '';
  ok('4 · compteur « N/x sources datées » disparu', !/sources datées/.test(body));
  ok('4 · phrase « fraîcheur maximale, prouvée »', /fraîcheur maximale, prouvée/.test(body));
  ok('4 · « donnée du » sur les lignes datées', await p.locator('[data-source-donnee]').count() >= 50);
  ok('4 · zéro « vérifié le » tant que source_checks est vide',
    await p.locator('[data-source-verifiee]').count() === 0);
  await ctx.close();
}

// ── 5 + 6 · loupe alignée, sélecteur communes ──
{
  const { ctx, p } = await page();
  const m = await p.evaluate(() => {
    const box = document.querySelector('[data-omnibox]').parentElement;
    const btn = box.querySelector('button');
    const b1 = box.getBoundingClientRect(), b2 = btn.getBoundingClientRect();
    return { droite: Math.round(b1.right - b2.right), haut: Math.round(b2.top - b1.top) };
  });
  ok('5 · loupe : marges symétriques (±1 px)', Math.abs(m.droite - m.haut) <= 1, JSON.stringify(m));
  await p.locator('[data-commune-select]').click();
  await p.waitForTimeout(600);
  ok('6 · 24 liens « voir la fiche commune → »', await p.locator('[data-fiche-commune]').count() === 24);
  const dd = await p.evaluate(() => document.body.innerText);
  ok('6 · plus aucun « N chaudes » dans le sélecteur', !/\d+ chaudes?\b/.test(dd.split('Toute l’île')[1] || dd));
  await p.locator('[data-fiche-commune]').first().click();
  await p.waitForTimeout(2500);
  ok('6 · le lien ouvre le volet contexte commune', /SRU|PLH|ANRU/i.test(
    await p.evaluate(() => document.body.innerText)));
  await ctx.close();
}

await browser.close();
console.log(failed === 0 ? '\n── E2E Vues & polish : tout est vert ──' : `\n── ${failed} échec(s) ──`);
process.exit(failed === 0 ? 0 : 1);
