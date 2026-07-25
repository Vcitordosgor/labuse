// M17 LOT A — millésimes des sources : trouvés affichés, introuvables (BPE/SAFER) en « non tracé ».
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 2400 } });
p.setDefaultTimeout(20000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);
await p.getByText('Sources', { exact: true }).first().click();
await p.waitForTimeout(2000);
const body = (await p.locator('body').innerText()).replace(/\s+/g, ' ');
const has = (s) => body.includes(s);

// millésimes RÉELS attendus
const found = {
  'Parc National → millésime 2021': has('millésime 2021'),
  'QPV → génération 2024': has('génération 2024'),
  'ITT → arrêtés déc. 2023': has('arrêtés déc. 2023'),
  '50 pas → cadastre 1877': has('cadastre 1877'),
  'trait de côte → millésime 2018': has('millésime 2018'),
};
// introuvables assumés
const nonTrace = (body.match(/non tracé en base/g) || []).length;
console.log('=== millésimes trouvés (attendus true) ===');
for (const [k, v] of Object.entries(found)) console.log(`  ${v ? '✓' : '✗'} ${k}`);
console.log('=== BPE / SAFER : « non tracé » assumé encore présent ===');
console.log('  occurrences « non tracé en base » :', nonTrace, '(BPE + SAFER + autres non ingérées)');
console.log('  aucun « — » nu :', !/\bVersion en service[^A-Za-z0-9]*—/.test(body));
await p.screenshot({ path: `${OUT}/sources_millesimes.png`, fullPage: true });
console.log('done');
await b.close();
