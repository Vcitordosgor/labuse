// M16 LOT B — refonte du panneau Notifications. Panneau peuplé de DÉMO (seed) pour tout voir.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);

// ouvrir la cloche
await p.getByRole('button', { name: 'Notifications' }).click();
await p.waitForTimeout(900);
const panel = () => p.locator('.floating').filter({ hasText: 'veilles' });
const txt = (await panel().innerText()).replace(/\s+/g, ' ');
const demoBadges = await p.locator('.floating span', { hasText: 'DÉMO' }).count();
const digestGone = !txt.includes('Digest');
const pointSemaine = txt.includes('Le point de la semaine');
const introReel = txt.includes('parcelles que vous suivez');
const veillesRenom = txt.includes('Vos veilles — alertes sur mesure');
const veillesExpl = txt.includes("dès qu'une parcelle");
const exChips = await p.locator('[data-veille-ex]').count();
const headerCount = txt.match(/Notifications[^·]*·\s*([^V]*?)(Le point|$)/)?.[1]?.trim() ?? '(n/a)';
await p.screenshot({ path: `${OUT}/b1_panneau_refondu.png` });
console.log('intro réelle:', introReel, '| Digest supprimé:', digestGone, '| « Le point de la semaine »:', pointSemaine);
console.log('DÉMO badges:', demoBadges, '| en-tête compteur:', JSON.stringify(headerCount));
console.log('veilles renommées:', veillesRenom, '| explication:', veillesExpl, '| exemples (chips):', exChips);

// exemple de veille : clic → filtres + nom pré-remplis
await p.locator('[data-veille-ex]').first().click();
await p.waitForTimeout(500);
const veilleNom = await p.locator('.floating input[placeholder="Nommez cette veille…"]').inputValue().catch(() => '(absent)');
await p.screenshot({ path: `${OUT}/b2_exemple_veille.png` });
console.log('clic exemple → nom pré-rempli:', JSON.stringify(veilleNom));

// « tout lire » → l'en-tête passe « à jour » (plus de « 0 non lue » incohérent)
const toutLire = p.locator('.floating button', { hasText: 'tout lire' });
if (await toutLire.count()) { await toutLire.first().click(); await p.waitForTimeout(1200); }
const txt2 = (await panel().innerText()).replace(/\s+/g, ' ');
const aJour = txt2.includes('à jour');
const zeroNonLue = /·\s*0\s*non lue/.test(txt2);
await p.screenshot({ path: `${OUT}/b3_tout_lu.png` });
console.log('après tout lire → « à jour »:', aJour, '| « 0 non lue » présent (doit être false):', zeroNonLue);

console.log('done');
await b.close();
