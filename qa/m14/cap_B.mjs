// M14 LOT B — preuve des 3 régressions, sur l'app en marche (:8044/socle/).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8044/socle/';
const OUT = new URL('./B', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1800);

// B3 — Couches ouvert par défaut au premier chargement
const drawerOpen = await p.locator('[data-couches-drawer]').count();
await p.screenshot({ path: `${OUT}/b3_couches_ouvert_defaut.png` });
console.log('B3 — couches drawer visible au load:', drawerOpen > 0);

// B1 — bulle « i » entière : survol de la pastille i d'une couche à long texte (« zonage »)
// on cible la pastille i en face de « Zonage PLU (zones officielles) »
const zonageRow = p.locator('div', { hasText: 'Zonage PLU (zones officielles)' });
const iPill = p.locator('[aria-label="En savoir plus sur cette couche"]');
// survol de la pastille i de la 5e couche (zonage officielle, texte le plus long)
const pills = await iPill.count();
await iPill.nth(Math.min(4, pills - 1)).hover();
await p.waitForTimeout(700);
await p.screenshot({ path: `${OUT}/b1_bulle_i_entiere.png` });
// mesure : la bulle (role=tooltip) est-elle dans le viewport, non rognée à droite ?
const tip = p.locator('[role="tooltip"]').first();
const box = await tip.boundingBox().catch(() => null);
const vw = 1440;
console.log('B1 — bulle tooltip box:', box, '| right<=vw:', box ? (box.x + box.width <= vw) : 'no tip');
console.log('B1 — bulle texte:', box ? (await tip.innerText()).slice(0, 60) : '—');

// B2 — icônes équipements : activer la couche puis zoomer
// clic sur « Équipements » dans la liste des couches
await p.getByText('Équipements', { exact: true }).first().click().catch(() => {});
await p.waitForTimeout(1500);
await p.screenshot({ path: `${OUT}/b2_equipements_actives.png` });
console.log('done');
await b.close();
