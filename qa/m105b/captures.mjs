// M105-B P3 — captures : chaque couche corrigée SEULE puis EN COMBINAISON avec le zonage,
// vue claire ET vue sombre (non-régression). Les combinaisons zonage U + PPR et
// zonage U + ANRU sont LES captures qui décident (arbitrage Vic).
// BASE=http://localhost:5173/ node qa/m105b/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(25000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.click('button:has-text("Cartes")').catch(() => {});
await page.waitForTimeout(3000);

const shot = async (name, note) => { await page.screenshot({ path: `${OUT}/${name}.png` }); console.log(`📸 ${name} — ${note}`) };
// le tiroir Couches est rétracté sur l'accueil (et peut se refermer au changement de thème) —
// ne cliquer l'en-tête QUE si les libellés ne sont pas déjà visibles (le clic bascule)
const ouvrirCouches = async () => {
  if (await page.locator('text=PPR multirisque').first().isVisible().catch(() => false)) return;
  const header = page.locator('span.label-caps', { hasText: 'Couches' }).first();
  await header.click().catch(() => console.log('⚠ en-tête Couches introuvable'));
  await page.waitForTimeout(600);
};
const toggle = async (label) => {
  const cb = page.locator(`text=${label}`).first();
  await cb.click({ timeout: 5000 }).catch(() => console.log(`⚠ couche introuvable : ${label}`));
  await page.waitForTimeout(1400);
};
// le sélecteur de fond doit être OUVERT (bouton « Fond de plan ») avant de choisir le thème
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]').catch(() => {});
  await page.waitForTimeout(400);
  await page.getByRole('button', { name: label, exact: true }).first().click().catch(() => console.log(`⚠ fond introuvable : ${label}`));
  await page.waitForTimeout(600);
  // si le popup est resté ouvert, son écran de garde `fixed inset-0` intercepte TOUT clic :
  // un clic souris dessus (coin bas-gauche) le referme sans jamais atteindre la carte
  if (await page.locator('text=Remonter le temps').first().isVisible().catch(() => false)) {
    await page.mouse.click(400, 860);
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(2000);
  await ouvrirCouches();
};

// cadrer la côte ouest (Saint-Paul) : glisser la côte au centre puis zoomer par le
// bouton « Zoomer » (jamais de dblclick — il sélectionne une parcelle et ouvre la fiche)
const zoomOuest = async () => {
  await page.mouse.move(600, 430); await page.mouse.down();
  await page.mouse.move(880, 460, { steps: 12 }); await page.mouse.up();
  await page.waitForTimeout(800);
  for (let i = 0; i < 3; i++) { await page.click('button[title="Zoomer"]'); await page.waitForTimeout(900) }
  await page.waitForTimeout(1500);
};

const L = {
  zonage: 'Zones du PLU officiel (brut)', ppr: 'PPR multirisque',
  anru: 'ANRU (NPNRU)', pas: '50 pas géométriques',
};

await ouvrirCouches();
for (const theme of ['Clair', 'Sombre']) {
  const p = theme === 'Clair' ? 'clair' : 'sombre';
  await basemap(theme);
  if (theme === 'Clair') await shot(`00-${p}-ile-cote`, 'île entière — trait de côte + masse (Clair seulement)');
  if (theme === 'Clair') await zoomOuest();
  // chaque couche corrigée SEULE
  await toggle(L.zonage); await shot(`01-${p}-zonage-seul`, 'zonage seul (U vs non-U)');
  await toggle(L.zonage);
  await toggle(L.ppr); await shot(`02-${p}-ppr-seul`, 'PPR seul');
  await toggle(L.ppr);
  await toggle(L.anru); await shot(`03-${p}-anru-seul`, 'ANRU seul (trame en Clair)');
  await toggle(L.anru);
  await toggle(L.pas); await shot(`04-${p}-50pas-seul`, '50 pas seuls');
  await toggle(L.pas);
  // les COMBINAISONS QUI DÉCIDENT : zonage + PPR, zonage + ANRU
  await toggle(L.zonage); await toggle(L.ppr);
  await shot(`05-${p}-zonage+ppr`, 'COMBO décisive : zonage U + PPR');
  await toggle(L.ppr); await toggle(L.anru);
  await shot(`06-${p}-zonage+anru`, 'COMBO décisive : zonage U + ANRU');
  await toggle(L.anru); await toggle(L.pas);
  await shot(`07-${p}-zonage+50pas`, 'zonage + 50 pas (littoral)');
  await toggle(L.pas);
  // COMBO décisive sur de l'ANRU RÉEL : le cadre Saint-Paul n'en contient pas → glisser
  // vers Le Port (nord). Le pan ne s'exécute qu'en Clair ; le Sombre garde la même vue.
  if (theme === 'Clair') {
    await page.click('button[title="Dézoomer"]'); await page.waitForTimeout(900);
    for (let i = 0; i < 2; i++) {
      await page.mouse.move(1100, 240); await page.mouse.down();
      await page.mouse.move(1050, 720, { steps: 12 });
      await page.waitForTimeout(400);   // vitesse nulle au relâcher — pas d'inertie
      await page.mouse.up();
      await page.waitForTimeout(1000);
    }
    await page.waitForTimeout(1200);
  }
  await toggle(L.anru);
  await shot(`08-${p}-zonage+anru-leport`, 'COMBO décisive : zonage U + ANRU (Le Port)');
  // gros plan sur LE quartier NPNRU (repéré aux pixels dans le cadre 08) : c'est à l'échelle
  // de travail que trame + contour doivent trancher — la capture qui décide vraiment.
  if (theme === 'Clair') {
    await page.mouse.move(1279, 504); await page.mouse.down();
    await page.mouse.move(822, 460, { steps: 12 });
    await page.waitForTimeout(400);   // vitesse nulle au relâcher — sinon l'inertie emporte le cadre
    await page.mouse.up();
    await page.waitForTimeout(1000);
    for (let i = 0; i < 2; i++) { await page.click('button[title="Zoomer"]'); await page.waitForTimeout(900) }
    await page.waitForTimeout(1200);
  }
  await shot(`09-${p}-zonage+anru-quartier`, 'zonage U + ANRU — gros plan quartier NPNRU');
  await toggle(L.anru); await toggle(L.zonage);
}
await browser.close();
console.log(`Captures : ${OUT}`);
