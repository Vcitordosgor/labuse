// M13 LOT A — preuve visuelle : filtre « Procédure collective » (corrigé, sans radiation) +
// fiche d'un résultat montrant réellement la procédure. app servie sur :8020/socle/.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8020/socle/';
const OUT = new URL('./A', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(20000);
const errs = []; p.on('pageerror', e => errs.push(String(e).slice(0, 120)));

// 1) état filtré via deep-link (verdict allumé + filtre pcl) — fiable et reproductible
await p.goto(`${BASE}#f=1&vs=pcl&v=1`, { waitUntil: 'networkidle' });
await p.waitForTimeout(3000);
const nCards = await p.locator('[data-results-scroll] > button').count();
await p.screenshot({ path: `${OUT}/01_resultats_procedure_collective.png` });

// 2) ouvrir le popover filtre pour montrer « Procédure collective » coché
await p.getByText('+ Filtre').first().click(); await p.waitForTimeout(700);
await p.screenshot({ path: `${OUT}/02_panneau_filtre.png` });
await p.mouse.click(1200, 500); await p.waitForTimeout(800);

// 3) ouvrir la fiche d'un résultat (evaluate-click : contourne l'overlay carte en headless)
await p.locator('[data-results-scroll] > button').first().evaluate(el => el.click());
await p.waitForTimeout(2500);
// amener la mention procédure à l'écran
await p.getByText(/Liquidation|Redressement|Sauvegarde/i).first()
  .scrollIntoViewIfNeeded().catch(() => {});
await p.waitForTimeout(600);
await p.screenshot({ path: `${OUT}/03_fiche_montre_procedure.png` });

const body = await p.locator('body').innerText();
const hasProc = /liquidation|redressement|sauvegarde/i.test(body);
console.log('cards pcl:', nCards, '| pageerrors:', errs.length);
console.log('fiche du résultat montre une procédure:', hasProc);
await b.close();
