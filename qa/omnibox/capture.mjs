// Recette PATRON OMNIBOX (M137) — chaque outil à saisie de parcelle a UN SEUL champ acceptant
// une ADRESSE et un IDU. Pour chacun : un IDU marche, une adresse marche. Capture + assertions.
// Usage : BASE=http://localhost:5173/socle/ node qa/omnibox/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const IDU = '97415000DK1044';         // Saint-Paul, en base
const ADRESSE = '12 rue';             // requête adresse → suggestion avec IDU rattaché (source interne)
const OUT = new URL('./captures', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1200 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(900);

const openTool = async (key) => { await page.evaluate((k) => window.__labuse.setModule(k), null); await page.waitForTimeout(150); await page.evaluate((k) => window.__labuse.setModule(k), key); await page.waitForTimeout(500); };
const has = async (sel) => (await page.locator(sel).count()) > 0;
// résolution asynchrone (réseau) : on POLLE la condition jusqu'à 8 s (le 1er compute est à froid).
const poll = async (fn) => { for (let i = 0; i < 40; i++) { if (await fn()) return true; await page.waitForTimeout(200); } return false; };

// saisir un IDU dans le champ omnibox → Entrée (l'IDU coupe la BAN, commit sur Entrée)
async function saisirIdu(field) {
  const f = page.locator(field).first();
  await f.click(); await f.fill(''); await f.fill(IDU); await page.waitForTimeout(300);
  await f.press('Enter'); await page.waitForTimeout(1500);
}
// saisir une ADRESSE → attendre la liste → Entrée (choisit la 1re suggestion, IDU rattaché)
async function saisirAdresse(field) {
  const f = page.locator(field).first();
  await f.click(); await f.fill(''); await f.fill(ADRESSE); await page.waitForTimeout(1300);
  await f.press('Enter'); await page.waitForTimeout(1600);
}

const R = {};
async function tool(name, key, field, resolved, { tab } = {}) {
  const res = { idu: false, adresse: false, champ_unique: false };
  // IDU
  await openTool(key); if (tab) { await tab(); }
  res.champ_unique = (await page.locator(field).count()) === 1;   // UN seul champ de saisie parcelle
  await saisirIdu(field);
  res.idu = await poll(resolved);
  await page.screenshot({ path: `${OUT}/${name}-idu.png` });
  // ADRESSE
  await openTool(key); if (tab) { await tab(); }
  await saisirAdresse(field);
  res.adresse = await poll(resolved);
  await page.screenshot({ path: `${OUT}/${name}-adresse.png` });
  R[name] = res;
  console.log(name, JSON.stringify(res));
}

// 1) Étudier un bien (créneau phare O2)
await tool('etudier', 'scoreur-adresse', '[data-etudier-adresse]',
  async () => has('[data-etudier-resultat]'));

// 2) Courrier — résolution = bouton « Suivant » activé (idu posé)
await tool('courrier', 'courriers', '[data-courrier-idu]',
  async () => (await page.locator('[data-courrier-next]:not([disabled])').count()) > 0);

// 3) Remonter le temps — résolution = passage à l'étape « année » (data-cmp-left)
await tool('temps', 'temps', '[data-temps-idu]',
  async () => has('[data-cmp-left]'));

// 4) Faisabilité (mode « par parcelle » → ParcelPicker) — résolution = le picker disparaît (picked)
await tool('faisabilite', 'programme', '[data-picker-idu]',
  async () => (await page.locator('[data-picker-idu]').count()) === 0,
  { tab: async () => { await page.locator('[data-faisa-mode="parcelle"]').click(); await page.waitForTimeout(400); } });

// 5) Pièges et risques — onglet « Une parcelle » (défaut) → O5. Résolution = pas d'erreur, un résultat servi
await tool('risques', 'risques', '[data-o5-idu]',
  async () => !(await has('text=Servitudes indisponibles')) && (await page.locator('[data-o5-idu]').count()) === 1,
  { tab: async () => { await page.locator('[data-risques-entree="parcelle"]').click(); await page.waitForTimeout(300); } });

writeFileSync(`${OUT}/resultats.json`, JSON.stringify(R, null, 2));
const tous = Object.values(R).every((r) => r.idu && r.adresse && r.champ_unique);
console.log('\nTOUS VERTS (idu+adresse+champ unique):', tous);
await browser.close();
console.log('OUT:', OUT);
