// QA E2E — mandat Wave ANC & Végétation. Serveur attendu sur BASE (labuse api), base
// ingérée (parcel_anc obligatoire ; parcel_vegetation requis pour les checks élagage).
//   node qa/e2e_anc_vegetation.mjs
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

// 1 — galerie : presets servis, filtres ANC dégrisés, mention légale présente
let vegDisponible = false;
{
  const home = await (await rq.get(`${BASE}/segments`)).json();
  const anc = (home.presets ?? []).find((p) => p.slug === 'anc-prospection');
  const ela = (home.presets ?? []).find((p) => p.slug === 'elagage-limite');
  const fProba = (home.filtres ?? []).find((f) => f.cle === 'proba_anc');
  const fCanopee = (home.filtres ?? []).find((f) => f.cle === 'canopee_limite_pct');
  vegDisponible = fCanopee?.disponible === true;
  ok('1a.presets-servis', !!anc && !!ela);
  ok('1b.filtre-proba-anc-degrise', fProba?.disponible === true,
    `disponible=${fProba?.disponible} (${fProba?.raison ?? ''})`);
  ok('1c.mention-anc-legifrance', !!anc?.mention_legale?.texte
    && anc.mention_legale.texte.includes('L.1331-11-1')
    && anc.mention_legale.texte.includes('L.271-4'));
  ok('1d.mention-elagage-art673', !!ela?.mention_legale?.texte
    && ela.mention_legale.texte.includes('673'));
}

// 2 — vue Prospection ANC : charge, non vide, mention dans la réponse query
{
  const r = await rq.post(`${BASE}/segments/query`, {
    data: { slug: 'anc-prospection', limit: 5 }, timeout: 120000 });
  const d = await r.json();
  ok('2a.anc-query-non-vide', r.status() === 200 && d.count > 0, `count=${d.count}`);
  ok('2b.anc-query-mention', !!d.mention_legale?.texte);
  // filtre à la volée : source du zonage
  const r2 = await rq.post(`${BASE}/segments/query`, {
    data: { slug: 'anc-prospection', limit: 5,
            filtres: [{ ou: [{ cle: 'zone_anc', value: true },
                             { cle: 'proba_anc', min: 70 }] },
                      { cle: 'anciennete_mutation_mois', max: 12 },
                      { cle: 'emprise_batie_m2', min: 20 },
                      { cle: 'source_anc', values: ['proba_insee'] }] },
    timeout: 120000 });
  const d2 = await r2.json();
  ok('2c.anc-filtre-source', r2.status() === 200 && d2.count > 0 && d2.count <= d.count,
    `count=${d2.count} (≤ ${d.count})`);
}

// 3 — export CSV « à l'occupant » ANC : non vide, colonnes du mandat
{
  const r = await rq.post(`${BASE}/segments/export`, {
    data: { slug: 'anc-prospection' }, timeout: 180000 });
  const body = (await r.body()).toString('utf-8');
  ok('3.export-anc', r.status() === 200 && body.includes('Probabilité ANC')
    && body.split('\n').length > 2, `${body.split('\n').length - 2} lignes`);
}

// 4 — vue Prospection élagage (uniquement si le Lot B a livré parcel_vegetation)
if (vegDisponible) {
  const r = await rq.post(`${BASE}/segments/query`, {
    data: { slug: 'elagage-limite', limit: 5 }, timeout: 120000 });
  const d = await r.json();
  ok('4a.elagage-query-non-vide', r.status() === 200 && d.count > 0, `count=${d.count}`);
  const rx = await rq.post(`${BASE}/segments/export`, {
    data: { slug: 'elagage-limite' }, timeout: 180000 });
  const body = (await rx.body()).toString('utf-8');
  ok('4b.export-elagage', rx.status() === 200 && body.includes('Canopée en limite')
    && body.split('\n').length > 2, `${body.split('\n').length - 2} lignes`);
} else {
  console.log('… 4.elagage : parcel_vegetation absent/vide — sauté (Lot B non matérialisé)');
}

// 5 — le preset PV embarque l'exclusion ombrage végétal décochable (si Lot B livré)
if (vegDisponible) {
  const home = await (await rq.get(`${BASE}/segments`)).json();
  const pv = (home.presets ?? []).find((p) => p.slug === 'pv-residentiel');
  const f = (pv?.filtres ?? []).find((x) => x.cle === 'flag_ombrage_vegetal');
  ok('5.pv-exclusion-ombrage-vegetal', !!f && f.value === false && f.optionnel === true);
}

// 6 — RGPD : l'export ne contient aucune colonne nominative
{
  const r = await rq.post(`${BASE}/segments/export`, {
    data: { slug: 'anc-prospection' }, timeout: 180000 });
  const entetes = (await r.body()).toString('utf-8').split('\n')[0].toLowerCase();
  ok('6.rgpd-pas-de-nominatif', !/propri[ée]taire|nom |pr[ée]nom/.test(entetes), entetes.slice(0, 120));
}

await browser.close();
console.log(fails ? `\n✗ ${fails} échec(s)` : '\n✓ E2E ANC & Végétation : tout passe');
process.exit(fails ? 1 : 0);
