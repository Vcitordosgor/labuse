// M14 F1 — preuve ciblée : verdicts sans « v2 » (panneau + Filtre, légende, cartes, entonnoir)
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';

const BASE = (process.env.BASE || 'http://127.0.0.1:8043/socle/').replace(/\/?$/, '/');
const OUT = new URL('.', import.meta.url).pathname;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 940 }, deviceScaleFactor: 2 });
page.setDefaultTimeout(20000);

// scope île pour peupler la liste des résultats
await page.goto(BASE + '#v=1', { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

// ouvrir le panneau « + Filtre » (chips de verdict : Brûlante / Chaude sans v2)
try {
  const filtre = page.getByText('+ Filtre', { exact: false }).first();
  await filtre.click();
  await page.waitForTimeout(700);
} catch (e) { console.log('filtre?', String(e).slice(0, 100)); }

// capture large (panneau filtre ouvert + cartes de résultat visibles à gauche)
await page.screenshot({ path: `${OUT}/f1_verdicts_sans_v2.png`, fullPage: false });
console.log('shot f1 (panneau filtre + cartes)');

await browser.close();
