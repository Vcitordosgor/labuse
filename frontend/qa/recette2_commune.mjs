import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const LABEL=process.env.LABEL||'apres'
const OUT=`/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
const p=await b.newPage({viewport:{width:1480,height:1400}})
await p.goto(BASE,{waitUntil:'domcontentloaded'})
await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{})
await sleep(1500)
await p.evaluate(()=>window.__labuse.setContexteCommune('Saint-Denis'))
await sleep(7000)
const sel=p.locator('[data-contexte-panel], aside').filter({hasText:'Saint-Denis'}).first()
const el = (await p.locator('[data-contexte-panel]').count().catch(()=>0)) ? p.locator('[data-contexte-panel]').first() : p.locator('aside').last()
await el.screenshot({path:`${OUT}/B_commune_StDenis.png`}).catch(async()=>{await p.screenshot({path:`${OUT}/B_commune_StDenis.png`,fullPage:true})})
console.log('commune captured; panel count', await p.locator('[data-contexte-panel]').count().catch(()=>0))
await b.close()
