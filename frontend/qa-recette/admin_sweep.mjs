// Famille 9 — Admin (Tour de contrôle). LECTURE SEULE, aucune action mutante.
import { ouvrir, aller, shot, lien, debordements, API } from './harness.mjs';

const FAM = '09-admin';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function snap(journal) {
  return { err: journal.consoleErrors.length, http: journal.httpErrors.length, perr: journal.pageErrors.length };
}
function delta(a, b) {
  return { err: b.err - a.err, http: b.http - a.http, perr: b.perr - a.perr };
}

const { browser, page, journal } = await ouvrir({});
const results = [];

// 1) Ouverture admin via deep-link
let ms = await aller(page, lien.admin());
await sleep(1500);
let title = await page.locator('h1, [data-admin-section]').first().textContent().catch(() => '');
await shot(page, FAM, 'pilotage_ouverture');
results.push({ ecran: 'Ouverture admin (#admin=1) → Pilotage', ms, ...snap(journal), note: `title=${(title||'').slice(0,40)}` });

// Liste des sections du rail
const sections = await page.$$eval('[data-admin-section]', (els) => els.map((e) => ({ key: e.getAttribute('data-admin-section'), txt: (e.textContent||'').trim().slice(0,30) })));
console.log('SECTIONS RAIL:', JSON.stringify(sections));

// Tuiles de pilotage (valeurs)
const tuiles = await page.$$eval('[data-tuile]', (els) => els.map((e) => ({ label: e.getAttribute('data-tuile'), txt: (e.textContent||'').replace(/\s+/g,' ').trim().slice(0,60) })));
console.log('TUILES:', JSON.stringify(tuiles, null, 1));

// Todos « À faire »
const todos = await page.$$eval('[data-todo]', (els) => els.map((e) => ({ cle: e.getAttribute('data-todo'), tone: e.getAttribute('data-tone'), txt: (e.textContent||'').replace(/\s+/g,' ').trim().slice(0,80) })));
console.log('TODOS:', JSON.stringify(todos, null, 1));

let deb = await debordements(page);
console.log('DEBORD pilotage:', JSON.stringify(deb));

// Détecter NaN/undefined/null dans le pilotage
const bodyTxt = await page.locator('body').innerText();
const badPilot = /NaN|undefined|\bnull\b/.test(bodyTxt);
console.log('PILOTAGE badTokens?', badPilot);

// 2) Parcourir chaque section via clic rail
const order = ['licences', 'donnees', 'courrier', 'radar', 'produit', 'ia', 'contacts'];
for (const key of order) {
  const before = snap(journal);
  const btn = page.locator(`[data-admin-section="${key}"]`);
  if (await btn.count() === 0) { results.push({ ecran: `Rail ${key}`, note: 'bouton ABSENT' }); continue; }
  const t0 = Date.now();
  await btn.first().click();
  try { await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch {}
  await sleep(1800);
  const dt = Date.now() - t0;
  const txt = await page.locator('body').innerText();
  const bad = /NaN|undefined/.test(txt);
  const deb2 = await debordements(page);
  await shot(page, FAM, `section_${key}`);
  const d = delta(before, snap(journal));
  results.push({ ecran: `Section ${key}`, ms: dt, dErr: d.err, dHttp: d.http, dPerr: d.perr, bad, deb: deb2.length });
  console.log(`== ${key} == ms=${dt} dErr=${d.err} dHttp=${d.http} bad=${bad} deb=${deb2.length}`);
  if (d.http > 0) console.log('   new HTTP:', journal.httpErrors.slice(-d.http));
  if (d.err > 0) console.log('   new ERR:', journal.consoleErrors.slice(-d.err));
}

console.log('\n=== RESULTS ===');
console.log(JSON.stringify(results, null, 1));
await browser.close();
