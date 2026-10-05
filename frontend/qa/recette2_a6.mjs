import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const LABEL=process.env.LABEL||'apres'
const OUT=`/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'; const IDU='97415000AM0097'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
const p=await b.newPage({viewport:{width:1480,height:1300}})
await p.goto(`${BASE}#f=1&idu=${IDU}`,{waitUntil:'domcontentloaded'})
await p.waitForSelector('.fiche-v6',{timeout:20000}).catch(()=>{}); await sleep(8000)
const btn=p.locator('.fiche-v6 button',{hasText:'Risques'}).first()
if(await btn.count().catch(()=>0)){await btn.scrollIntoViewIfNeeded().catch(()=>{});await btn.click().catch(()=>{});await sleep(1500)}
const body=await p.locator('.fiche-v6').first().innerText().catch(()=>'')
const penteLine=body.split('\n').filter(l=>/pente/i.test(l)).join(' | ')
console.log('PENTE vigilance:', penteLine.slice(0,200))
console.log('contient 56:', /56/.test(body), '| contient tres_fort:', /tres_fort/.test(body), '| contient 19,1:', /19,1/.test(body))
await p.locator('.fiche-v6').first().screenshot({path:`${OUT}/A6_risques_pente.png`}).catch(()=>{})
await b.close()
