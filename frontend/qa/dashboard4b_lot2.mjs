// DASHBOARD-4b Lot 2 — preuve : le SENS INVERSE, accessible par recherche sur la page Données. On tape
// un outil / une section / une couche → ses sources ; clic sur une source → détail réservoir.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT='/Users/openclaw/Desktop/labuse-dash4b/captures/dashboard4b/'
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms))
mkdirSync(OUT,{recursive:true})
const br=await chromium.launch({channel:'chrome',headless:true,args:['--window-size=1400,1700']})
const p=await (await br.newContext({viewport:{width:1400,height:1700}})).newPage(); p.on('pageerror',(e)=>console.log('ERR',e.message))
await p.goto('http://localhost:5335/socle/#admin=1',{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1500)
await p.evaluate(()=>document.querySelector('aside button[data-admin-section="donnees"]')?.click())
await p.waitForFunction(()=>!!document.querySelector('.cxp .tabs'),{timeout:30000}).catch(()=>{})
await sleep(6000) // le Circuit charge (~7s)
// onglet Circuit
await p.evaluate(()=>{const b=[...document.querySelectorAll('.cxp .tabs button')].find(x=>/^Circuit/.test(x.textContent)); if(b)b.click()})
await p.waitForFunction(()=>!!document.querySelector('.si-input'),{timeout:20000}).catch(()=>{})
await sleep(500)
async function cherche(terme, slug){
  await p.fill('.si-input', terme)
  await p.waitForFunction(()=>document.querySelectorAll('.si-list li').length>0 || (document.querySelector('.sens-inverse')?.innerText||'').includes('aucun élément'),{timeout:8000}).catch(()=>{})
  await sleep(500)
  const info=await p.evaluate(()=>{
    const lis=[...document.querySelectorAll('.si-list li')].map(li=>({
      el:(li.querySelector('.si-el')?.innerText||'').replace(/\n/g,' ').trim(),
      sources:[...li.querySelectorAll('.si-src .chip')].map(c=>c.textContent),
    }))
    return {n:lis.length, first:lis[0]}
  })
  console.log(`\n« ${terme} » → ${info.n} élément(s)`)
  if(info.first) console.log('  ',info.first.el,'← sources:', info.first.sources.slice(0,4).join(' · '))
  await p.screenshot({path:`${OUT}lot2-inverse-${slug}.png`,fullPage:true})
  return info
}
await cherche('Faisabilité','outil')       // un outil
await cherche('Zonage','section')          // une section de fiche / carte
await cherche('Aléa inondation','couche')  // une couche
// clic sur une source du premier résultat → détail réservoir
await p.fill('.si-input','Faisabilité'); await sleep(600)
await p.evaluate(()=>{const c=document.querySelector('.si-list li .si-src .chip'); if(c)c.click()})
await p.waitForFunction(()=>{const t=document.body.innerText||''; return t.includes('Dans le réservoir')||t.includes('Couches carte alimentées')},{timeout:15000}).catch(()=>{})
await sleep(800)
const ouvert=await p.evaluate(()=>{const t=document.body.innerText||''; return t.includes('Dans le réservoir')||t.includes('Couches carte alimentées')})
console.log('\nclic source → détail réservoir ouvert ?', ouvert)
await p.screenshot({path:`${OUT}lot2-clic-source.png`,fullPage:true})
await br.close(); console.log('\nDONE lot2')
