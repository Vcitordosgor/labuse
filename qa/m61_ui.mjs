// LA BUSE — M6.1 items 3/4/5 (UI hors carte) :
//  3. panneau outil : fil d'Ariane « ← Outils › <nom> », retour direct au menu, Échap ferme
//  4. page Sources : badges de fraîcheur honnêtes (cadence producteur), prochaine MAJ,
//     « jamais vérifiée » tant que source_checks est vide
//  5. bloc P v2 en fiche : fin du silent-fail — erreur visible + réessayer ; 404 = « non scorée »
//   node qa/m61_ui.mjs               (app d'audit :8010 — JAMAIS :8000)
const pw = await import('../frontend/node_modules/playwright/index.mjs')
  .catch(() => import('/opt/node22/lib/node_modules/playwright/index.mjs'));
const { chromium } = pw;

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/';
const SHOTS = process.env.SHOTS || 'reports/m61-couches/captures-ui';
const NONSCORED_IDU = process.env.NONSCORED_IDU || '';  // parcelle SANS score v2 (aucune à ce jour :
                                                        // périmètre 100 % scoré → 5b simule le 404)
// IDU de test pris sur le RUN COURANT via l'API (jamais en dur : survit aux recomputes).
// Trois IDU distincts (5a nominal / 5b 404 / 5c panne) : le cache react-query (staleTime
// 5 min) ne refait AUCUN appel pour un idu déjà chargé — un même idu rendrait 5b/5c inertes.
const origin = new URL(BASE).origin;
const top = await (await fetch(`${origin}/v2/liste?limit=3`)).json();
const [IDU_A, IDU_B, IDU_C] = top.items.map((i) => i.parcelle_id);
const SCORED_IDU = process.env.SCORED_IDU || IDU_A;
console.log(`IDU run courant (${top.run_id}) : nominal ${SCORED_IDU} · 404 ${IDU_B} · panne ${IDU_C}`);
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
await page.waitForTimeout(1000);

/* ── ITEM 3 — navigation outils ── */
await page.evaluate(() => window.__labuse.setModule('division'));
await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 });
const crumb = (await page.locator('[data-module-breadcrumb]').textContent()) ?? '';
ok('3.fil-ariane', /OUTILS/.test(crumb) && /›/.test(crumb), `« ${crumb.trim()} »`);
await page.screenshot({ path: `${SHOTS}/item3-panneau-fil-ariane.png` });

await page.locator('[data-module-retour]').click();                    // ← Outils
await page.waitForTimeout(400);
const menuOuvert = await page.locator('[data-outil-group]').count();
const panneauFerme = await page.locator('[data-module-breadcrumb]').count();
ok('3.retour-menu', menuOuvert > 0 && panneauFerme === 0, `${menuOuvert} groupes visibles, panneau fermé`);
await page.screenshot({ path: `${SHOTS}/item3-retour-menu-outils.png` });

// depuis le menu, ouvrir un AUTRE outil sans repasser par le rail (le vrai gain)
await page.evaluate(() => window.__labuse.setModule('velocite'));
await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 });
await page.keyboard.press('Escape');                                    // Échap ferme le panneau
await page.waitForTimeout(400);
ok('3.echap-ferme', (await page.locator('[data-module-breadcrumb]').count()) === 0);

// Échap ne doit PAS fermer le module quand une fiche est ouverte (la fiche a priorité)
if (SCORED_IDU) {
  await page.evaluate(() => window.__labuse.setModule('division'));
  await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 });
  await page.evaluate((idu) => window.__labuse.select(idu), SCORED_IDU);
  await page.waitForSelector('[data-score-v2]', { timeout: 20000 }).catch(() => {});
  await page.keyboard.press('Escape');                                  // ferme la FICHE
  await page.waitForTimeout(400);
  const moduleEncore = (await page.locator('[data-module-breadcrumb]').count()) === 1;
  ok('3.echap-priorite-fiche', moduleEncore, 'la fiche se ferme, le module reste');
  await page.keyboard.press('Escape');                                  // puis le module
  await page.waitForTimeout(400);
  ok('3.echap-puis-module', (await page.locator('[data-module-breadcrumb]').count()) === 0);
}

/* ── ITEM 4 — page Sources : badges de fraîcheur ── */
await page.evaluate(() => window.__labuse.setView('sources'));
await page.waitForSelector('[data-source-row]', { timeout: 15000 });
const nRows = await page.locator('[data-source-row]').count();
const nBadges = await page.locator('[data-source-badge]').count();
ok('4.badge-sur-chaque-ligne', nRows > 0 && nBadges === nRows, `${nBadges}/${nRows}`);
const nVert = await page.locator('[data-source-badge="a_jour"]').count();
const nOrange = await page.locator('[data-source-badge="maj_attendue"]').count();
const nGris = await page.locator('[data-source-badge="a_verifier"]').count();
ok('4.trois-etats-presents', nVert > 0 && nOrange > 0 && nGris > 0, `vert ${nVert} · orange ${nOrange} · gris ${nGris}`);
const nProchaine = await page.locator('[data-source-prochaine]').count();
const nTirets = await page.locator('[data-source-prochaine]', { hasText: '—' }).count();
ok('4.prochaine-maj-honnete', nProchaine === nRows && nTirets === nGris,
  `${nProchaine} lignes, ${nTirets} « — » = ${nGris} cadences inconnues`);
// source_checks est VIDE → aucune ligne « vérifié le », toutes « jamais vérifiée » (discret)
const nJamais = await page.locator('[data-source-verifiee="jamais"]').count();
ok('4.jamais-verifiee', nJamais === nRows, `${nJamais}/${nRows} (source_checks vide)`);
ok('4.legende', (await page.locator('[data-sources-legende]').count()) === 1);
// contrôles ancrés sur les cadences documentées
const rowDPE = page.locator('[data-source-row]', { hasText: 'DPE ADEME' });
ok('4.dpe-hebdo-a-jour', (await rowDPE.locator('[data-source-badge="a_jour"]').count()) === 1);
const rowBodacc = page.locator('[data-source-row]', { hasText: 'BODACC' });
ok('4.bodacc-retard-orange', (await rowBodacc.locator('[data-source-badge="maj_attendue"]').count()) === 1);
await page.screenshot({ path: `${SHOTS}/item4-sources-badges.png` });
await rowDPE.first().scrollIntoViewIfNeeded();
await page.screenshot({ path: `${SHOTS}/item4-sources-badges-detail.png` });

/* ── ITEM 5 — bloc P v2 : fin du silent-fail ── */
await page.evaluate(() => window.__labuse.setView('cartes'));
// routeur unique : 'normal' laisse passer, '404' répond comme l'API pour une parcelle
// absente du run, 'panne' coupe le réseau (le front ne voit AUCUNE différence avec le réel)
let modeV2 = 'normal';
await page.route('**/v2/score/**', (route) =>
  modeV2 === '404' ? route.fulfill({ status: 404, contentType: 'application/json',
    body: JSON.stringify({ detail: 'parcelle absente du run (simulation QA)' }) })
  : modeV2 === 'panne' ? route.abort()
  : route.continue());

// 5a. cas nominal inchangé
await page.evaluate((idu) => window.__labuse.select(idu), SCORED_IDU);
await page.waitForSelector('[data-score-v2]', { timeout: 20000 });
const attrNominal = await page.locator('[data-score-v2]').getAttribute('data-score-v2');
ok('5.nominal-inchange', attrNominal === '' || attrNominal === 'true', 'bloc ×N/percentile affiché');
await page.locator('[data-score-v2]').scrollIntoViewIfNeeded();
await page.screenshot({ path: `${SHOTS}/item5-bloc-nominal.png` });
await page.evaluate(() => window.__labuse.select(null));
await page.waitForTimeout(300);

// 5b. parcelle sans score v2 → « non scorée », pas de disparition muette.
//     404 réel si NONSCORED_IDU est fourni ; sinon 404 simulé au niveau réseau sur IDU_B
//     (périmètre 100 % scoré aujourd'hui : aucun idu avec fiche ne renvoie un vrai 404).
const idu404 = NONSCORED_IDU || IDU_B;
if (!NONSCORED_IDU) modeV2 = '404';
await page.evaluate((idu) => window.__labuse.select(idu), idu404);
await page.waitForSelector('[data-score-v2="non-scoree"]', { timeout: 20000 });
const msg404 = (await page.locator('[data-score-v2="non-scoree"]').textContent()) ?? '';
ok('5.404-non-scoree', /copropriété ou hors périmètre/i.test(msg404),
  NONSCORED_IDU ? '404 réel' : '404 simulé (route réseau — même chemin UI)');
await page.locator('[data-score-v2="non-scoree"]').scrollIntoViewIfNeeded();
await page.screenshot({ path: `${SHOTS}/item5-non-scoree.png` });
modeV2 = 'normal';
await page.evaluate(() => window.__labuse.select(null));
await page.waitForTimeout(300);

// 5c. panne (réseau/5xx) → état visible + « Réessayer » qui REMET le bloc
modeV2 = 'panne';
await page.evaluate((idu) => window.__labuse.select(idu), IDU_C);
await page.waitForSelector('[data-score-v2="erreur"]', { timeout: 20000 });
const msg = (await page.locator('[data-score-v2="erreur"]').textContent()) ?? '';
ok('5.erreur-visible', /momentanément indisponible/i.test(msg));
ok('5.erreur-meme-gabarit', /Probabilité de mutation/i.test(msg), 'même en-tête que le bloc nominal');
await page.locator('[data-score-v2="erreur"]').scrollIntoViewIfNeeded();
await page.screenshot({ path: `${SHOTS}/item5-erreur-reessayer.png` });
modeV2 = 'normal';                                                    // le réseau revient
await page.locator('[data-score-v2="erreur"] button').click();        // Réessayer
await page.waitForSelector('[data-score-v2=""], [data-score-v2="true"]', { timeout: 20000 });
ok('5.reessayer-recupere', true, 'le bloc nominal remplace l\'erreur');
await page.screenshot({ path: `${SHOTS}/item5-apres-reessayer.png` });

await browser.close();
console.log(fails ? `\n${fails} échec(s)` : '\nOK — M6.1 items 3/4/5 vérifiés');
process.exit(fails ? 1 : 0);
