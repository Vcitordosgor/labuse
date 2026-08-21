// M137-T — captures : outil « Pièges et risques » (fusion O5 + M10), deux entrées.
//  A) une parcelle → servitudes détaillées + bloc NON COUVERT (PEB inclus, retiré des couvertes).
//  B) un lot → checklist + risque + bloc NON COUVERT REPORTÉ (plus de « RAS » muet à l'échelle du lot).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = '97414000CE0141';   // intersecte une SUP → l'entrée détail a de la matière
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 160)) } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);

// Outils → Pièges et risques
await soft(async () => { await page.getByRole('button', { name: 'Outils' }).first().click(); await page.waitForTimeout(700); }, 'outils');
await soft(async () => { await page.locator('[data-outil="risques"]').click(); await page.waitForTimeout(900); }, 'risques');
console.log('deux entrées présentes:', await page.locator('[data-risques-entree]').count());

// ── A) UNE PARCELLE (entrée par défaut) ──
await soft(async () => { await page.locator('[data-risques-entree="parcelle"]').click(); await page.waitForTimeout(300); }, 'entrée parcelle');
await soft(async () => { await page.locator('[data-o5-idu]').fill(IDU); await page.waitForTimeout(2500); }, 'idu');
const aNonCouvert = await page.getByText('Non couvert par la base').count();
const aPeb = await page.getByText('Plan d\'Exposition au Bruit').count();
console.log('A · bloc NON COUVERT:', aNonCouvert > 0, '| PEB en non couvert:', aPeb > 0);
await page.screenshot({ path: `${OUT}/A_une_parcelle_detail.png`, fullPage: true });

// ── B) UN LOT ──
await soft(async () => { await page.locator('[data-risques-entree="lot"]').click(); await page.waitForTimeout(400); }, 'entrée lot');
await soft(async () => { await page.locator('[data-diligence-quick]').fill(IDU); await page.locator('[data-diligence-add]').click(); await page.waitForTimeout(300); }, 'add ref');
await soft(async () => { await page.getByRole('button', { name: /Analyser le lot/ }).click(); }, 'analyser');
await page.waitForSelector('[data-diligence-noncouvert]', { timeout: 20000 }).catch(() => console.log('WARN NON COUVERT lot absent'));
await page.waitForTimeout(800);
const bNonCouvert = await page.locator('[data-diligence-noncouvert]').count();
const bPeb = await page.locator('[data-diligence-noncouvert]').getByText('Plan d\'Exposition au Bruit').count();
console.log('B · bloc NON COUVERT reporté sur le lot:', bNonCouvert > 0, '| PEB:', bPeb > 0);
await page.screenshot({ path: `${OUT}/B_un_lot_au_crible.png`, fullPage: true });

await b.close();
const ok = aNonCouvert > 0 && aPeb > 0 && bNonCouvert > 0 && bPeb > 0;
console.log(ok ? 'OK — 2 entrées · NON COUVERT sur parcelle ET lot · PEB en non couvert' : 'À VÉRIFIER (voir WARN)');
