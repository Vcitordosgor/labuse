// M16 LOT C — menu compte / avatar VL : abonnement réel + compte + déconnexion + suggestion.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);

// ── ouvrir le menu compte ──
await p.locator('[data-account-btn]').click();
await p.waitForSelector('[data-account-menu]', { timeout: 8000 });
await p.waitForTimeout(800);
const menu = (await p.locator('[data-account-menu]').innerText()).replace(/\s+/g, ' ');
const logout = await p.locator('[data-account-menu] a[href="/logout"]').count();
await p.screenshot({ path: `${OUT}/c1_menu_ouvert.png` });
console.log('menu:', JSON.stringify(menu.slice(0, 200)));
console.log('abonnement Intégral:', menu.includes('Intégral'), '| session pilote:', menu.includes('Session pilote'),
  '| proposer amélioration:', menu.includes('Proposer une amélioration'), '| déconnexion (/logout):', logout > 0);

// ── formulaire de suggestion ──
await p.locator('[data-account-suggest]').click();
await p.waitForSelector('[data-sugg-texte]', { timeout: 8000 });
await p.locator('[data-sugg-cat="bug"]').click();
await p.locator('[data-sugg-texte]').fill('Preuve M16-C : le menu compte fonctionne, super.');
await p.screenshot({ path: `${OUT}/c2_formulaire.png` });
await p.locator('[data-sugg-send]').click();
await p.waitForSelector('[data-sugg-ok]', { timeout: 8000 });
const ok = (await p.locator('[data-sugg-ok]').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/c3_envoye.png` });
console.log('suggestion envoyée → confirmation:', JSON.stringify(ok.slice(0, 80)));

console.log('done');
await b.close();
