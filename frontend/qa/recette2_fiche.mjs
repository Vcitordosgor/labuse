import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const LABEL = process.env.LABEL || 'apres'
const OUT = `/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5905/socle/'
const sleep = ms => new Promise(r => setTimeout(r, ms))
const b = await chromium.launch({ channel: 'chrome', headless: true })
async function fiche(idu, tag, opts={}) {
  const p = await b.newPage({ viewport: { width: 1480, height: 1300 } })
  const errs = []; p.on('pageerror', e => errs.push(String(e).split('\n')[0]))
  await p.goto(`${BASE}#f=1&idu=${idu}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 30000 }).catch(()=>{})
  await p.waitForSelector('.fiche-v6', { timeout: 20000 }).catch(()=>{})
  await sleep(4500)
  if (opts.openAll) { // ouvre tous les tiroirs (accordéons) pour voir le contenu
    const toggles = await p.locator('.fiche-v6 [class*="tiroir"] > button, .fiche-v6 button[aria-expanded]').all().catch(()=>[])
    for (const t of toggles) { await t.click().catch(()=>{}); await sleep(120) }
    await sleep(800)
  }
  const el = p.locator('.fiche-v6').first()
  await el.screenshot({ path: `${OUT}/${tag}.png` }).catch(async()=>{ await p.screenshot({path:`${OUT}/${tag}.png`, clip:{x:1040,y:56,width:420,height:1240}}) })
  console.log(`${tag} ${idu} err=${errs.length} ${errs[0]||''}`)
  await p.close()
}
await fiche('97415000AM0097', 'A_fiche_AM0097')
await fiche('97411000BZ1065', 'A_fiche_BZ1065')
await b.close()
