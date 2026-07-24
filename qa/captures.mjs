// =============================================================================
// LA BUSE — HARNAIS DE CAPTURES Playwright v1 (pré-vol M7 · P5)
// -----------------------------------------------------------------------------
// Le finding des reliquats front, en avance : chaque parcours critique de l'UI
// est photographié automatiquement → les mandats UI deviennent auto-documentants
// (avant/après = deux runs du harnais). ADDITIF PUR : aucun code produit touché.
//
// Usage :  BASE=http://127.0.0.1:8010/socle/ node qa/captures.mjs [--out qa/captures/out]
//          (l'app doit être servie ; les PNG sont écrits horodatés, JAMAIS commités)
// Parcours couverts (v1) :
//   01 dashboard + recherche (omnibox)         04 scoreur d'adresse (panneau O2)
//   02 fiche — nav 7 onglets (Synthèse)        05 fiche écartée — onglet « Pourquoi pas ? »
//   03 fiche — onglet Faisabilité               06 fiche — boutons export (Banquier)
//   (+ 07 parcours de tri si un projet existe — sinon capture de la vue Projets, honnête)
// =============================================================================
// Playwright résolu depuis frontend/node_modules (devDependency du repo — pas de chemin machine)
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:8010/socle/').replace(/\/?$/, '/');
const outIdx = process.argv.indexOf('--out');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = (outIdx > -1 ? process.argv[outIdx + 1] : new URL('./captures/out', import.meta.url).pathname) + '/' + STAMP;
mkdirSync(OUT, { recursive: true });

const results = [];
async function shot(page, name, note) {
  await page.waitForTimeout(600);                       // laisse la peinture se poser
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  results.push({ name, note, ok: true });
  console.log(`  📸 ${name} — ${note}`);
}
function miss(name, note, err) {
  results.push({ name, note, ok: false, err: String(err).slice(0, 120) });
  console.log(`  ⚠ ${name} — ${note} : ${String(err).slice(0, 120)}`);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(15000);

// ── 01 · dashboard + recherche ───────────────────────────────────────────────
const communesLoaded = page.waitForResponse((r) => r.url().includes('/communes'), { timeout: 30000 }).catch(() => null);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-omnibox]');
await shot(page, '01-dashboard', 'dashboard chargé, omnibox visible');
try {
  await communesLoaded;                          // la bascule commune exige la liste chargée
  await page.fill('[data-omnibox]', 'Saint-Paul');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(1500);
  await shot(page, '01b-recherche-commune', 'recherche commune (bascule périmètre)');
} catch (e) { miss('01b-recherche-commune', 'recherche', e); }

// ── 02-03 · fiche : nav 7 onglets + Faisabilité ─────────────────────────────
// l'analyse est OPT-IN → cliquer ; puis fiche par IDU d'une BRÛLANTE (verdict garanti, découverte
// via l'API réseau — indépendant du cache communes du front, fragile en E2E froid)
try {
  const optin = await page.$('[data-verdict-on]');
  if (optin) { await optin.click(); }
  const api = BASE.replace(/\/socle\/$/, '');
  const r = await page.request.get(`${api}/parcels?limit=1&tiers=brulante`);
  const iduB = (await r.json())[0]?.idu;
  await page.fill('[data-omnibox]', iduB);
  await page.keyboard.press('Enter');
  await page.waitForSelector('[data-fiche-adresse]', { timeout: 25000 });
  await shot(page, '02-fiche-synthese', `fiche ${iduB} — nav d'onglets (7 attendus, sans Solaire)`);
  const onglets = await page.$$eval('aside .overflow-x-auto button', (b) => b.map((x) => x.textContent));
  console.log('  onglets vus :', JSON.stringify(onglets));
  await page.click('text=Faisabilité');
  await shot(page, '03-fiche-faisabilite', 'onglet Faisabilité (a pris la place de Solaire)');
  await shot(page, '06-fiche-exports', 'boutons PDF · Dossier · Banquier visibles en bas de fiche');
} catch (e) { miss('02-fiche', 'fiche via IDU brûlante', e); }

// ── 04 · scoreur d'adresse (O2) — M12-D4 : déplacé dans le tiroir Outils ─────
try {
  await page.click('button[title="Outils"]');
  await page.click('[data-outil="scoreur-adresse"]');
  await page.waitForSelector('[data-scoreur-adresse]');
  await shot(page, '04-scoreur-adresse', 'module « Scorer une adresse » (autocomplétion + prix manuel)');
  await page.click('[data-module-retour]');
} catch (e) { miss('04-scoreur-adresse', 'module scoreur', e); }

// ── 05 · fiche écartée : onglet « Pourquoi pas ? » (O3) ─────────────────────
// fiche par IDU d'une écartée (même voie robuste que 02)
try {
  const api5 = BASE.replace(/\/socle\/$/, '');
  const r5 = await page.request.get(`${api5}/parcels?limit=1&tiers=ecartee`);
  const iduE = (await r5.json())[0]?.idu;
  await page.fill('[data-omnibox]', iduE);
  await page.keyboard.press('Enter');
  await page.waitForSelector('text=Pourquoi pas ?', { timeout: 25000 });
  await page.click('text=Pourquoi pas ?');
  await page.waitForSelector('[data-pourquoi-pas]');
  await shot(page, '05-pourquoi-pas', 'fiche écartée — motifs RÉDHIBITOIRE/VIGILANCE hiérarchisés');
} catch (e) { miss('05-pourquoi-pas', 'fiche écartée via chip Écartées', e); }

// ── 07 · parcours de tri (si un projet existe — sinon vue Projets, honnête) ──
try {
  await page.goto(BASE + '#projets', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  const tinder = await page.$('[data-decision-card]');
  if (tinder) {
    await shot(page, '07-tri-tinder', 'carte de décision — les 3 boutons (Écarter · À analyser · Retenir)');
  } else {
    await shot(page, '07-projets', 'vue Projets (pas de parcours actif — capture honnête)');
  }
} catch (e) { miss('07-tri', 'parcours de tri', e); }

await browser.close();
const ok = results.filter((r) => r.ok).length;
console.log(`\n${ok}/${results.length} captures → ${OUT}`);
process.exit(ok >= 5 ? 0 : 1);   // v1 : au moins 5 parcours photographiés
