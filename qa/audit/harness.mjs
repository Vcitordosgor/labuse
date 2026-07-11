// LA BUSE — harnais d'audit UI (mandat 11/07/2026). Collecte automatique par page :
// console.error/warn, pageerror, requêtes en échec, HTTP ≥ 400, promesses non catchées.
// Chaque anomalie : horodatée + URL + vue + action déclencheuse. Preuves → audit_shots/ui2026/.
import { mkdirSync, appendFileSync, writeFileSync } from 'node:fs';

const pw = await import('../../frontend/node_modules/playwright/index.mjs')
  .catch(() => import('/opt/node22/lib/node_modules/playwright/index.mjs'));
export const { chromium } = pw;

export const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
export const SHOTS = new URL('../../audit_shots/ui2026/', import.meta.url).pathname;
export const FINDINGS = new URL('./findings.jsonl', import.meta.url).pathname;
mkdirSync(SHOTS, { recursive: true });

//: bruit non applicatif (tuiles/basemap externes, cert CI) — jamais compté comme anomalie.
const NOISE = /tile|cartocdn|basemaps|openstreetmap|data\.geopf|ERR_CERT|ERR_NETWORK_CHANGED/i;

export const state = { vue: '?', action: 'chargement', viewport: '?', anomalies: [] };
export const setCtx = (vue, action) => { state.vue = vue; if (action !== undefined) state.action = action; };

export function pushAnomalie(type, detail, url = '') {
  const a = { ts: new Date().toISOString(), viewport: state.viewport, vue: state.vue,
              action: state.action, type, detail: String(detail).slice(0, 500), url };
  state.anomalies.push(a);
  appendFileSync(FINDINGS, JSON.stringify(a) + '\n');
}

/** Branche les collecteurs sur une page. À appeler UNE fois par page créée. */
export function collecte(page) {
  page.on('console', (m) => {
    if ((m.type() === 'error' || m.type() === 'warning') && !NOISE.test(m.text()))
      pushAnomalie(`console.${m.type()}`, m.text(), page.url());
  });
  page.on('pageerror', (e) => pushAnomalie('pageerror', e.message, page.url()));
  page.on('requestfailed', (r) => {
    if (!NOISE.test(r.url())) pushAnomalie('requestfailed', `${r.failure()?.errorText} ${r.url()}`, page.url());
  });
  page.on('response', (r) => {
    try {
      const u = new URL(r.url());
      if (u.port === '8000' && r.status() >= 400 && !NOISE.test(r.url()))
        pushAnomalie(`http.${r.status()}`, `${r.request().method()} ${u.pathname}${u.search.slice(0, 80)}`, page.url());
    } catch { /* URL non parsable : ignorée */ }
  });
}

export async function shot(page, nom) {
  const f = `${SHOTS}${state.viewport}_${nom}.png`;
  await page.screenshot({ path: f, timeout: 8000 }).catch((e) => pushAnomalie('shot.fail', `${nom}: ${e.message}`));
  return f;
}

export const VIEWPORTS = [
  ['1440', { width: 1440, height: 900 }],
  ['768', { width: 768, height: 1024 }],
  ['375', { width: 375, height: 812 }],
];

/** Attend le boot de l'app socle (hook QA exposé). */
export async function boot(page) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
  await page.waitForTimeout(1200);
}

export function bilan(nomRun) {
  const parType = {};
  for (const a of state.anomalies) parType[a.type] = (parType[a.type] || 0) + 1;
  console.log(`\n── ${nomRun} : ${state.anomalies.length} anomalie(s) ──`);
  console.log(JSON.stringify(parType, null, 1));
}

export const RESULTATS = new URL('./resultats/', import.meta.url).pathname;
mkdirSync(RESULTATS, { recursive: true });
export const sauveJson = (nom, data) =>
  writeFileSync(`${RESULTATS}${nom}.json`, JSON.stringify(data, null, 1));
