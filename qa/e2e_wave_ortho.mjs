// QA E2E — mandat Wave Détection Ortho (clôture Option B). Serveur : labuse api (BASE).
//   node qa/e2e_wave_ortho.mjs
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8003';
let fails = 0;
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? '✓' : '✗'} ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) fails += 1;
};

const browser = await chromium.launch();
const ctx = await browser.newContext();
const rq = ctx.request;

// 1 — les 2 vues piscinistes (presets du moteur) chargent et filtrent
let iduPiscine = null;
for (const slug of ['piscinistes-construction', 'parc-piscines-entretien']) {
  const r = await rq.post(`${BASE}/segments/query`, { data: { slug, limit: 5 }, timeout: 120000 });
  const d = await r.json();
  if (slug === 'parc-piscines-entretien') iduPiscine = d.items?.[0]?.idu ?? null;
  ok(`1.${slug}`, r.status() === 200 && d.count > 0, `count=${d.count}`);
}

// 2 — filtre à la volée : AVEC piscine plus restrictif que la base bâtie
{
  const avec = await (await rq.post(`${BASE}/segments/query`, {
    data: { filtres: [{ cle: 'piscine', value: true }], limit: 1 } })).json();
  ok('2.filtre-piscine-volee', avec.count > 5000 && avec.count < 15000, `count=${avec.count}`);
}

// 3 — exports ROUVERTS (Option B) et non vides, mention precision au preset
{
  const r = await rq.post(`${BASE}/segments/export`, {
    data: { slug: 'parc-piscines-entretien' }, timeout: 120000 });
  const body = (await r.body()).toString('utf-8');
  ok('3a.export-rouvert-non-vide', r.status() === 200 && body.split('\n').length > 10,
    `${body.split('\n').length - 2} lignes`);
  const home = await (await rq.get(`${BASE}/segments`)).json();
  const p = home.presets.find((x) => x.slug === 'piscinistes-construction');
  ok('3b.mention-precision', (p?.description ?? '').includes('90,7 %'));
}

// 4 — badges fiche : endpoint équipements sourcé (précision + attribution IGN)
{
  const r = await rq.get(`${BASE}/ortho/equipements/${iduPiscine}`);
  const d = await r.json();
  ok('4.equipements-fiche', r.status() === 200 && d.piscine === true
    && d.source.includes('90,7 %') && d.source.includes('IGN'),
    `piscine=${d.piscine} ~${d.piscine_m2} m²`);
}

// 5 — PV : STUB (dette v1.1) — candidats en base, jamais matérialisés
{
  const r = await rq.get(`${BASE}/ortho/equipements/${iduPiscine}`);
  const d = await r.json();
  ok('5.pv-stub', d.pv_detecte == null && d.pv_probable_ces == null);
}

// 6 — outil de validation : page + quota serveur toujours en place (v1.1)
{
  const page1 = await rq.get(`${BASE}/ortho/validation?profil=juge&quota=100`);
  const stop = await (await rq.get(
    `${BASE}/ortho/validation/api/suivante?type=piscine&profil=juge&quota=0`)).json();
  ok('6.outil-quota-serveur', page1.status() === 200 && stop.quota_atteint === true);
}

// 7 — UI aux 2 viewports : chargement sans erreur, bundle porte les badges équipements
for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  const page = await ctx.newPage();
  await page.setViewportSize(vp);
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  const resp = await page.goto(`${BASE}/socle/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2500);
  const bundleOk = await page.evaluate(async () => {
    const src = [...document.querySelectorAll('script[src]')].map((s) => s.src)
      .find((s) => s.includes('assets/'));
    const txt = await (await fetch(src)).text();
    return txt.includes('CES probable') && txt.includes('Piscine ~');
  });
  ok(`7.ui-${vp.width}px`, resp.status() < 400 && errs.length === 0 && bundleOk,
    errs.join(' | '));
  await page.close();
}

await browser.close();
console.log(fails ? `\n✗ ${fails} échec(s)` : '\n✓ E2E wave-ortho : tout est vert');
process.exit(fails ? 1 : 0);
