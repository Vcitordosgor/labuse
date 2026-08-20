import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const IDU = '97411000IO0091';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
page.on('response', r => { const u=r.url(); if (u.includes('/parcels/')) console.log('RESP', r.status(), u.slice(-70)); });
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);
// vrai chemin : la barre de recherche du header
const sb = page.locator('input[placeholder*="IDU"], input[placeholder*="Rechercher"]').first();
await sb.click(); await sb.fill(IDU); await page.waitForTimeout(1200);
await page.keyboard.press('Enter'); await page.waitForTimeout(1500);
// cliquer 1er résultat s'il y a une liste
await page.locator(`text=${IDU}`).first().click().catch(()=>{});
await page.waitForTimeout(10000);
const still = await page.locator('text=Chargement de la fiche').count();
console.log('encore en chargement:', still);
await page.screenshot({ path: `${OUT}/03-fiche-parcelle.png` });
console.log('shot 03');
await browser.close();
