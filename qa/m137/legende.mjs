import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 } });
const soft = async (fn,w)=>{ try{await fn()}catch(e){console.log('⚠',w,String(e).slice(0,120))} };
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(3000);
await soft(async()=>{ await page.click('[data-filtres-toggle]'); await page.waitForTimeout(700); }, 'open');
await soft(async()=>{ await page.click('[data-analyser-btn]', {force:true}); await page.waitForTimeout(8000); }, 'analyser');
await soft(async()=>{ await page.click('[data-voir-parcelles]'); await page.waitForTimeout(3500); }, 'voir parcelles');
console.log('scoring-open =', await page.locator('[data-scoring-open]').count());
if(await page.locator('[data-scoring-open]').count()){
  await page.locator('[data-scoring-open]').scrollIntoViewIfNeeded();
  await page.click('[data-scoring-open]'); await page.waitForSelector('[data-modale]'); await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/3_legende_paliers.png` });
  const box = await page.locator('[data-modale]').first().boundingBox().catch(()=>null);
  if (box) await page.screenshot({ path: `${OUT}/3b_legende_zoom.png`, clip:{ x:Math.max(0,box.x-4), y:Math.max(0,box.y-4), width:Math.min(box.width+8,780), height:Math.min(box.height+8,780) } });
  console.log('--- LÉGENDE « i » DES PALIERS ---\n'+await page.locator('[data-modale]').innerText());
} else { await page.screenshot({ path: `${OUT}/_debug5.png` }); }
await b.close();
