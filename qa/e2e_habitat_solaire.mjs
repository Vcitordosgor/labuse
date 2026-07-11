// QA E2E — mandat Habitat Solaire. Serveur attendu sur BASE (labuse api), base ingérée.
//   node qa/e2e_habitat_solaire.mjs
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8002';
let fails = 0;
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? '✓' : '✗'} ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) fails += 1;
};

const browser = await chromium.launch();
const ctx = await browser.newContext();
const rq = ctx.request;

// 1 — galerie segments : le preset pv-residentiel est servi et le filtre score dégrisé
let iduTest = null;
{
  const home = await (await rq.get(`${BASE}/segments`)).json();
  const pv = (home.presets ?? []).find((p) => p.slug === 'pv-residentiel');
  const fscore = (home.filtres ?? []).find((f) => f.cle === 'score_solaire');
  ok('1.preset-pv-residentiel', !!pv && !!fscore && fscore.disponible === true,
    `filtre score_solaire disponible=${fscore?.disponible}`);
}

// 2 — vue Prospection PV résidentiel (= preset du moteur) : résultats non vides
{
  const r = await rq.post(`${BASE}/segments/query`, {
    data: { slug: 'pv-residentiel', limit: 5 }, timeout: 120000 });
  const d = await r.json();
  iduTest = d.items?.[0]?.idu ?? null;
  ok('2.pv-residentiel-non-vide', r.status() === 200 && d.count > 0, `count=${d.count}`);
}

// 3 — export CSV du preset : colonnes solaires présentes
{
  const r = await rq.post(`${BASE}/segments/export`, {
    data: { slug: 'pv-residentiel' }, timeout: 180000 });
  const body = (await r.body()).toString('utf-8');
  ok('3.export-colonnes-solaires', r.status() === 200
    && body.includes('Score solaire') && body.split('\n').length > 2,
    `${body.split('\n').length - 2} lignes`);
}

// 4 — vue Parkings APER : assujettis + échéances dépassées + CSV
{
  const d = await (await rq.get(`${BASE}/solaire/parkings`)).json();
  ok('4a.parkings-aper', d.total > 0 && d.echeances_depassees >= 1,
    `${d.total} parkings, ${d.echeances_depassees} dépassée(s)`);
  const csv = await rq.get(`${BASE}/solaire/parkings?fmt=csv`);
  const rows = +(csv.headers()['x-rows'] || 0);
  ok('4b.parkings-csv', csv.status() === 200 && rows > 0, `${rows} lignes`);
}

// 5 — vue Toitures tertiaires : non vide, scores solaires branchés
{
  const d = await (await rq.get(`${BASE}/solaire/tertiaire`)).json();
  const avecScore = (d.items ?? []).filter((i) => i.score_solaire != null).length;
  ok('5.tertiaire', d.total > 0 && avecScore > 0,
    `${d.total} toitures, ${avecScore} avec score`);
}

// 6 — panneau Solaire de la fiche : données sourcées ; mesure fine = 501 honnête (Lot 8)
{
  const r = await rq.get(`${BASE}/solaire/fiche/${iduTest}`);
  const d = await r.json();
  ok('6a.fiche-solaire', r.status() === 200 && d.score_solaire != null
    && !!d.sources?.gisement, `score=${d.score_solaire}`);
  const m = await rq.post(`${BASE}/solaire/mesure/${iduTest}`);
  ok('6b.mesure-fine-501', m.status() === 501);
}

// 7 — UI : la page charge sans crash aux 2 viewports, le bundle porte les vues solaires
for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  const page = await ctx.newPage();
  await page.setViewportSize(vp);
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  const resp = await page.goto(`${BASE}/socle/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);
  const bundleOk = await page.evaluate(async () => {
    // bundle code-splitté : concaténer le chunk principal + tous les chunks référencés
    const src = [...document.querySelectorAll('script[src]')].map((s) => s.src)
      .find((s) => s.includes('assets/'));
    let txt = await (await fetch(src)).text();
    const chunks = [...new Set(txt.match(/assets\/[A-Za-z0-9_.-]+\.js/g) ?? [])];
    for (const c of chunks) {
      try { txt += await (await fetch(`/socle/${c}`)).text() } catch { /* chunk optionnel */ }
    }
    return txt.includes('Parkings APER') && txt.includes('Toitures tertiaires')
      && txt.includes('GISEMENT SOLAIRE');
  });
  ok(`7.ui-${vp.width}px`, resp.status() < 400 && errs.length === 0 && bundleOk,
    errs.join(' | '));
  await page.close();
}

await browser.close();
console.log(fails ? `\n✗ ${fails} échec(s)` : '\n✓ E2E habitat-solaire : tout est vert');
process.exit(fails ? 1 : 0);
