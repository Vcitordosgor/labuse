import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
async function commune(){ const p=await b.newPage({viewport:{width:1480,height:1400}})
  await p.goto(BASE,{waitUntil:'domcontentloaded'}); await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{}); await sleep(1500)
  await p.evaluate(()=>window.__labuse.setContexteCommune('Saint-Denis')); await sleep(7000); return p }
const panel = p => p.locator('[data-contexte-panel]').first()
// collapsed (B1 pied absent, B5 sous-titre, B7 chevrons)
{ const p=await commune(); const sc=p.locator('[data-contexte-panel] [class*="overflow-y"]').first(); await sc.evaluate(e=>e.scrollTo(0,99999)).catch(()=>{}); await sleep(800)
  await panel(p).screenshot({path:`${OUT}/B_commune_pied.png`}).catch(()=>{}); await p.close() }
// open tiroirs
for (const [sec,tag] of [['Risques et contraintes','B2_catnat'],['Fiscalité','B3_fiscalite'],['Foncier','B5_foncier'],['Urbanisme','B6_urbanisme']]) {
  const p=await commune(); const btn=p.locator('[data-contexte-panel] button',{hasText:sec}).first()
  if(await btn.count().catch(()=>0)){await btn.scrollIntoViewIfNeeded().catch(()=>{});await btn.click().catch(()=>{});await sleep(1200)}
  await panel(p).screenshot({path:`${OUT}/${tag}.png`}).catch(()=>{}); await p.close()
}
console.log('commune2 done')
await b.close()
