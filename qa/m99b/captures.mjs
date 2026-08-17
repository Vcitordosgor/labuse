// M99-B — captures de recette du sélecteur de zonage « choix pur » (3 vues demandées par Vic).
// Usage : BASE=http://localhost:5173/ node qa/m99b/captures.mjs
// (vite dev servi + API :8000 ; PNG écrits sous qa/m99b/captures/<stamp>/, JAMAIS commités.)
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });   // Chrome système (motif maison, cf. qa/entree/verif.mjs)
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);

async function shot(name, note) {
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`📸 ${name} — ${note}`);
}

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-filtres-toggle]');
const toggle = await page.$('[data-filtres-toggle][aria-expanded="false"]');
if (toggle) await toggle.click();
await page.waitForSelector('[data-zones-fam="U"]');
await page.$eval('[data-zones-fam="U"]', (el) => el.scrollIntoView({ block: 'center' }));

// 1 · famille U repliée (les 4 familles visibles, aucun menu ouvert, aucun <input>)
await shot('01-famille-U-repliee', 'sélecteur replié — familles U/A/N/AU, comptes île');

// 2 · menu U ouvert, portée île
await page.click('[data-zones-fam="U"]');
await page.waitForSelector('[data-zone-toutes="U"]');
const zonesIle = await page.$$eval('[data-zone]', (els) => els.length);
console.log(`   menu U île : ${zonesIle} zones listées (attendu 131)`);
await shot('02-menu-U-ile', `menu U ouvert, portée île — « Toutes les zones U » en tête, ${zonesIle} zones`);

// 3 · Le Tampon filtré → menu U réduit aux zones du Tampon
const majPortee = page.waitForResponse((r) => r.url().includes('/zonage/zones') && r.url().includes('Tampon'));
await page.click('button:has-text("97430")');       // chip commune Le Tampon
await majPortee;
await page.waitForTimeout(500);
const zonesTampon = await page.$$eval('[data-zone]', (els) => els.map((e) => e.dataset.zone));
console.log(`   menu U Le Tampon : ${zonesTampon.length} zones — ${zonesTampon.join(', ')} (attendu 9 : UC UB UA UAV UD UE UCM UCTOM UCTO)`);
await shot('03-menu-U-le-tampon', `menu U, Le Tampon filtré — ${zonesTampon.length} zones de la commune seulement`);

// aucun <input> dans le SÉLECTEUR : on remonte au conteneur direct du menu (le parent commun
// de « Toutes les zones » et des entrées de zone), pas à un ancêtre du panneau entier.
const nInputs = await page.$eval('[data-zone-toutes="U"]', (el) =>
  el.parentElement.querySelectorAll('input').length
  + el.closest('.rounded-lg').querySelectorAll('input').length);
console.log(`   <input> dans le bloc famille U (menu ouvert) : ${nInputs} (attendu 0)`);

await browser.close();
console.log(`\nCaptures : ${OUT}`);
