// M14 LOT G — re-vérification SUR MAIN MERGÉE (:8050/socle/), les 8 points.
// La preuve qui compte : sur main, pas sur les branches isolées.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8050/socle/';
const OUT = new URL('./G', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
const R = {};
async function shot(n){ await p.screenshot({ path: `${OUT}/${n}.png` }); }

await p.goto(BASE, { waitUntil: 'networkidle' }); await p.waitForTimeout(1800);

// ── B3 : Couches ouvert par défaut au chargement
R.B3_couches_ouvert = (await p.locator('[data-couches-drawer]').count()) > 0;
await shot('g_b3_couches_ouvert');

// ── B1 : bulle « i » entière (survol pastille i d'une couche à long texte)
const pills = p.locator('[aria-label="En savoir plus sur cette couche"]');
await pills.nth(Math.min(4, (await pills.count()) - 1)).hover(); await p.waitForTimeout(700);
const tip = p.locator('[role="tooltip"]').first();
const tbox = await tip.boundingBox().catch(() => null);
R.B1_bulle_non_rognee = !!tbox && (tbox.x + tbox.width <= 1440) && (tbox.x >= 0);
R.B1_texte = tbox ? (await tip.innerText()).length : 0;
await shot('g_b1_bulle_i');

// ── D1 : placeholder ; D2 : barre cliquable bord à bord
const omni = p.locator('[data-omnibox]').first();
R.D1_placeholder = await omni.getAttribute('placeholder');
const obox = await omni.boundingBox();
await p.mouse.click(obox.x + obox.width - 8, obox.y + obox.height / 2); await p.waitForTimeout(400);
R.D2_clic_droite_focus = await p.evaluate(() => document.activeElement?.getAttribute('data-omnibox') !== null);
await shot('g_d1d2_recherche');
await p.keyboard.press('Escape');

// ── B2 : icônes équipements (activer la couche)
await p.getByText('Équipements', { exact: true }).first().click().catch(() => {});
await p.waitForTimeout(1200); await shot('g_b2_equipements');

// ── F1 : plus de « v2 » — ouvrir « + Filtre » + regarder les chips + la liste
await p.getByText('+ Filtre').first().click().catch(() => {}); await p.waitForTimeout(600);
await shot('g_f1_filtre_sans_v2');
const filterTxt = await p.locator('body').innerText();
R.F1_aucun_v2_verdict = !/Brûlante v2|Chaude v2|brûlantes v2|chaudes v2/i.test(filterTxt);
await p.keyboard.press('Escape'); await p.waitForTimeout(300);

// ── E1/E2 : Sources deux régimes, aucun « — » nu
await p.getByText('Sources', { exact: true }).first().click(); await p.waitForTimeout(1800);
const srcTxt = await p.locator('body').innerText();
R.E1_verifie_present = /vérifié il y a|vérifié aujourd|vérifié hier/i.test(srcTxt);
R.E1_cadence_present = /Cadence producteur/i.test(srcTxt);
R.E1_aucun_tiret_nu = !/Dernier contrôle : —/i.test(srcTxt);
await p.screenshot({ path: `${OUT}/g_e1_sources.png`, fullPage: true });

// ── C1 : bouton Projet multi + grisé ; ── F2 : plus de « + Chercher plus »
try {
  await p.goto(`${BASE}#f=1&v=1`, { waitUntil: 'networkidle' }); await p.waitForTimeout(3500);
  await p.locator('[data-results-scroll] > button').first().waitFor({ timeout: 12000 });
  await p.locator('[data-results-scroll] > button').first().evaluate(el => el.click()); await p.waitForTimeout(2500);
  const projBtn = p.getByRole('button', { name: /^Projet$/ }).first();
  if (await projBtn.count()) { await projBtn.click(); await p.waitForTimeout(900); await shot('g_c1_projet_menu'); }
  const menuTxt = await p.locator('body').innerText();
  R.C1_menu_rattacher = /RATTACHER À UN PROJET|dedans/i.test(menuTxt);
  await p.keyboard.press('Escape');
} catch (e) { R.C1_menu_rattacher = `ERR ${String(e).slice(0,50)}`; }
try {
  await p.getByText('Projets', { exact: true }).first().click(); await p.waitForTimeout(1800);
  await shot('g_f2_projets');
  const projTxt = await p.locator('body').innerText();
  R.F2_chercher_plus_absent = !/Chercher plus/i.test(projTxt);
} catch (e) { R.F2_chercher_plus_absent = `ERR ${String(e).slice(0,50)}`; }

console.log(JSON.stringify(R, null, 1));
await b.close();
