import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT='/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
mkdirSync(OUT,{recursive:true})
const BASE='http://localhost:5905/socle/'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
const PANEL={x:0,y:0,width:560,height:980}
async function open(mod){const p=await b.newPage({viewport:{width:1440,height:1000}})
  await p.goto(`${BASE}#m=${mod}`,{waitUntil:'domcontentloaded',timeout:60000})
  await p.waitForFunction(()=>!!window.__labuse,{timeout:30000}).catch(()=>{}); await sleep(2000); return p}
// D8 — étude de zone : chemin unique (plus de 2 portes, plus de badge/Changer la zone)
{ const p=await open('etude-zone')
  const portes=await p.locator('[data-etude-porte]').count().catch(()=>0)
  const changer=await p.locator('[data-etude-changer-porte]').count().catch(()=>0)
  const badge=await p.locator('[data-etude-porte-active]').count().catch(()=>0)
  console.log('D8 — portes:',portes,'| « Changer la zone »:',changer,'| badge mode:',badge,'(attendu 0/0/0)')
  await p.screenshot({path:`${OUT}/D8_etude_zone_unique.png`,clip:PANEL}); await p.close() }
// D7 — pièges : servitudes ES0981 regroupées (1 carte « Classement sonore »)
{ const p=await open('risques'); await p.evaluate(()=>window.__labuse.select('97416000ES0981')); await sleep(3000)
  const sonore=await p.getByText(/Classement sonore/i).count().catch(()=>0)
  console.log('D7 — cartes « Classement sonore »:',sonore,'(attendu 1)')
  await p.screenshot({path:`${OUT}/D7_pieges_sonore.png`,clip:PANEL}); await p.close() }
// D10 — faisabilité : Réinitialiser présent après sélection
{ const p=await open('programme'); await p.evaluate(()=>window.__labuse.select('97411000BZ1065')); await sleep(3500)
  const reinit=await p.locator('[data-reinitialiser]').count().catch(()=>0)
  console.log('D10 — Réinitialiser Faisabilité:',reinit,'(attendu ≥1)')
  await p.screenshot({path:`${OUT}/D10_faisabilite_reinit.png`,clip:PANEL}); await p.close() }
console.log('done')
await b.close()
