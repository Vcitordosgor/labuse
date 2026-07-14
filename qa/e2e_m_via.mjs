// QA E2E — mandat M-VIA (viabilisation & raccordement). Serveur attendu sur BASE
// (labuse api), table parcel_viabilisation construite (labuse viabilisation), front
// buildé (frontend/dist). Assertions API + captures navigateur des 2 blocs.
//   IDU_CONF=... IDU_LOURDE=... node qa/e2e_m_via.mjs
import { mkdirSync } from 'node:fs';
import { chromium } from '../frontend/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const SOURCE = process.env.SOURCE || 'q_v5_m6b';
const OUT = 'reports/m-via/captures';
mkdirSync(OUT, { recursive: true });

// parcelles de démo (confirmée + lourde) — passées par env, sinon défauts découverts.
const IDU_CONF = process.env.IDU_CONF;
const IDU_LOURDE = process.env.IDU_LOURDE;

let fails = 0;
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? '✓' : '✗'} ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) fails += 1;
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
const rq = ctx.request;
const fiche = async (idu) => (await rq.get(`${BASE}/parcels/${idu}?source=${SOURCE}`)).json();

// ─────────────────────────── 1. Bloc viabilisation (confirmée) ───────────────────────────
if (IDU_CONF) {
  const f = await fiche(IDU_CONF);
  const v = f.viabilisation;
  ok('1a.viab-present', !!v, `commune=${f.commune}`);
  ok('1b.viab-confirmee', v && v.score >= 70 && v.band === 'confirmee', `score=${v?.score} band=${v?.band}`);
  ok('1c.contributions-tracees', v && v.contributions.length >= 2 && v.contributions.some((c) => c.points > 0));
  const permis = v?.contributions.find((c) => c.libelle.startsWith('Permis'));
  ok('1d.permis-signal-fort', permis && permis.points > 0 && /permis/i.test(permis.detail), `${permis?.points}pts`);
  // Lot 3 — coût qualitatif, JAMAIS en euros
  const cout = JSON.stringify(v?.cout_raccordement || {});
  ok('1e.cout-qualitatif', !!v?.cout_raccordement?.niveau && !cout.includes('€') && !/\d+\s*eur/i.test(cout));
  // indicateur, jamais un verrou : disclaimer probabilité + interdiction tracé
  ok('1f.disclaimer-indicateur', /probabilit|certitude/i.test(v?.disclaimer || ''));
  ok('1g.aucun-trace-reseau', /tracé/i.test(v?.disclaimer || '') && !JSON.stringify(v).match(/"coordinates"|"geom"|"traces?"/i));
  // Lot 2.5 — note PV S3REnR niveau île
  ok('1h.elec-pv-ilot', !!v?.elec_pv?.note && /S3REnR|photovolta/i.test(v.elec_pv.note));
}

// ─────────────────────────── 2. Bloc viabilisation (lourde) ───────────────────────────
if (IDU_LOURDE) {
  const f = await fiche(IDU_LOURDE);
  const v = f.viabilisation;
  ok('2a.viab-lourde', v && v.score < 25 && v.band === 'lourde', `score=${v?.score} band=${v?.band}`);
  ok('2b.cout-extension', /extension|surcoût/i.test(v?.cout_raccordement?.niveau || ''));
}

// ─────────────────────────── 3. Bloc gestionnaires (Lot 1) ───────────────────────────
{
  const idu = IDU_CONF || IDU_LOURDE;
  if (idu) {
    const f = await fiche(idu);
    const g = f.gestionnaires;
    ok('3a.gest-present', !!g, `commune=${g?.commune}`);
    ok('3b.gest-epci', !!g?.epci?.code && ['CINOR', 'CIREST', 'TCO', 'CIVIS', 'CASUD'].includes(g.epci.code));
    ok('3c.gest-eau-assainissement', !!g?.eau?.operateur && !!g?.assainissement?.operateur);
    ok('3d.gest-edf-sei', g?.electricite?.gestionnaire === 'EDF SEI');
    ok('3e.gest-date', !!g?.a_jour_au, `à jour ${g?.a_jour_au}`);
    ok('3f.gest-disclaimer', /revérifier|confirmer|DT-DICT/i.test(g?.disclaimer || ''));
  }
}

// ─────────────────────────── 4. Captures navigateur ───────────────────────────
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 150)));
for (const [tag, idu] of [['confirmee', IDU_CONF], ['lourde', IDU_LOURDE]]) {
  if (!idu) continue;
  await page.goto(`${BASE}/socle/#v=1`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.fill('[data-omnibox]', idu).catch(() => {});
  await page.keyboard.press('Enter');
  await page.waitForTimeout(4000);
  const viab = page.locator('[data-viabilisation]');
  const gest = page.locator('[data-gestionnaires]');
  await viab.first().scrollIntoViewIfNeeded().catch(() => {});
  const vVisible = await viab.count().then((n) => n > 0);
  const gVisible = await gest.count().then((n) => n > 0);
  ok(`4.${tag}-blocs-rendus`, vVisible && gVisible, `viab=${vVisible} gest=${gVisible}`);
  if (vVisible) await viab.screenshot({ path: `${OUT}/viabilisation-${tag}-${idu}.png` }).catch(() => {});
  if (gVisible) await gest.screenshot({ path: `${OUT}/gestionnaires-${tag}-${idu}.png` }).catch(() => {});
  await page.screenshot({ path: `${OUT}/fiche-${tag}-${idu}.png` });
}
ok('4z.pas-erreur-console', errs.length === 0, errs.join(' | '));

await browser.close();
console.log(`\n${fails === 0 ? '✓ E2E M-VIA OK' : `✗ ${fails} échec(s)`} — captures → ${OUT}/`);
process.exit(fails === 0 ? 0 : 1);
