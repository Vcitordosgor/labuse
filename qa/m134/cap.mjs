import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const OUT = new URL('./captures', import.meta.url).pathname; mkdirSync(OUT,{recursive:true});
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1280, height:1000 } });
const soft = async (fn,w)=>{ try{await fn()}catch(e){console.log('⚠',w,String(e).slice(0,110))} };
await page.goto('http://localhost:5173/', { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);
// vue cartes + zoom sur Saint-Denis (QPV + ANRU)
await soft(async()=>{ await page.evaluate(()=>{ window.__labuse.setView('cartes'); window.__labuse.setCommune('Saint-Denis'); }); await page.waitForTimeout(3500); }, 'commune');
// ouvrir le tiroir Couches si fermé
await soft(async()=>{ const open = await page.locator('[data-couches-drawer]').count(); if(!open){ await page.click('[data-couches-toggle]'); await page.waitForTimeout(400);} }, 'couches');
const dispos = [
  ['qpv','QPV — quartier prioritaire'],
  ['tva','TVA réduite primo-accédant (QPV + 500 m)'],
  ['anru','NPNRU / ANRU — renouvellement urbain'],
  ['zfang','zone franche'],   // partial match
  ['frr','France Ruralités'],
];
async function clickLayer(text){ const el = page.locator(`[data-couches-drawer] button:has-text("${text}")`).first(); await el.scrollIntoViewIfNeeded(); await el.click(); await page.waitForTimeout(2200); }
// chaque dispositif SEUL
for (const [tag,txt] of dispos){
  await soft(()=>clickLayer(txt), 'on '+tag);
  await page.screenshot({ path: `${OUT}/dispo-${tag}.png` }); console.log('📸 dispo-'+tag);
  await soft(()=>clickLayer(txt), 'off '+tag);   // re-clic = éteindre
}
// TOUS ensemble
for (const [,txt] of dispos){ await soft(()=>clickLayer(txt), 'all'); }
await page.screenshot({ path: `${OUT}/dispo-tous.png` }); console.log('📸 dispo-tous');
// la légende (coin bas-droit) — zoom
await soft(async()=>{ const lg = await page.locator('[data-legend-dispositifs]').boundingBox(); if(lg) await page.screenshot({ path:`${OUT}/legende.png`, clip:{x:lg.x-8,y:lg.y-8,width:lg.width+16,height:lg.height+16} }); }, 'legende');
console.log('📸 legende');
await b.close();
