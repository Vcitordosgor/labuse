import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
const p=await b.newPage({viewport:{width:1440,height:1000}})
await p.goto(BASE,{waitUntil:'domcontentloaded'}); await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{}); await sleep(2000)
const railDocs = await p.getByText('Docs',{exact:true}).count().catch(()=>0)
const railDocuments = await p.getByText('Documents',{exact:true}).count().catch(()=>0)
console.log('rail « Docs »:', railDocs, '| « Documents »:', railDocuments)
await p.screenshot({path:`${OUT}/E1_rail_docs.png`,clip:{x:0,y:0,width:70,height:1000}})
await b.close()
