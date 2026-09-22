// DASHBOARD-4b Lot 1 — preuve : le détail d'une source montre 7 blocs DISTINCTS (Couches · Sections
// fiche parcelle · Cartes fiche commune · Outils · Documents · Copilote · Radar), jamais « Ailleurs ».
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE='http://localhost:5335/socle/'
const OUT='/Users/openclaw/Desktop/labuse-dash4b/captures/dashboard4b/'
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms))
mkdirSync(OUT,{recursive:true})
const SRC=[{id:5,slug:'dvf',nom:'DVF'},{id:30,slug:'ppr',nom:'PPR/DEAL'},{id:1,slug:'cadastre',nom:'Cadastre'},{id:16,slug:'sitadel',nom:'SITADEL'},{id:83,slug:'cosia',nom:'CoSIA'}]
const BLOCS=['Couches carte alimentées','Sections de la fiche parcelle','Cartes de la fiche commune','Outils','Documents','Copilote','Radar']
const br=await chromium.launch({channel:'chrome',headless:true,args:['--window-size=1500,2000']})
for (const s of SRC){
  const ctx=await br.newContext({viewport:{width:1500,height:2000}})
  const p=await ctx.newPage(); p.on('pageerror',()=>{})
  await p.goto(BASE+'#admin=1',{waitUntil:'domcontentloaded',timeout:60000})
  await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1200)
  await p.evaluate(()=>document.querySelector('aside button[data-admin-section="donnees"]')?.click())
  await p.waitForFunction(()=>(document.body.innerText||'').includes('réservoir')||document.querySelector('.reservoirs,.diagram'),{timeout:30000}).catch(()=>{})
  await sleep(800)
  await p.evaluate((id)=>{location.hash=`#admin=1&cx=reservoir:${id}`;dispatchEvent(new HashChangeEvent('hashchange'))}, s.id)
  await p.waitForFunction(()=>{const t=document.body.innerText||'';return t.includes('Sections de la fiche parcelle')&&t.includes('Copilote')&&t.includes('Radar')},{timeout:30000}).catch(()=>{})
  await sleep(1000)
  const info=await p.evaluate((BLOCS)=>{
    const cards=[...document.querySelectorAll('.detail .card h3')].map(h=>h.textContent||'')
    const present=BLOCS.filter(b=>cards.some(c=>c.startsWith(b)))
    const counts={}
    for(const b of BLOCS){const h=cards.find(c=>c.startsWith(b)); if(h){const m=h.match(/·\s*(\d+)/); counts[b]=m?+m[1]:0}}
    const ailleurs=(document.body.innerText||'').includes('Ailleurs ·')
    return {present,counts,ailleurs}
  }, BLOCS)
  console.log(`\n=== ${s.nom} (réservoir ${s.id}) ===`)
  console.log('  7 blocs présents:', info.present.length, '/', BLOCS.length)
  console.log('  comptes:', JSON.stringify(info.counts))
  console.log('  « Ailleurs » présent ?', info.ailleurs, '(doit être false)')
  await p.screenshot({path:`${OUT}lot1-${s.slug}.png`,fullPage:true})
  await ctx.close()
}
await br.close(); console.log('\nDONE lot1')
