import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true,args:['--window-size=1440,1000']})
const tryClick=async(p,sel)=>{try{await p.click(sel,{timeout:6000})}catch{}}
async function open(mod){const p=await b.newPage({viewport:{width:1440,height:1000}})
  await p.goto(`${BASE}#m=${mod}`,{waitUntil:'domcontentloaded',timeout:60000})
  await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{}); await sleep(2000); return p}
// D14a — piscines : goutte sur la carte (pas de parcelle teintée)
{ const p=await open('prospection-solaire')
  await tryClick(p,'[data-solaire-mode="piscines"]'); await sleep(1500)
  await tryClick(p,'[data-piscines-perim="Saint-Paul"]'); await sleep(1000)   // périmètre commune (moins de points)
  await tryClick(p,'[data-piscines-statut="servie"]'); await sleep(3500)
  await p.waitForFunction(()=>window.__labuse_map && window.__labuse_map.areTilesLoaded(),{timeout:30000}).catch(()=>{})
  await sleep(2000)
  // compter les features goutte rendues
  const n=await p.evaluate(()=>{try{const m=window.__labuse_map;return m.queryRenderedFeatures({layers:['module-piscine']}).length}catch(e){return 'err:'+e.message}})
  const tinted=await p.evaluate(()=>{try{const m=window.__labuse_map;return m.queryRenderedFeatures({layers:['module-piscine-fill']}).length}catch(e){return 'na'}})
  console.log('D14a gouttes rendues:',n,'| parcelles teintées:',tinted)
  await p.screenshot({path:`${OUT}/D14_piscines_gouttes.png`})
  await p.close() }
// D2a — permis : « Tous » par défaut
{ const p=await open('permis'); await sleep(2500)
  await p.screenshot({path:`${OUT}/D2_permis_tous.png`,clip:{x:0,y:0,width:560,height:1000}})
  await p.close() }
console.log('lotD captures done')
await b.close()
