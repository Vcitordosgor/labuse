import { chromium } from 'playwright'
const BASE='http://127.0.0.1:8011/socle/'
const b=await chromium.launch(); const pg=await b.newPage({viewport:{width:1440,height:900}})
await pg.goto(BASE+'#f=1&v=1',{waitUntil:'networkidle',timeout:60000}); await pg.waitForTimeout(2500)
const idus=['97409000BK0245','97411000BE0651','97412000BR0775','97410000AB0343']  // fraîches
const res=[]
for(const idu of idus){
  // vider toute fiche précédente
  await pg.keyboard.press('Escape'); await pg.waitForTimeout(600)
  const t0=Date.now()
  await pg.fill('input[title^="Recherche du dashboard"]', idu)
  await pg.keyboard.press('Enter')
  // attendre le badge verdict de CETTE parcelle (pas l'ancien)
  try{ await pg.waitForFunction(()=>{const el=document.querySelector('[data-badge-verdict]');return el&&el.innerText.trim().length>3},{timeout:15000})
    const tVerdict=Date.now()-t0
    // attendre stabilité réseau (contenu complet)
    await pg.waitForLoadState('networkidle',{timeout:15000})
    const tStable=Date.now()-t0
    res.push({idu, verdict_ms:tVerdict, contenu_complet_ms:tStable})
  }catch(e){ res.push({idu, err:e.message.slice(0,60)}) }
}
console.log(JSON.stringify(res,null,1))
await b.close()
