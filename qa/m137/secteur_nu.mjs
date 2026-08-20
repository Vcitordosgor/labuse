import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97414000EN0451';
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
// fermer la liste d'autocomplétion de l'omnibox (elle est aussi `.floating`)
await page.keyboard.press('Escape').catch(() => {});
await page.locator('[data-bandeau-chiffres]').click({ position: { x: 5, y: 5 } }).catch(() => {});
await page.waitForTimeout(1200);
// lire le bandeau : label + valeur de la case SECTEUR
const info = await page.evaluate(() => {
  const stats = [...document.querySelectorAll('[data-bandeau-chiffres] .stat')];
  const sect = stats.find(s => /SECTEUR/.test(s.querySelector('.stat-l')?.textContent || ''));
  return {
    labels: stats.map(s => s.querySelector('.stat-l')?.textContent?.trim()),
    secteurLabel: sect?.querySelector('.stat-l')?.textContent?.replace(/\s+/g, ' ').trim(),
    secteurValeur: sect?.querySelector('.stat-v')?.textContent?.trim(),
    aUnI: !!sect?.querySelector('[aria-label^="Méthode"]'),
  };
});
console.log(JSON.stringify(info, null, 2));
// survoler le « i » pour révéler la méthode
await soft(async () => {
  const i = page.locator('[aria-label="Méthode : Secteur · nu"]');
  await i.scrollIntoViewIfNeeded(); await i.hover(); await page.waitForTimeout(900);
}, 'hover i');
const tip = await page.locator('.floating', { hasText: 'terrain nu' }).first().innerText().catch(() => '(pas de tooltip)');
console.log('TOOLTIP:', tip.replace(/\s+/g, ' ').trim());
await page.screenshot({ path: `${OUT}/secteur_nu.png` });
const head = page.locator('[data-bandeau-chiffres]');
await soft(async () => { const bx = await head.boundingBox(); if (bx) await page.screenshot({ path: `${OUT}/secteur_nu_zoom.png`, clip: { x: Math.max(0, bx.x - 10), y: Math.max(0, bx.y - 120), width: Math.min(bx.width + 20, 640), height: Math.min(bx.height + 240, 420) } }); }, 'zoom');
await b.close();
const ok = /^SECTEUR · NU/.test(info.secteurLabel || '') && info.aUnI && /€\/m²/.test(info.secteurValeur || '');
console.log(ok ? 'OK — « SECTEUR · NU » + valeur + « i »' : 'À VÉRIFIER');
