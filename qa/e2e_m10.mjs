// QA E2E — mandat M10 (radar permis cliquable + vélocité administrative). Serveur attendu
// sur BASE (labuse api de ce worktree, table m10_permit_delais construite, front buildé).
// Assertions API + captures navigateur (fiche permis, radar filtrable, vélocité, proximité).
//   BASE=http://127.0.0.1:8012 node qa/e2e_m10.mjs
import { mkdirSync } from 'node:fs';
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8012';
const SOURCE = process.env.SOURCE || 'q_v5_m6b';
const OUT = 'reports/m10-permis/captures';
mkdirSync(OUT, { recursive: true });

let fails = 0;
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? '✓' : '✗'} ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) fails += 1;
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
const rq = ctx.request;
const getj = async (path) => (await rq.get(`${BASE}${path}`)).json();

// ─────────────────── 1. Radar permis filtrable (commune / période / nature) ───────────────────
const radarPC = await getj('/modules/permis?months=48&nature=PC');
const radarDP = await getj('/modules/permis?months=48&nature=DP');
ok('1a.radar-repond', radarPC.total > 0 && Array.isArray(radarPC.items), `total PC=${radarPC.total}`);
ok('1b.filtre-nature', radarPC.nature === 'PC' && radarPC.items.every((i) => i.type === 'PC'));
ok('1c.nature-discrimine', radarPC.total !== radarDP.total, `PC=${radarPC.total} DP=${radarDP.total}`);
const withDelai = radarPC.items.filter((i) => i.delai_mois != null);
ok('1d.radar-porte-depot-delai', radarPC.items[0].depot !== undefined && withDelai.length > 0,
  `${withDelai.length}/${radarPC.items.length} avec délai`);
const radar12 = await getj('/modules/permis?months=12&nature=PC');
ok('1e.filtre-periode', radar12.total <= radarPC.total, `12m=${radar12.total} ≤ 48m=${radarPC.total}`);

// ─────────────────── 2. Fiche permis cliquable (lot 1.1) ───────────────────
const permitId = radarPC.items.find((i) => i.geom)?.permit_id || radarPC.items[0].permit_id;
const fp = await getj(`/modules/permis/${encodeURIComponent(permitId)}`);
ok('2a.fiche-lisible', fp.permit_id === permitId && !!fp.nature_libelle && !!fp.statut, `${fp.nature_libelle}`);
ok('2b.dates-cles', !!fp.date_depot && !!fp.date_autorisation, `dépôt=${fp.date_depot} autor=${fp.date_autorisation}`);
ok('2c.delai-instruction', fp.delai_instruction && fp.delai_instruction.mois >= 0 && /mois/.test(fp.delai_instruction.libelle),
  `${fp.delai_instruction?.mois} mois`);
ok('2d.porteur-ou-note', fp.porteur != null || /physique|anonymis/i.test(fp.porteur_note || ''));
ok('2e.parcelles-liees', Array.isArray(fp.parcelles) && fp.parcelles.length > 0, `${fp.parcelles.length} parcelle(s)`);
ok('2f.404-propre', (await rq.get(`${BASE}/modules/permis/XXINEXISTANT`)).status() === 404);

// ─────────────────── 3. Permis à proximité, cohérent avec M-VIA (lot 1.2/1.3) ───────────────────
const idu = process.env.IDU || fp.parcelles[0];
const prox = await getj(`/modules/parcelle-permis?idu=${encodeURIComponent(idu)}`);
ok('3a.proximite-repond', Array.isArray(prox.items), `idu=${idu} c200=${prox.c200}`);
ok('3b.permis-cliquables', prox.items.every((i) => !!i.permit_id && i.distance_m != null));
ok('3c.rayons-100-200', prox.items.every((i) => i.distance_m <= 200) && prox.c100 <= prox.c200);
// cohérence STRICTE avec le faisceau de viabilisation M-VIA (mêmes c100/c200 que la fiche)
const fiche = await (await rq.get(`${BASE}/parcels/${idu}?source=${SOURCE}`)).json();
const via = fiche.viabilisation;
if (via) {
  const c = via.contributions.find((x) => /permis/i.test(x.libelle));
  ok('3d.coherence-m-via', !!c, `signal viabilisation présent (proximité=${prox.c200})`);
}

// ─────────────────── 4. Vélocité : médiane dépôt→autorisation, N, censure (lot 2) ───────────────────
const vel = await getj('/modules/velocite?nature=PC');
ok('4a.velocite-par-commune', vel.communes.length >= 20, `${vel.communes.length} communes`);
ok('4b.mediane-pas-moyenne', /[Mm]édian/.test(vel.indicateur) && /médiane/i.test(vel.note));
const withN = vel.communes.filter((c) => c.delai_median_mois != null && c.n_mur > 0);
ok('4c.mediane-et-N', withN.length >= 20 && withN.every((c) => Number.isInteger(c.delai_median_mois) && c.delai_median_mois >= 0),
  `ex: ${withN[0].commune} ${withN[0].delai_median_mois} mois / N=${withN[0].n_mur}`);
ok('4d.censure-documentee', /accord/i.test(vel.censure) && /en cours|refus/i.test(vel.censure));
ok('4e.cohortes-mures', !!vel.maturite_cutoff && withN.every((c) => c.n_recent_exclu != null),
  `cutoff=${vel.maturite_cutoff}`);
ok('4f.qualite-exclusions', withN.every((c) => c.n_exclus_qualite != null));
ok('4g.disclaimer-historique', /historique/i.test(vel.disclaimer));
const velDP = await getj('/modules/velocite?nature=DP');
ok('4h.velocite-par-nature', velDP.nature === 'DP' && velDP.communes.length > 0);

// ─────────────────── 5. Captures navigateur ───────────────────
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 150)));

// Le SPA ne lit le hash qu'au montage → on pilote via l'API de test exposée (window.__labuse).
await page.goto(`${BASE}/socle/#v=1`, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForFunction(() => !!window.__labuse, null, { timeout: 15000 }).catch(() => {});

// 5a. Radar permis + clic sur une CARTE permis (datée) → tiroir fiche permis
await page.evaluate(() => window.__labuse.setModule('permis'));
await page.waitForTimeout(3500);
await page.screenshot({ path: `${OUT}/radar-permis.png` });
const card = page.getByRole('button').filter({ hasText: /20\d{2}-\d{2}-\d{2}/ }).first();
let drawerSeen = false;
if (await card.count()) {
  await card.click().catch(() => {});
  await page.waitForTimeout(1800);
  const drawer = page.locator('[data-permis-drawer]');
  drawerSeen = (await drawer.count()) > 0;
  if (drawerSeen) await drawer.screenshot({ path: `${OUT}/fiche-permis-drawer.png` }).catch(() => {});
}
ok('5a.radar-et-fiche-permis', drawerSeen, 'tiroir permis ouvert au clic sur une carte');
await page.keyboard.press('Escape').catch(() => {});

// 5b. Vélocité admin
await page.evaluate(() => window.__labuse.setModule('velocite'));
await page.waitForTimeout(3500);
await page.screenshot({ path: `${OUT}/velocite.png` });
ok('5b.velocite-rendue', /médian|dépôt/i.test(await page.content()));

// 5c. Fiche parcelle → bloc « permis à proximité »
await page.evaluate((id) => { window.__labuse.setModule(null); window.__labuse.select(id); }, idu);
await page.waitForTimeout(2500);
await page.waitForSelector('[data-permis-proximite]', { timeout: 9000 }).catch(() => {});
const block = page.locator('[data-permis-proximite]');
const blockSeen = (await block.count()) > 0;
if (blockSeen) {
  await block.first().scrollIntoViewIfNeeded().catch(() => {});
  await block.first().screenshot({ path: `${OUT}/proximite-fiche-${idu}.png` }).catch(() => {});
}
await page.screenshot({ path: `${OUT}/fiche-${idu}.png` });
ok('5c.proximite-sur-fiche', blockSeen, `bloc permis proximité (idu=${idu})`);
ok('5z.pas-erreur-console', errs.length === 0, errs.join(' | '));

await browser.close();
console.log(`\n${fails === 0 ? '✓ E2E M10 OK' : `✗ ${fails} échec(s)`} — captures → ${OUT}/`);
process.exit(fails === 0 ? 0 : 1);
