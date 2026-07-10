// LA BUSE — E2E du mandat wave-adresses-courrier-ia (Playwright).
//   L'app doit tourner avec un rate limit haut (les 301 consultations du test de gel
//   dépasseraient 60/min) et un quota fiches par défaut (300) :
//   LABUSE_RATE_LIMIT_RPM=100000 .venv/bin/uvicorn labuse.api.app:app --port 8001
//   BASE=http://127.0.0.1:8001 node qa/e2e_wave_aci.mjs
// Critères du mandat : publipostage non vide (adresses BAN), Dossier parcelle < 30 s,
// libellé préparatoire du pré-dossier, recherche NL Saint-Leu cohérente, 301 fiches → gel.
// PRÉREQUIS du scénario 5 : compteur de fiches du jour vierge pour ce sujet (persisté
// exprès au restart) — purge : psql -c "DELETE FROM usage_compteurs WHERE kind='fiche'".
// chemin playwright : vendorisé du frontend en local, /opt/node22 sur le VPS QA
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8001';
const IDU = process.env.IDU || '97405000AO0461';        // parcelle bâtie de référence
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch();
const ctx = await browser.newContext();
const rq = ctx.request;

// 1 — export publipostage non vide, adresses BAN dans le CSV
{
  const r = await rq.post(`${BASE}/segments/publipostage`, {
    data: { slug: 'pergolas-terrasses' }, timeout: 120000 });
  const rows = +(r.headers()['x-rows'] || 0);
  const body = await r.body();
  ok('1.publipostage-non-vide', r.status() === 200 && rows > 0 && body.length > 10000,
     `HTTP ${r.status()}, ${rows} lignes, ${body.length} octets`);
}

// 2 — Dossier parcelle < 30 s
{
  const t0 = Date.now();
  const r = await rq.get(`${BASE}/dossier/${IDU}.pdf`, { timeout: 45000 });
  const dt = (Date.now() - t0) / 1000;
  const body = await r.body();
  ok('2.dossier-parcelle-30s', r.status() === 200 && dt < 30
     && body.subarray(0, 5).toString() === '%PDF-', `HTTP ${r.status()} en ${dt.toFixed(1)} s`);
}

// 3 — pré-dossier PC : le libellé préparatoire est là
{
  const r = await rq.get(`${BASE}/pre-dossier/${IDU}.zip`, { timeout: 60000 });
  const body = await r.body();
  ok('3.pre-dossier-libelle', r.status() === 200
     && body.toString('latin1').includes('LISEZMOI.txt')
     && body.toString('utf8').includes('Document pr'),   // « Document préparatoire… » (LISEZMOI stocké non compressé ? sinon présence du fichier suffit + tests pytest couvrent le contenu)
     `HTTP ${r.status()}, ${body.length} octets`);
}

// 4 — recherche NL « maisons mutées récemment à Saint-Leu avec jardin » → résultats cohérents
{
  const r = await rq.post(`${BASE}/ia/segments-search`, {
    data: { text: 'maisons mutées récemment à Saint-Leu avec jardin' }, timeout: 45000 });
  const j = await r.json();
  const cles = (j.filtres || []).map((f) => f.cle);
  const communeOk = (j.filtres || []).some((f) => f.cle === 'communes' && (f.values || []).includes('Saint-Leu'));
  ok('4a.nl-traduction', r.status() === 200 && communeOk && cles.includes('jardin_m2')
     && cles.includes('anciennete_mutation_mois'), JSON.stringify(cles));
  const q = await rq.post(`${BASE}/segments/query`, {
    data: { filtres: j.filtres, limit: 5 }, timeout: 60000 });
  const qq = await q.json();
  const toutesSaintLeu = (qq.items || []).every((i) => i.commune === 'Saint-Leu');
  ok('4b.nl-resultats-coherents', q.status() === 200 && qq.count > 0 && toutesSaintLeu,
     `count=${qq.count}, communes=${[...new Set((qq.items || []).map((i) => i.commune))]}`);
}

// 5 — 301 consultations de fiches distinctes le même jour → gel (quota 300)
{
  let gele = null;
  for (let i = 0; i < 301; i++) {
    const idu = `97416000QA${String(i).padStart(4, '0')}`;   // fiches distinctes (404 métier : compte)
    const r = await rq.get(`${BASE}/parcels/${idu}`, { timeout: 15000 });
    if (r.status() === 429) { gele = { i, body: await r.json() }; break; }
  }
  ok('5.quota-301-gel', gele !== null && gele.i >= 300 - 1 && /minuit/.test(gele.body.detail || ''),
     gele ? `429 à la consultation #${gele.i + 1} : ${gele.body.detail}` : 'jamais gelé');
}

// 6 — UI Socle : la page charge sans crash et le bundle porte la barre NL + publipostage
{
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  const resp = await page.goto(`${BASE}/socle/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  const bundleOk = await page.evaluate(async () => {
    const src = [...document.querySelectorAll('script[src]')].map((s) => s.src).find((s) => s.includes('assets/'));
    if (!src) return false;
    const txt = await (await fetch(src)).text();
    return txt.includes('data-seg-nl') && txt.includes('Publipostage');
  });
  ok('6.socle-nl-publipostage', resp.status() < 400 && errs.length === 0 && bundleOk,
     `HTTP ${resp.status()}, pageerrors=${errs.length}, bundle=${bundleOk}`);
}

await browser.close();
console.log(fails ? `\n${fails} échec(s)` : '\nTous les scénarios wave-aci passent.');
process.exit(fails ? 1 : 0);
