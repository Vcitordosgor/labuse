// UX V1 — suite E2E des 15 items (mandat 12/07/2026). Usage : BASE=http://127.0.0.1:8020/socle/ node qa/ux_v1/e2e.mjs
// Chaque assert est nommé ; sortie non-zéro si au moins un échec. Complément : tests/test_ux_v1.py
// (refus stub des verbes hors périmètre + rattachement ingestion_runs, côté serveur).
const pw = await import('../../frontend/node_modules/playwright/index.mjs');
const { chromium } = pw;

const BASE = process.env.BASE || 'http://127.0.0.1:8020/socle/';
const API = BASE.replace(/\/socle\/?$/, '');
let failed = 0;
const ok = (nom, cond, detail = '') => {
  console.log(`${cond ? '✓' : '✗'} ${nom}${cond ? '' : ` — ${detail}`}`);
  if (!cond) failed++;
};

const browser = await chromium.launch();
async function page(viewport, hash = '') {
  const ctx = await browser.newContext({ viewport });
  const p = await ctx.newPage();
  await p.goto(BASE + hash, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await p.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
  await p.waitForTimeout(1200);
  return { ctx, p };
}

// ── Item 1 : mobile 375 — carte plein écran au boot, tiroir Couches ──
{
  const { ctx, p } = await page({ width: 375, height: 812 });
  await p.waitForTimeout(1500);
  const m = await p.evaluate(() => {
    const canvas = document.querySelector('.maplibregl-map');
    return { mapW: canvas?.clientWidth ?? 0, rail: document.querySelector('nav')?.clientWidth ?? 0, vw: innerWidth };
  });
  ok('1 · carte plein écran au boot 375', m.mapW >= m.vw - m.rail - 2, JSON.stringify(m));
  ok('1 · bouton Couches flottant présent', await p.locator('[data-couches-mobile]').count() === 1);
  await p.locator('[data-couches-mobile]').click();
  await p.waitForTimeout(500);
  ok('1 · tiroir : couches + légende VERDICT', await p.locator('[data-couches-drawer]').count() === 1
    && /VERDICT/.test(await p.locator('[data-couches-drawer]').textContent()));
  await ctx.close();
}

// ── Items 6 + 5 : builder mobile en onglets · garde des ranges ──
{
  const { ctx, p } = await page({ width: 375, height: 812 });
  await p.evaluate(() => window.__labuse.setView('segments'));
  await p.waitForTimeout(1500);
  await p.locator('[data-seg-preset-open]').first().click();
  await p.waitForTimeout(1500);
  ok('6 · onglets Filtres/Résultats sous 640 px', await p.locator('[data-seg-onglets]').isVisible());
  await p.locator('[data-seg-onglet="filtres"]').click();
  await p.waitForTimeout(400);
  const min = p.locator('[data-seg-filtre] input[placeholder="min"]').first();
  ok('5 · input range porte min=0', await min.getAttribute('min') === '0');
  await min.fill('-50');
  await p.waitForTimeout(600);
  ok('5 · garde ambre sur valeur négative', await p.locator('[data-seg-garde]').count() >= 1);
  await ctx.close();
}

// ── Item 11 : plus de warning MapLibre au boot 375 ──
{
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const p = await ctx.newPage();
  const warns = [];
  p.on('console', (msg) => { if (/cannot fit/i.test(msg.text())) warns.push(1); });
  await p.goto(BASE, { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
  await p.waitForTimeout(2500);
  ok('11 · zéro « Map cannot fit within canvas » au boot 375', warns.length === 0, `${warns.length} warnings`);
  await ctx.close();
}

// ── Item 2 : mode dégradé VISIBLE dans la restitution (réponse stub simulée) ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/ia/search', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ stub: true,
      filters: { statuts: [], scoreMin: null, surfaceMin: null, surfaceMax: null, sdpMin: null, evenement: false, vueMer: false, flags: [], commune: 'Le Tampon' },
      explanation: 'Filtres appliqués : commune Le Tampon.' }),
  }));
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(600);
  const input = p.locator('[data-porte-recherche] input');
  await input.fill('maisons avec un DPE F ou G au Tampon');
  await input.press('Enter');
  await p.locator('[data-ia-restitution]').waitFor({ timeout: 30000 });
  ok('2 · badge « mode mots-clés » dans la restitution', await p.locator('[data-ia-badge-stub]').count() === 1);
  const expl = await p.locator('[data-ia-explication]').textContent();
  ok('2 · explication serveur affichée', /Filtres appliqués : commune Le Tampon/.test(expl || ''));
  ok('2 · le non-traduit est annoncé', /n'ont pas été traduits/.test(expl || ''));
  await ctx.close();
}

// ── Item 10 : verbes hors périmètre → out_of_scope (API réelle, clé neutralisée = stub local)
//    NB : nécessite un serveur SANS clé Anthropic (lancé par le runner sur :8021) — sinon skip.
{
  const stubApi = process.env.STUB_API;   // ex. http://127.0.0.1:8021
  if (stubApi) {
    for (const q of ['supprime toutes les parcelles de la base',
                     'modifie le score de la parcelle 97411000BH0670',
                     'écris une lettre au propriétaire']) {
      const r = await fetch(`${stubApi}/ia/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: q }),
      }).then((x) => x.json());
      ok(`10 · refus stub « ${q.slice(0, 32)}… »`, !!r.out_of_scope && !r.filters, JSON.stringify(r).slice(0, 120));
    }
    const legit = await fetch(`${stubApi}/ia/search`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'les chaudes de Saint-Pierre' }),
    }).then((x) => x.json());
    ok('10 · recherche légitime toujours traduite (stub)', !!legit.filters && legit.filters.commune === 'Saint-Pierre');
  } else {
    console.log('· 10 : STUB_API non fourni — couvert par tests/test_ux_v1.py (pytest)');
  }
}

// ── Ajout C : 0 résultat → relâchement proposé et relançable ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/ia/search', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ stub: false,
      filters: { statuts: ['chaude'], scoreMin: null, surfaceMin: 100000, surfaceMax: null, sdpMin: null, evenement: false, vueMer: false, flags: [], commune: 'Cilaos' },
      explanation: 'Filtres proposés par l\'IA (validés par schéma).' }),
  }));
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(600);
  const input = p.locator('[data-porte-recherche] input');
  await input.fill('les chaudes de Cilaos de plus de 100 000 m²');
  await input.press('Enter');
  await p.locator('[data-ia-zero]').waitFor({ timeout: 30000 });
  ok('C · 0 résultat → proposition de relâchement', /Réessayer sans le critère/.test(await p.locator('[data-ia-zero]').textContent() || ''));
  await p.locator('[data-ia-relance]').click();
  await p.waitForTimeout(4000);
  const count = await p.locator('[data-ia-count]').textContent();
  ok('C · relance sans le critère → résultats', (count || '0') !== '0');
  await ctx.close();
}

// ── Ajout A : page Sources & fraîcheur ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('sources'));
  await p.waitForTimeout(1800);
  ok('A · phrase de positionnement', /traçable jusqu'à sa source publique/.test(
    await p.locator('[data-sources-positionnement]').textContent() || ''));
  ok('A · 4 précisions mesurées', await p.locator('[data-sources-precisions] > div').count() === 4);
  ok('A · licence sur chaque ligne', await p.locator('[data-source-licence]').count() ===
    await p.locator('[data-source-row]').count());
  // la date du cadastre vient d'ingestion_runs (servie par l'API, jamais en dur)
  const src = await fetch(`${API}/sources`).then((r) => r.json());
  const cad = src.find((s) => s.name.startsWith('Cadastre Etalab'));
  ok('A · derniere_ingestion servie depuis ingestion_runs', !!cad?.derniere_ingestion && cad.ingestion_runs > 0,
    JSON.stringify({ d: cad?.derniere_ingestion, n: cad?.ingestion_runs }));
  await ctx.close();
}

// ── Item 3 : erreur fiche — wording client, zéro jargon ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/parcels/97411000*', (route) => route.abort('connectionrefused'));
  await p.evaluate(() => window.__labuse.select('97411000BH0670'));
  await p.locator('[data-fiche-erreur]').waitFor({ timeout: 25000 });
  const txt = await p.locator('[data-fiche-erreur]').textContent();
  ok('3 · wording client (« Connexion au serveur impossible »)', /Connexion au serveur impossible/.test(txt || ''));
  ok('3 · jargon développeur absent', !/labuse api|périmé/i.test(txt || ''));
  await ctx.close();
}

// ── Item 4 : liste vide — message explicite + CTA ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 }, '#f=1&st=chaude&smin=100000&c=Cilaos&v=1');
  await p.locator('[data-liste-vide]').waitFor({ timeout: 25000 });
  const txt = await p.locator('[data-liste-vide]').textContent();
  ok('4 · message explicite avec commune', /Aucune parcelle chaude à Cilaos/.test(txt || ''));
  ok('4 · CTA « Élargir à toute l\'île »', await p.locator('[data-vide-ile]').count() === 1);
  await ctx.close();
}

// ── Items 14 + B : galerie — note compteur datée, pictos, bénéfices, compteur réel ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('segments'));
  await p.waitForTimeout(1800);
  ok('14 · note « compteur du JJ/MM à HH:MM »', /compteur du \d{2}\/\d{2} à \d{2}:\d{2}/.test(
    await p.locator('[data-seg-count-date]').first().textContent() || ''));
  ok('B · un picto par preset', await p.locator('[data-seg-picto]').count() >= 5);
  ok('B · 5 phrases de bénéfice', await p.locator('[data-seg-benefice]').count() === 5);
  // le compteur de la phrase piscines = le compteur RÉEL du segment (même carte)
  const carte = p.locator('[data-seg-preset="parc-piscines-entretien"]');
  const phrase = await carte.locator('[data-seg-benefice]').textContent();
  const compteur = (await carte.locator('[data-seg-preset-count]').textContent() || '').trim();
  ok('B · compteur piscines dynamique (= count du segment)',
    (phrase || '').replace(/ | /g, ' ').includes(compteur.replace(/ | /g, ' ')),
    `phrase="${phrase}" compteur="${compteur}"`);
  await ctx.close();
}

// ── Items 9 + 7 : focus clavier visible · tooltips Q/A/V ──
{
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.keyboard.press('Tab');
  const o = await p.evaluate(() => {
    const cs = getComputedStyle(document.activeElement);
    return `${cs.outlineWidth} ${cs.outlineColor}`;
  });
  ok('9 · anneau mint 2 px au premier Tab (rail)', o === '2px rgb(92, 230, 161)', o);
  await p.evaluate(() => window.__labuse.select('97411000BH0670'));
  await p.waitForTimeout(4000);
  const tips = await p.evaluate(() => ({
    q: !![...document.querySelectorAll('[title]')].find((e) => e.title.startsWith('Q — Qualité intrinsèque')),
    a: !![...document.querySelectorAll('[title]')].find((e) => e.title.startsWith('A — Accessibilité du dossier')),
    v: !![...document.querySelectorAll('[title]')].find((e) => e.title.startsWith('V — Vendabilité')),
  }));
  ok('7 · tooltips Q, A et V posés sur la fiche', tips.q && tips.a && tips.v, JSON.stringify(tips));
  await ctx.close();
}

await browser.close();
console.log(failed === 0 ? '\n── E2E UX V1 : tout est vert ──' : `\n── E2E UX V1 : ${failed} échec(s) ──`);
process.exit(failed === 0 ? 0 : 1);
