import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97421000AB0118';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('⚠', w, String(e).slice(0, 160)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
await soft(async () => {
  const box = page.locator('[data-omnibox]');
  await box.click(); await box.fill(IDU); await page.waitForTimeout(700);
  await box.press('Enter'); await page.waitForTimeout(3800);
}, 'recherche IDU');
await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(() => console.log('⚠ fiche non ouverte'));
await page.waitForFunction(() => !document.body.innerText.includes('Chargement de la fiche'), { timeout: 20000 }).catch(() => {});
await page.waitForTimeout(2000);
// aller à la grille EXPORTS
await soft(async () => { await page.locator('.exp-grid').scrollIntoViewIfNeeded(); await page.waitForTimeout(800); }, 'scroll exports');
// mesures : nb de tuiles dans la grille, présence du Pré-dossier DANS la grille, plus de .exp-wide
const info = await page.evaluate(() => {
  const grid = document.querySelector('.fiche-v6 .exp-grid') || document.querySelector('.exp-grid');
  if (!grid) return { grid: false };
  const tiles = [...grid.children];
  const labels = tiles.map(t => (t.querySelector('span')?.textContent || t.textContent || '').trim());
  const pre = grid.querySelector('[data-predossier], [data-predossier-gate]');
  const preIdx = pre ? tiles.indexOf(pre.closest('.exp') || pre) : -1;
  return {
    grid: true,
    nbTiles: tiles.length,
    labels,
    predossierDansGrille: !!pre,
    predossierPosition: preIdx + 1,           // 1-based
    predossierClasse: pre ? pre.className : null,
    predossierHref: pre?.tagName === 'A' ? pre.getAttribute('href') : (pre?.getAttribute('data-predossier-gate') != null ? 'gated (plan non-intégral)' : null),
    expWideRestant: document.querySelectorAll('.exp-wide').length,
  };
});
console.log(JSON.stringify(info, null, 2));
await page.screenshot({ path: `${OUT}/exports_pleine.png` });
await soft(async () => {
  const bx = await page.locator('.exp-grid').boundingBox();
  if (bx) await page.screenshot({ path: `${OUT}/exports_grille.png`, clip: { x: Math.max(0, bx.x - 8), y: Math.max(0, bx.y - 40), width: Math.min(bx.width + 16, 700), height: Math.min(bx.height + 60, 400) } });
}, 'zoom grille');
await b.close();
const ok = info.grid && info.nbTiles === 8 && info.predossierDansGrille && info.predossierPosition === 8 && info.expWideRestant === 0;
console.log(ok ? 'OK — grille 4×2, Pré-dossier en 8e case (2e ligne, 4e col), plus de ligne pleine largeur' : 'À VÉRIFIER');
