import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-audit/rehabilitation/'
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args:['--window-size=1460,1100'] })
const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
const p = await ctx.newPage()
await p.goto('http://localhost:5277/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 }).catch(()=>{})
const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(()=>0)) await ex.first().click().catch(()=>{})
await sleep(2000)
await p.evaluate(() => window.__labuse.select('97415000DI0183'))
await p.waitForFunction(()=>{const b=document.querySelector('.fiche-v6');const t=b&&b.innerText||'';return b&&!/Chargement de la fiche/.test(t)&&/Risques et protections/.test(t)},{timeout:90000}).catch(()=>{})
await sleep(1200)
const cta = p.locator('.fiche-v6').getByText(/Demander à LABUSE|analyser la parcelle/i).first()
if (await cta.count().catch(()=>0)){await cta.click().catch(()=>{}); await sleep(1500)}
const loc = p.locator('.fiche-v6').getByText('Réhabilitation',{exact:false}).first()
console.log('Rehab present:', await loc.count().catch(()=>0))
await loc.scrollIntoViewIfNeeded().catch(()=>{})
await loc.click({timeout:5000}).catch(()=>{})
await sleep(800)
await p.evaluate(()=>{document.querySelector('.fiche-v6').querySelectorAll('details').forEach(e=>e.open=true)})
await sleep(400)
await p.evaluate(() => {
  const box=document.querySelector('.fiche-v6'); if(!box) return
  let sc=null,mx=0
  box.querySelectorAll('*').forEach(el=>{const d=el.scrollHeight-el.clientHeight; if(d>mx&&/auto|scroll/.test(getComputedStyle(el).overflowY)){mx=d;sc=el}})
  sc=sc||box; let n=sc
  while(n&&n!==document.body){n.style.overflow='visible';n.style.maxHeight='none';n.style.height='auto';n.style.flex='none';n.style.position='static';n=n.parentElement}
  sc.style.height=sc.scrollHeight+'px'; box.style.width='400px'
})
await sleep(400)
await p.locator('.fiche-v6').first().screenshot({ path: OUT + '04_Rehabilitation_97415000DI0183.png' })
console.log('captured')
await ctx.close(); await br.close()
