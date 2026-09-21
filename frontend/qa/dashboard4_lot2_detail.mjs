import { chromium } from 'playwright'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1900'] })
const p = await (await br.newContext({ viewport:{width:1400,height:1900} })).newPage(); p.on('pageerror',()=>{})
await p.goto('http://localhost:5335/socle/#admin=1',{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1500)
await p.evaluate(()=>document.querySelector('aside button[data-admin-section="donnees"]')?.click())
await p.waitForFunction(()=>(document.body.innerText||'').includes('Les compteurs, tels que les verrous'),{timeout:30000}).catch(()=>{}); await sleep(1200)
await p.evaluate(()=>{ location.hash='#admin=1&cx=reservoir:17'; dispatchEvent(new HashChangeEvent('hashchange')) })
await p.waitForFunction(()=>{const t=document.body.innerText||''; return t.includes('Dans le réservoir')||t.includes('Couches carte')},{timeout:30000}).catch(()=>{}); await sleep(1500)
const info = await p.evaluate(()=>{
  const t = document.body.innerText||''
  return {
    dates: ['Dans le réservoir','Chez le producteur','Dernier contrôle'].filter(x=>t.includes(x)),
    blocs: ['Couches carte','fiche parcelle','Ailleurs'].filter(x=>t.includes(x)),
    mode: /sonde|agent|manuel|interne/i.test(t),
  }
})
console.log('D4 dates présentes:', info.dates.join(' | '))
console.log('D3 blocs alimente:', info.blocs.join(' | '))
console.log('D4 mode (sonde/agent/manuel/interne):', info.mode)
await p.screenshot({ path: OUT+'lot2-reservoir-detail-apres.png', fullPage:true }); console.log('capté detail réservoir')
await br.close()
