// DASHBOARD-4 D2 — le résultat persistant des verrous (30 lignes) se REND au chargement du Résumé
// (sans rejouer), avec phrase + état + preuve. Les 6 ajoutés depuis le 9/09 présents ; V1c/G8 cassés.
import { chromium } from 'playwright'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,2400'] })
const p = await (await br.newContext({ viewport:{width:1400,height:2400} })).newPage(); p.on('pageerror',()=>{})
await p.goto('http://localhost:5335/socle/#admin=1',{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1500)
await p.evaluate(()=>document.querySelector('aside button[data-admin-section="donnees"]')?.click())
await p.waitForFunction(()=>document.querySelectorAll('.verrous-bloc details.item').length>=30,{timeout:30000}).catch(()=>{})
await sleep(1000)
const info = await p.evaluate(()=>{
  const lignes=[...document.querySelectorAll('.verrous-bloc details.item')].map(d=>({
    id:(d.querySelector('.num')?.textContent||'').trim(),
    cls:d.className.replace('item','').trim(),
    t:(d.querySelector('.t')?.textContent||'').trim().slice(0,40),
  }))
  const has=id=>lignes.some(l=>l.id===id)
  return { n:lignes.length, six:['V5d','V5e','V5f','V6a','V7a','G8'].filter(has),
    casses:lignes.filter(l=>l.cls.includes('rouge')||l.cls.includes('ambre')).map(l=>l.id),
    resume:(document.querySelector('.verrous-bloc .sub')?.textContent||'').trim() }
})
console.log('D2 lignes:',info.n,'| 6 depuis 9/09:',info.six.join(','),'| non-verts:',info.casses.join(','))
console.log('D2 résumé:',info.resume)
await p.screenshot({ path: OUT+'lot2-donnees-resume-apres.png', fullPage:true }); console.log('capté résumé (30 lignes)')
await br.close()
