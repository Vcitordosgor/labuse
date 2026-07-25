// M17 LOT B — veilles en langage naturel : phrase → filtres visibles + veille ; refus honnête.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);
const openBell = async () => { await p.getByRole('button', { name: 'Notifications' }).click(); await p.waitForTimeout(700); };

// ── B1/B2 : phrase déclenchable → filtres visibles + veille enregistrée ──
await openBell();
await p.locator('[data-nl-veille]').fill('les parcelles à Saint-Paul qui deviennent chaudes');
await p.locator('[data-nl-go]').click();
await p.waitForSelector('[data-nl-resume]', { timeout: 10000 });
const resume = (await p.locator('[data-nl-resume]').innerText()).replace(/\s+/g, ' ');
// filtres devenus visibles (chips actives dans l'en-tête) + nom pré-rempli
const veilleNom = await p.locator('.floating input[placeholder="Nommez cette veille…"]').inputValue();
const chipsTxt = (await p.locator('header').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/b1_nl_traduit.png` });
console.log('B2 resume:', JSON.stringify(resume.slice(0, 90)));
console.log('   nom pré-rempli:', JSON.stringify(veilleNom), '| chips visibles (Saint-Paul/chaude):', /Saint-Paul|chaude|Priorité/i.test(chipsTxt));
// enregistrer la veille (même bouton que les chips)
const before = await p.locator('.floating a[href^="/socle/#"]').count();
await p.locator('.floating button', { hasText: '+ Veille' }).click();
await p.waitForTimeout(1200);
const after = await p.locator('.floating a[href^="/socle/#"]').count();
await p.screenshot({ path: `${OUT}/b2_veille_enregistree.png` });
console.log('   veille enregistrée:', after > before, `(${before} → ${after})`);

// ── B3 : demande INDÉCLENCHABLE → refus honnête, PAS d'enregistrement ──
await p.locator('[data-nl-veille]').fill('préviens-moi si le PLU change sur mes parcelles');
await p.locator('[data-nl-go]').click();
await p.waitForSelector('[data-nl-refus]', { timeout: 10000 });
const refus = (await p.locator('[data-nl-refus]').innerText()).replace(/\s+/g, ' ');
const noResume = await p.locator('[data-nl-resume]').count();
await p.screenshot({ path: `${OUT}/b3_refus_honnete.png` });
console.log('B3 refus:', JSON.stringify(refus.slice(0, 120)));
console.log('   pas de résumé affiché (refus pur):', noResume === 0);

// ── B4 : les chips M16 existent toujours ──
console.log('B4 chips M16 présentes:', (await p.locator('[data-veille-ex]').count()) >= 2);

console.log('done');
await b.close();
