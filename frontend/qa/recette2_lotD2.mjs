import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true,args:['--window-size=1440,1000']})
const p=await b.newPage({viewport:{width:1440,height:1000}})
await p.goto(`${BASE}#m=assemblage`,{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse&&!!window.__labuse_map,{timeout:30000}).catch(()=>{}); await sleep(2500)
await p.evaluate(()=>window.__labuse.setMsel(['97416000ET2262','97416000ET2264','97416000ET2266'])); await sleep(3000)
// nombre de features DANS la source GeoJSON dédiée (indépendant du zoom) = garantie « N surlignées »
const srcN=await p.evaluate(()=>{try{const m=window.__labuse_map;const s=m.getSource('module-hl-geo');const d=s&&s._data;return d&&d.features?d.features.length:'na'}catch(e){return 'err:'+String(e.message).slice(0,40)}})
console.log('D4a — features dans module-hl-geo (zoom-indépendant):', srcN)
// cadrer sur les 3 parcelles (close) et screenshot
await p.evaluate(()=>window.__labuse_map.jumpTo({center:[55.4726,-21.3086],zoom:17})); await sleep(2500)
await p.waitForFunction(()=>window.__labuse_map.areTilesLoaded(),{timeout:15000}).catch(()=>{}); await sleep(1200)
const rend=await p.evaluate(()=>{try{return window.__labuse_map.queryRenderedFeatures({layers:['module-hl-geo-line']}).length}catch(e){return 'err'}})
console.log('D4a — rendues (z17):', rend)
await p.screenshot({path:`${OUT}/D4a_assemblage_surlignage.png`})
await b.close()
