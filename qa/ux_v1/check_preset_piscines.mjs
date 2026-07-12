// Fix preset parc-piscines — vérification POST-APPLICATION (à lancer APRÈS la mise à jour
// de la ligne segment_presets + refresh des compteurs). Usage :
//   BASE=http://127.0.0.1:8000/socle/ node qa/ux_v1/check_preset_piscines.mjs
// Asserts : filtres servis (emprise 40-400, plus de type_bien), compteur galerie ≈ 5 784,
// phrase de bénéfice alignée sur le compteur ; screenshot → audit_shots/ux_v1/.
const pw = await import('../../frontend/node_modules/playwright/index.mjs');
const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
const API = BASE.replace(/\/socle\/?$/, '');
let failed = 0;
const ok = (nom, cond, detail = '') => {
  console.log(`${cond ? '✓' : '✗'} ${nom}${cond ? '' : ` — ${detail}`}`);
  if (!cond) failed++;
};

const home = await fetch(`${API}/segments`).then((r) => r.json());
const p = home.presets.find((x) => x.slug === 'parc-piscines-entretien');
const cles = p.filtres.map((f) => f.cle);
ok('filtres servis : piscine + emprise 40-400 + jardin 100', JSON.stringify(cles) === '["piscine","emprise_batie_m2","jardin_m2"]', JSON.stringify(p.filtres));
const emp = p.filtres.find((f) => f.cle === 'emprise_batie_m2');
ok('fenêtre emprise 40-400', emp?.min === 40 && emp?.max === 400);
ok('compteur rafraîchi ≥ 5 000 (attendu 5 784)', (p.count ?? 0) >= 5000, `count=${p.count}`);

const b = await pw.chromium.launch();
const page = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
await page.evaluate(() => window.__labuse.setView('segments'));
await page.waitForTimeout(1800);
const carte = page.locator('[data-seg-preset="parc-piscines-entretien"]');
const compteur = (await carte.locator('[data-seg-preset-count]').textContent() || '').trim();
const phrase = await carte.locator('[data-seg-benefice]').textContent().catch(() => null);
ok('galerie : compteur affiché = count API', compteur.replace(/[  ]/g, '') === (p.count ?? 0).toLocaleString('fr-FR').replace(/[  ]/g, ''), `carte=${compteur}`);
if (phrase) ok('phrase piscines alignée sur le compteur', phrase.replace(/[  ]/g, ' ').includes(compteur.replace(/[  ]/g, ' ')), phrase);
await page.screenshot({ path: new URL('../../audit_shots/ux_v1/apres_fix_preset_piscines_galerie.png', import.meta.url).pathname });
await b.close();
console.log(failed === 0 ? '── preset parc-piscines : tout est vert ──' : `── ${failed} échec(s) ──`);
process.exit(failed === 0 ? 0 : 1);
