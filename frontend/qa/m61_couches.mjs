// LA BUSE — M6.1 items 1+2 (couches carte) :
//  1. « Zonage PLU (parcelles) » : recoloration U/AU/A/N (palette dédiée), étiquette de zone
//     précise (zone_lib) au zoom ≥ 16 + popup au clic, légende dédiée, commune (geojson) ET île (tuiles)
//  2. « 50 pas géométriques » : case Couches, style distinct, toast état-vide (commune sans littoral)
//   node frontend/qa/m61_couches.mjs      (app d'audit :8010 — JAMAIS :8000)
const pw = await import('../node_modules/playwright/index.mjs')
  .catch(() => import('/opt/node22/lib/node_modules/playwright/index.mjs'));
const { chromium } = pw;

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/';
const SHOTS = process.env.SHOTS || 'reports/m61-couches/captures';
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 });

const idle = () => page.evaluate(() => new Promise((r) => {
  const m = window.__labuse_map;
  if (m.loaded() && m.areTilesLoaded()) r(true); else m.once('idle', () => r(true));
}));
const paintHasZone = (layer) => page.evaluate((l) =>
  JSON.stringify(window.__labuse_map.getPaintProperty(l, 'fill-color') ?? '').includes('zone_fam'), layer);
const vis = (layer) => page.evaluate((l) => window.__labuse_map.getLayoutProperty(l, 'visibility'), layer);
const toggleCouche = async (label) => {
  await page.locator(`aside button:has-text("${label}")`).first().click();
  await page.waitForTimeout(600);
};

/* ════ ITEM 1 — mode COMMUNE (GeoJSON, jointure live parcel_zone_plu) ════ */
await page.evaluate(() => window.__labuse.setCommune('Saint-Paul'));
await page.waitForTimeout(2500); await idle();

await toggleCouche('Zonage PLU (parcelles)');
ok('1.legende-dediee', (await page.locator('[data-legend-zonage]').count()) === 1);
const nFam = await page.locator('[data-legend-zonage] .flex.items-center').count();
ok('1.legende-5-familles', nFam === 5, `${nFam} familles`);
// la vignette VERDICT reste intacte au-dessus de la légende zonage
const legTxt = (await page.locator('[data-legend-zonage]').locator('..').textContent()) ?? '';
ok('1.vignette-verdict-intacte', /VERDICT/.test(legTxt) && /ZONAGE PLU/.test(legTxt));
ok('1.fill-commune-zone_fam', await paintHasZone('parcels-fill'));
ok('1.label-commune-visible', (await vis('parcels-zone-label')) === 'visible');

// une parcelle AVEC zone_lib → zoom 16.5 dessus, étiquette + popup au clic
// (le GeoJSON commune fait ~60k parcelles : attendre le fetch + setData, pas seulement l'idle carte)
await page.waitForFunction(() => {
  try { return window.__labuse_map.querySourceFeatures('parcels').some((x) => x.properties?.zone_lib && x.properties.zone_lib !== 'null'); }
  catch { return false; }
}, null, { timeout: 90000 }).catch(() => {});
const target = await page.evaluate(() => {
  const m = window.__labuse_map;
  const f = m.querySourceFeatures('parcels').find((x) => x.properties?.zone_lib && x.properties.zone_lib !== 'null');
  if (!f) return null;
  const c = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0][0] : f.geometry.coordinates[0][0][0];
  return { lng: c[0], lat: c[1], zone: f.properties.zone_lib, fam: f.properties.zone_fam };
});
ok('1.geojson-porte-zone_lib', !!target, target ? `zone ${target.zone} (fam ${target.fam})` : 'aucune parcelle zonée');
if (target) {
  await page.evaluate((t) => { window.__labuse_map.jumpTo({ center: [t.lng, t.lat], zoom: 16.6 }) }, target);
  await page.waitForTimeout(1500); await idle();
  // les étiquettes RENDENT réellement (régression glyphs Carto : 404 silencieux = zéro symbol)
  const nLabels = await page.evaluate(() =>
    window.__labuse_map.queryRenderedFeatures(undefined, { layers: ['parcels-zone-label'] }).length);
  ok('1.etiquettes-rendues-z16', nLabels > 0, `${nLabels} étiquettes à l'écran`);
  await page.screenshot({ path: `${SHOTS}/item1-zonage-commune-z16-etiquettes.png` });
  // clic au centre → popup « Zone U1e » (le gabarit équipements) + la fiche s'ouvre normalement
  const px = await page.evaluate((t) => {
    const m = window.__labuse_map;
    const fs = m.queryRenderedFeatures(m.project([t.lng, t.lat]), { layers: ['parcels-fill'] });
    const p = m.project([t.lng, t.lat]);
    return { x: p.x, y: p.y, hit: fs.length > 0 };
  }, target);
  const canvas = await page.locator('.maplibregl-canvas').boundingBox();
  await page.mouse.click(canvas.x + px.x, canvas.y + px.y);
  await page.waitForTimeout(900);
  const popup = (await page.locator('.maplibregl-popup').textContent().catch(() => '')) ?? '';
  ok('1.popup-clic-zone', /Zone\s/.test(popup) && /zonage PLU/.test(popup), `« ${popup.trim().slice(0, 60)} »`);
  await page.screenshot({ path: `${SHOTS}/item1-zonage-commune-popup-clic.png` });
  await page.keyboard.press('Escape');  // referme la fiche ouverte par le même clic
  await page.waitForTimeout(400);
}

// dézoom pour la vue d'ensemble commune (recoloration par famille)
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.27, -21.04], zoom: 12.4 }) });
await page.waitForTimeout(1800); await idle();
await page.screenshot({ path: `${SHOTS}/item1-zonage-commune-vue.png` });

// toggle OFF → le verdict revient (plus de zone_fam dans le remplissage, étiquettes éteintes)
await toggleCouche('Zonage PLU (parcelles)');
ok('1.toggle-off-verdict-revient', !(await paintHasZone('parcels-fill')));
ok('1.toggle-off-labels-off', (await vis('parcels-zone-label')) === 'none');
ok('1.toggle-off-legende-retiree', (await page.locator('[data-legend-zonage]').count()) === 0);

/* ════ ITEM 2 — 50 pas géométriques ════ */
await toggleCouche('50 pas géométriques');
ok('2.couche-visible', (await vis('ov-50pas')) === 'visible' && (await vis('ov-50pas-line')) === 'visible');
// tooltip métier exact sur la case du panneau Couches
const hint = await page.locator('aside button:has-text("50 pas géométriques")').first().getAttribute('title');
ok('2.tooltip-metier', /81,20\s?m/.test(hint ?? '') && /outre-mer/.test(hint ?? ''), `« ${hint} »`);
ok('2.legende-active', (await page.locator('[data-legend-50pas]').count()) === 1);
// Saint-Paul est littorale → PAS de toast « sans littoral »
await page.waitForTimeout(1200);
const toastSP = (await page.locator('[data-toast]').textContent().catch(() => '')) ?? '';
ok('2.littorale-pas-de-toast', !/50 pas/.test(toastSP));
// la bande longe le rivage (features présentes dans la source)
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.2705, -21.009], zoom: 14.2 }) });
await page.waitForTimeout(1500); await idle();
const n50 = await page.evaluate(() => window.__labuse_map.querySourceFeatures('ov-50pas').length);
ok('2.bande-rendue', n50 > 0, `${n50} features en viewport`);
await page.screenshot({ path: `${SHOTS}/item2-50pas-commune-littoral.png` });

// commune SANS littoral → toast état-vide (pattern ANRU), la couche reste honnêtement vide
await page.evaluate(() => window.__labuse.setCommune('Salazie'));
await page.waitForFunction(() => document.querySelector('[data-toast]')?.textContent?.includes('50 pas'),
  null, { timeout: 8000 }).catch(() => {});
const toastSalazie = (await page.locator('[data-toast]').textContent().catch(() => '')) ?? '';
ok('2.toast-sans-littoral', /50 pas/.test(toastSalazie) && /Salazie/.test(toastSalazie), `« ${toastSalazie} »`);
await page.screenshot({ path: `${SHOTS}/item2-50pas-salazie-toast.png` });

/* ════ ITEM 1 — mode ÎLE (tuiles MVT, zone_fam/zone_lib embarquées au build) ════ */
const meta = await page.evaluate(() => fetch('/map/tiles/meta').then((r) => r.json()));
ok('ile.tiles-meta', meta.run_label === 'q_v5_m6b' && meta.zonage_parcelle === true,
  JSON.stringify(meta));
await page.evaluate(() => window.__labuse.setCommune(null));
await page.waitForTimeout(2000); await idle();
await toggleCouche('Zonage PLU (parcelles)');
ok('ile.fill-zone_fam', await paintHasZone('ile-fill'));
ok('ile.label-visible', (await vis('ile-zone-label')) === 'visible');
// pas de toast de repli : les tuiles portent le zonage
const toastIle = (await page.locator('[data-toast]').textContent().catch(() => '')) ?? '';
ok('ile.pas-de-toast-repli', !/prochain build/.test(toastIle));
// zoom moyen : recoloration par famille visible sur les tuiles (Saint-Denis)
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.4504, -20.8907], zoom: 13.2 }) });
await page.waitForTimeout(2500); await idle();
// échantillon de POINTS (pas de query plein-viewport : le volume sérialisé à z13+
// fait planter le transport playwright) — 5×5 sondes réparties sur le canvas
const famIle = await page.evaluate(() => {
  const m = window.__labuse_map;
  const { clientWidth: w, clientHeight: h } = m.getCanvas();
  const fams = new Set();
  for (let i = 1; i <= 5; i++) for (let j = 1; j <= 5; j++) {
    const fs = m.queryRenderedFeatures([(w * i) / 6, (h * j) / 6], { layers: ['ile-fill'] });
    const z = fs[0]?.properties?.zone_fam;
    if (z) fams.add(z);
  }
  return [...fams];
});
ok('ile.tuiles-portent-zone_fam', famIle.length >= 2, `familles vues : ${famIle.join(', ')}`);
await page.screenshot({ path: `${SHOTS}/item1-zonage-ile-vue.png` });
// zoom ≥ 16 : étiquette zone_lib depuis les tuiles pleines
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.4504, -20.8907], zoom: 16.3 }) });
await page.waitForTimeout(2500);
await idle();
const libIle = await page.evaluate(() => {
  const m = window.__labuse_map;
  const { clientWidth: w, clientHeight: h } = m.getCanvas();
  for (let i = 1; i <= 5; i++) for (let j = 1; j <= 5; j++) {
    const fs = m.queryRenderedFeatures([(w * i) / 6, (h * j) / 6], { layers: ['ile-fill'] });
    const z = fs[0]?.properties?.zone_lib;
    if (z && z !== 'null') return z;
  }
  return null;
});
ok('ile.tuiles-portent-zone_lib', !!libIle, `ex. « ${libIle} »`);
const nLabelsIle = await page.evaluate(() =>
  window.__labuse_map.queryRenderedFeatures(undefined, { layers: ['ile-zone-label'] }).length);
ok('ile.etiquettes-rendues-z16', nLabelsIle > 0, `${nLabelsIle} étiquettes à l'écran`);
await page.screenshot({ path: `${SHOTS}/item1-zonage-ile-z16-etiquettes.png` });

// 50 pas en mode île (couche servie île entière)
ok('ile.50pas-visible', (await vis('ov-50pas')) === 'visible');
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.29, -21.05], zoom: 11.4 }) });
await page.waitForTimeout(2000); await idle();
await page.screenshot({ path: `${SHOTS}/item2-50pas-ile.png` });

/* ════ PERF — navigation île avec la couche zonage active (info) ════ */
const t0 = Date.now();
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.45, -21.28], zoom: 13 }) }); // Saint-Pierre
await idle();
const dtOn = Date.now() - t0;
await toggleCouche('Zonage PLU (parcelles)');
const t1 = Date.now();
await page.evaluate(() => { window.__labuse_map.jumpTo({ center: [55.29, -20.94], zoom: 13 }) }); // Le Port
await idle();
const dtOff = Date.now() - t1;
console.log(`INFO  perf navigation île : saut+idle couche ON ${dtOn} ms · OFF ${dtOff} ms`);
ok('perf.navigation', dtOn < 15000, `${dtOn} ms (même pipeline de tuiles, colonnes en plus seulement)`);

await browser.close();
console.log(fails === 0 ? '\n✅ M6.1 couches : E2E PASS' : `\n❌ ${fails} échec(s)`);
process.exit(fails === 0 ? 0 : 1);
