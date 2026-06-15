// LA BUSE — suite E2E (Playwright) — audit fonctionnel.
//   node qa/e2e.mjs            (l'app doit tourner : `labuse api` sur :8000)
//   BASE=http://127.0.0.1:8000/app/ node qa/e2e.mjs
// Sort en code ≠ 0 si un scénario échoue. Le bruit des tuiles externes (réseau bloqué)
// est ignoré : seules les erreurs applicatives comptent.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8000/app/';
const PW = '/opt/node22/lib/node_modules/playwright/index.mjs';
const tileNoise = /tile|cartocdn|basemaps|openstreetmap|ERR_CERT|net::ERR_/i;
let fails = 0;
const ok = (n, cond, detail = '') => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${n}${detail ? ' — ' + detail : ''}`); if (!cond) fails++; };

const browser = await chromium.launch({ args: ['--ignore-certificate-errors'] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true });

// helpers
const sheetHidden = (pg) => pg.evaluate(() => document.querySelector('#sheet').classList.contains('hidden'));
const rmNum = async (pg) => { const t = await pg.locator('#rm-count').textContent(); const m = (t || '').replace(/\s/g, '').match(/\d+/); return m ? +m[0] : null; };

// ───────── parcours principal ─────────
const page = await ctx.newPage();
const pageErrors = [], consoleErrors = [], badReq = [];
page.on('pageerror', e => pageErrors.push(e.message));
page.on('console', m => { if (m.type() === 'error' && !tileNoise.test(m.text())) consoleErrors.push(m.text()); });
page.on('response', r => { try { const u = new URL(r.url()); if (u.port === '8000' && r.status() >= 400) badReq.push(`${u.pathname} ${r.status()}`); } catch {} });

const resp = await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 25000 });
await page.waitForTimeout(6500);

// 1 — chargement sans crash
ok('1.load-no-crash', resp.status() < 400 && pageErrors.length === 0, `HTTP ${resp.status()}, pageerrors=${pageErrors.length}`);
// 2 — KPIs remplis (jamais « — »)
const kpis = await page.evaluate(() => ['kpi-total', 'kpi-opp', 'kpi-creuser', 'kpi-exclue'].map(i => document.getElementById(i).textContent));
ok('2.kpis-filled', kpis.every(v => v && v !== '—'), JSON.stringify(kpis));
// 3 — pas de loader + empty simultanés ; empty caché par défaut
const emptyShown = await page.locator('#map-empty').isVisible();
ok('3.no-empty-at-default', !emptyShown, `empty=${emptyShown}`);
// 4 — filtres verdict changent le compteur
await page.locator('.qf[data-status="opportunite"]').click(); await page.waitForTimeout(600);
const nOpp = await rmNum(page);
await page.locator('.qf[data-status="all"]').click(); await page.waitForTimeout(600);
const nAll = await rmNum(page);
ok('4.verdict-filter', nOpp !== null && nAll !== null && nAll >= nOpp, `opp=${nOpp} all=${nAll}`);
// 5 — état vide propre + reset récupère des résultats
await page.locator('#filter-toggle').click(); await page.waitForTimeout(200);
await page.evaluate(() => { const s = document.querySelector('#f-surf'); s.value = s.max; s.dispatchEvent(new Event('input', { bubbles: true })); });
await page.waitForTimeout(700);
const emptyAfterStrict = await page.locator('#map-empty').isVisible();
const emptyTitle = await page.locator('#map-empty .me-title').textContent().catch(() => '');
await page.locator('#map-empty .js-reset').click(); await page.waitForTimeout(600);
const nReset = await rmNum(page);
ok('5.empty-and-reset', emptyAfterStrict && nReset > 0, `empty=${emptyAfterStrict} ("${emptyTitle}") reset→${nReset}`);
// 6 — audit champ vide : pas de fiche, message d'aide
await page.locator('#audit-q').fill('');
await page.locator('.audit-go').click(); await page.waitForTimeout(700);
const sheetStillHidden = await sheetHidden(page);
const auditMsg = await page.locator('#audit-msg').textContent();
ok('6.audit-empty-guarded', sheetStillHidden && /saisi/i.test(auditMsg || ''), `fermée=${sheetStillHidden} msg="${(auditMsg||'').slice(0,40)}"`);
// 7 — carte : ouverture fiche + fermeture (Escape) + inert
await page.locator('.qf[data-status="all"]').click(); await page.waitForTimeout(500);
await page.locator('#parcel-list > *').first().click(); await page.waitForTimeout(1500);
const fOpen = await page.evaluate(() => { const s = document.querySelector('#sheet'); return { open: !s.classList.contains('hidden'), inert: s.hasAttribute('inert'), note: s.querySelectorAll('.note-pro').length, gauge: s.querySelectorAll('.g-arc').length }; });
ok('7.fiche-open', fOpen.open && !fOpen.inert && fOpen.note > 0, JSON.stringify(fOpen));
await page.keyboard.press('Escape'); await page.waitForTimeout(600);
const fClosed = await page.evaluate(() => { const s = document.querySelector('#sheet'); const cb = document.querySelector('#sheet-close'); cb.focus(); return { hidden: s.classList.contains('hidden'), inert: s.hasAttribute('inert'), focusLeak: document.activeElement === cb }; });
ok('7b.fiche-escape-inert', fClosed.hidden && fClosed.inert && !fClosed.focusLeak, JSON.stringify(fClosed));
// 8 — navigation onglets (pipeline ↔ radar) + colonnes
await page.locator('.nav-kanban.js-view').first().click(); await page.waitForTimeout(1400);
const kb = await page.evaluate(() => ({ open: document.body.classList.contains('view-kanban'), cols: document.querySelectorAll('#kb-board .kb-col').length }));
ok('8.pipeline-columns', kb.open && kb.cols >= 1, JSON.stringify(kb));
await page.locator('.kb-back').click(); await page.waitForTimeout(700);
ok('8b.back-to-radar', await page.evaluate(() => !document.body.classList.contains('view-kanban')));
// 9 — démo guidée : ouverture + fermeture Escape, pas de commande terminal au 1er niveau
await page.locator('.nav-demo.js-demo').first().click(); await page.waitForTimeout(1200);
const demoOpen = await page.locator('#demo-overlay').isVisible();
const rawCmd = await page.locator('#demo-body code:visible').count();
await page.keyboard.press('Escape'); await page.waitForTimeout(500);
const demoClosed = !(await page.locator('#demo-overlay').isVisible());
ok('9.demo-open-close', demoOpen && demoClosed && rawCmd === 0, `open=${demoOpen} close=${demoClosed} cmdVisibles=${rawCmd}`);
// 10 — santé globale : aucune erreur JS / requête 4xx-5xx applicative
ok('10.no-js-errors', pageErrors.length === 0 && consoleErrors.length === 0, `pageerr=${pageErrors.length} console=${consoleErrors.length} ${JSON.stringify([...new Set(consoleErrors)].slice(0,3))}`);
ok('10b.no-bad-requests', badReq.length === 0, JSON.stringify([...new Set(badReq)].slice(0, 8)));

// ───────── garde-fou régression FIX KPI fallback (/stats HS) ─────────
const page2 = await ctx.newPage();
await page2.route('**/stats**', r => r.abort());
await page2.goto(BASE, { waitUntil: 'domcontentloaded' }); await page2.waitForTimeout(6500);
const kpis2 = await page2.evaluate(() => ['kpi-total', 'kpi-opp', 'kpi-creuser', 'kpi-exclue'].map(i => document.getElementById(i).textContent));
ok('11.kpi-fallback-stats-down', kpis2.every(v => v && v !== '—'), `KPIs=${JSON.stringify(kpis2)}`);

await browser.close();
console.log(`\n${fails === 0 ? 'OK' : 'ÉCHEC'} — ${fails} scénario(s) en échec.`);
process.exit(fails === 0 ? 0 : 1);
