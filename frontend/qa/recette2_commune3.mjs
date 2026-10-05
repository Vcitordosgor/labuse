import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
async function commune(){ const p=await b.newPage({viewport:{width:1480,height:1500}})
  await p.goto(BASE,{waitUntil:'domcontentloaded'}); await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{}); await sleep(1500)
  await p.evaluate(()=>window.__labuse.setContexteCommune('Saint-Denis')); await sleep(7000); return p }
for (const [id,tag] of [['risques','B2_catnat'],['fiscalite','B3_fiscalite'],['foncier','B5_foncier']]) {
  const p=await commune(); const s=p.locator(`[data-ligne-carte="${id}"]`).first()
  if(await s.count().catch(()=>0)){await s.scrollIntoViewIfNeeded().catch(()=>{});await s.click().catch(()=>{});await sleep(1200);await s.scrollIntoViewIfNeeded().catch(()=>{})}
  await p.locator('[data-contexte-panel]').first().screenshot({path:`${OUT}/${tag}.png`}).catch(()=>{})
  await p.close()
}
console.log('done')
await b.close()
