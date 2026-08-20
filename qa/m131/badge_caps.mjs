import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 } });
const soft = async (fn,w)=>{ try{await fn()}catch(e){console.log('⚠',w,String(e).slice(0,120))} };
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);

// ── LISTE : analyse LABUSE → liste classée avec badges état du bien ──
await soft(async()=>{ await page.click('[data-filtres-toggle]'); await page.waitForSelector('[data-filtres-drawer]'); await page.waitForTimeout(400);
  await page.click('[data-analyser-btn]'); await page.waitForTimeout(4500);
  await page.click('text=Voir les parcelles').catch(()=>{}); await page.waitForTimeout(4000); }, 'analyse LABUSE');
await page.screenshot({ path: `${OUT}/01-liste-badges.png` });
console.log('📸 01-liste-badges');
// zoom sur une carte de résultat (badge lisible)
await soft(async()=>{ const c=page.locator('[data-tier-chip]').first(); await c.scrollIntoViewIfNeeded(); }, 'scroll');
const card = await page.locator('button:has([data-tier-chip])').first().boundingBox().catch(()=>null);
if (card) await page.screenshot({ path: `${OUT}/01b-liste-carte-zoom.png`, clip:{ x:0, y:Math.max(60,card.y-10), width:430, height:320 } });
console.log('📸 01b-liste-carte-zoom');

// ── KANBAN : projet 24 avec badges ──
await soft(async()=>{ await page.click('[title="Projets"]'); await page.waitForSelector('[data-projets-liste]'); await page.waitForTimeout(500);
  await page.click('text=/VOIR LES \\d+ AUTRES/').catch(()=>{}); await page.waitForTimeout(400);
  await page.locator('text=Démo — 40 logements').first().click(); await page.waitForSelector('[data-projet-kanban]'); await page.waitForTimeout(1200); }, 'kanban 24');
await page.screenshot({ path: `${OUT}/02-kanban-badges.png` });
console.log('📸 02-kanban-badges');
await b.close();
