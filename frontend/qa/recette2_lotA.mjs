import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/apres'
mkdirSync(OUT, { recursive: true })
const BASE='http://localhost:5905/socle/'; const IDU='97415000AM0097'
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
const b=await chromium.launch({channel:'chrome',headless:true})
async function fiche(){ const p=await b.newPage({viewport:{width:1480,height:1300}})
  await p.goto(`${BASE}#f=1&idu=${IDU}`,{waitUntil:'domcontentloaded'})
  await p.waitForSelector('.fiche-v6',{timeout:20000}).catch(()=>{}); await sleep(9000); return p }
// collapsed fiche
{ const p=await fiche(); await p.locator('.fiche-v6').first().screenshot({path:`${OUT}/A_fiche_AM0097.png`}).catch(()=>{}); await p.close() }
// one tiroir per load
for (const [sec,tag] of [['Bâti','A4_bati'],['Urbanisme','A5_urbanisme'],['Réseaux','A7_reseaux'],['Fiscalité','A8_fiscalite'],['Marché','A9_marche'],['Quartier','A10_quartier']]) {
  const p=await fiche()
  const btn=p.locator('.fiche-v6 button',{hasText:sec}).first()
  if(await btn.count().catch(()=>0)){ await btn.scrollIntoViewIfNeeded().catch(()=>{}); await btn.click().catch(()=>{}); await sleep(1500) }
  await p.locator('.fiche-v6').first().screenshot({path:`${OUT}/${tag}.png`}).catch(()=>{})
  await p.close()
}
console.log('lotA captures done')
await b.close()
