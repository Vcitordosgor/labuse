import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 1200 } });
await p.goto('http://127.0.0.1:8060/socle/', { waitUntil: 'networkidle' });
await p.waitForTimeout(1500);
await p.getByRole('button', { name: 'Outils', exact: true }).click();
await p.waitForTimeout(800);
// compter les cartes outils + repérer les libellés clés
const labels = await p.locator('aside').getByRole('button').allInnerTexts();
const flat = labels.join(' | ');
const has = (s) => flat.includes(s);
console.log('Faisabilité (rename C):', has('Faisabilité'), '| Calculette foncière (C2):', has('Calculette foncière'),
  '| Radar des mutations (F):', has('Radar des mutations'), '| Contrôle avant achat (F):', has('Contrôle avant achat'));
await p.screenshot({ path: new URL('./drawer_outils.png', import.meta.url).pathname, fullPage: true });
console.log('capture ok');
await b.close();
