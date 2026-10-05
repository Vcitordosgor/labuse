import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const LABEL=process.env.LABEL||'apres'
const OUT=`/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true,args:['--window-size=1400,1000']})
const p=await b.newPage({viewport:{width:1400,height:1000}})
await p.goto(BASE,{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse_map,{timeout:60000}).catch(()=>{})
const btn=p.getByText('Explorer la carte',{exact:false}); if(await btn.count().catch(()=>0)) await btn.first().click().catch(()=>{})
await sleep(2000)
await p.waitForFunction(()=>window.__labuse_map.areTilesLoaded(),{timeout:60000}).catch(()=>{})
// vue île
await p.evaluate(()=>window.__labuse_map.jumpTo({center:[55.53,-21.13],zoom:9.4})); await sleep(1500)
// activer 3 couches de la liste C1 : QPV, 50 pas géométriques, BPE (INSEE)
for (const k of ['qpv','cinquante_pas','amenite_bpe']) { await p.evaluate((kind)=>window.__labuse.toggleTuyau(kind), k); await sleep(600) }
await sleep(2500)
await p.waitForFunction(()=>window.__labuse_map.areTilesLoaded(),{timeout:30000}).catch(()=>{})
await sleep(1500)
// compter les features rendues de ces couches à l'île
const counts = await p.evaluate(()=>{
  const m=window.__labuse_map; const out={}
  for (const k of ['qpv','cinquante_pas','amenite_bpe']) {
    try { out[k]=m.queryRenderedFeatures({layers:m.getStyle().layers.filter(l=>l.id.startsWith(`tuyau-${k}-`)||l.id.startsWith(`tuyau-${k}`)).map(l=>l.id)}).length } catch(e){ out[k]='err' }
  }
  return out
})
console.log('features rendues à l île (z9.4):', JSON.stringify(counts))
await p.screenshot({path:`${OUT}/C1_ile_3couches.png`})
await b.close()
