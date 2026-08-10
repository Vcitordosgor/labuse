import { mkdirSync } from 'node:fs'; import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse/reports/m55-e-equipements'; mkdirSync(OUT,{recursive:true})
const LABEL=process.env.LABEL||'apres'
const b=await chromium.launch({channel:'chrome'})
const p=await b.newPage({viewport:{width:1440,height:900}})
await p.goto('http://localhost:5173/socle/',{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2000)
await p.locator('button:has(span:text-is("Équipements"))').first().click(); await p.waitForTimeout(500)
// centre dense EST de Saint-Denis (île mode — le cas du constat)
await p.evaluate(()=>window.__labuse_map.jumpTo({center:[55.455,-20.882],zoom:14.5}))
await p.waitForTimeout(3500)
const n=await p.evaluate(()=>window.__labuse_map.queryRenderedFeatures({layers:['ov-equip']}).length)
console.log(`${LABEL}: équipements rendus SD centre-est =`, n)
await p.screenshot({path:`${OUT}/sd_centre_${LABEL}.png`, clip:{x:300,y:0,width:1140,height:900}})
await b.close()
