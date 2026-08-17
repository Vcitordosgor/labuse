// M102-B2 — capture du FIL multi-tours complet (demandé / compris / répondu, champ de réponse
// dans le fil). Usage : BASE=http://localhost:5173/ node qa/m102/captures_fil.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}-fil`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.click('button:has-text("IA")');
await page.waitForSelector('[data-accueil-envoyer]');
await page.fill('textarea', "j'aimerais créer un projet immobilier");
await page.click('[data-accueil-envoyer]');
await page.waitForSelector('[data-fil-reponse]');
await page.screenshot({ path: `${OUT}/01-question-et-champ-reponse.png` });
console.log('📸 01 — la question du Copilote a SON champ de réponse dans le fil');
await page.fill('[data-fil-reponse] input', '15 logements à Saint-Paul');
await page.click('[data-fil-envoyer]');
await page.waitForSelector('[data-fil] [data-reponse] >> nth=1', { timeout: 30000 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/02-fil-complet.png` });
const compris = await page.$$eval('[data-compris]', (els) => els.map((e) => e.textContent?.slice(0, 80)));
console.log('📸 02 — fil complet (2 tours) ; lignes « compris » :', JSON.stringify(compris));
await browser.close();
console.log(`Captures : ${OUT}`);
