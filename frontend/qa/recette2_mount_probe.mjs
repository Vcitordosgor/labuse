// RECETTE-2 — sonde de montage : chaque deep-link #m=<clé> monte-t-il sans erreur console ?
import { chromium } from 'playwright'
const BASE = 'http://localhost:5905/socle/'
const KEYS = ['plu','permis','communes','patrimoine','assemblage','comparer','risques','etude-zone','temps','programme','gabarit','taxe-amenagement','prospection-solaire','blocs-fonciers','successions','courriers','calculette-fonciere','mon-secteur']
const b = await chromium.launch({ channel: 'chrome', headless: true })
const sleep = (ms) => new Promise(r => setTimeout(r, ms))
for (const k of KEYS) {
  const errs = []
  const p = await b.newPage({ viewport: { width: 1440, height: 980 } })
  p.on('pageerror', (e) => errs.push(String(e).split('\n')[0]))
  await p.goto(`${BASE}#m=${k}`, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {})
  await p.waitForFunction(() => !!window.__labuse, { timeout: 20000 }).catch(() => {})
  await sleep(1200)
  const hasPanel = await p.locator('[data-entree-parcelle], [data-module-panel], main, aside').count().catch(() => 0)
  const title = await p.locator('h1,h2,h3').first().innerText().catch(() => '?')
  console.log(`${k.padEnd(20)} mount=${hasPanel>0?'ok':'??'} err=${errs.length} ${errs[0]||''} | ${title.replace(/\n/g,' ').slice(0,40)}`)
  await p.close()
}
await b.close()
