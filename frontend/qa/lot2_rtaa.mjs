import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-rangement/lot2/'
mkdirSync(OUT + 'simple', { recursive: true }); mkdirSync(OUT + 'rehab', { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args:['--window-size=1460,1100'] })
for (const [idu, dir] of [['97422000AK0924','simple'],['97415000DI0183','rehab']]) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage(); p.on('pageerror',()=>{})
  await p.goto('http://localhost:5277/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 }).catch(()=>{})
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(()=>0)) await ex.first().click().catch(()=>{})
  await sleep(2000)
  await p.evaluate((i) => window.__labuse.select(i), idu)
  await p.waitForFunction(()=>{const b=document.querySelector('.fiche-v6');const t=b&&b.innerText||'';return b&&!/Chargement de la fiche/.test(t)&&/Risques/.test(t)},{timeout:90000}).catch(()=>{})
  await sleep(1200)
  const l = p.locator('.fiche-v6').getByText('Constructibilité',{exact:false}).first()
  await l.click().catch(()=>{}); await sleep(1500)
  // expand RtaaBlock ("N exigences") + all details
  const rtaaBtn = p.locator('.fiche-v6').getByText(/RTAA DOM|exigences/i).first()
  if (await rtaaBtn.count().catch(()=>0)) { await rtaaBtn.click().catch(()=>{}); await sleep(500) }
  await p.evaluate(()=>{document.querySelector('.fiche-v6').querySelectorAll('details').forEach(e=>e.open=true)})
  const hasRtaa = await p.evaluate(()=>/RTAA DOM/i.test(document.querySelector('.fiche-v6').innerText||''))
  console.log(idu, dir, 'RTAA DOM visible:', hasRtaa)
  await p.evaluate(() => {
    const box=document.querySelector('.fiche-v6'); if(!box) return
    let sc=null,mx=0; box.querySelectorAll('*').forEach(el=>{const d=el.scrollHeight-el.clientHeight; if(d>mx&&/auto|scroll/.test(getComputedStyle(el).overflowY)){mx=d;sc=el}})
    sc=sc||box; let n=sc; while(n&&n!==document.body){n.style.overflow='visible';n.style.maxHeight='none';n.style.height='auto';n.style.flex='none';n.style.position='static';n=n.parentElement}
    sc.style.height=sc.scrollHeight+'px'; box.style.width='400px'
  })
  await sleep(400)
  await p.locator('.fiche-v6').first().screenshot({ path: OUT + dir + '/Constructibilite_rtaa.png' }).catch(()=>{})
  await ctx.close().catch(()=>{})
}
await br.close(); console.log('DONE')
