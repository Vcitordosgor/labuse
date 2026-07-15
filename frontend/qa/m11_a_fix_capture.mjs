// M11 surface A — capture du fix rendu Markdown + cohérence zonage sur AS0090 (La Possession).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m11-ia/captures/a-fix-as0090-markdown-zonage.png'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 10000 })
await p.evaluate(() => window.__labuse.select('97408000AS0090'))
await p.waitForSelector('[data-askbar]', { timeout: 10000 })
// pose la question via le chip « Combien je peux construire ? »
await p.locator('[data-askbar] button:has-text("Combien je peux construire")').click()
await p.waitForSelector('[data-askbar] p.whitespace-pre-wrap, [data-askbar] .whitespace-pre-wrap', { timeout: 20000 })
await p.waitForTimeout(600)
// contrôle : aucun marqueur brut ne doit rester dans le texte rendu
const rendered = await p.locator('[data-askbar]').innerText()
const rawMarks = { '##': rendered.includes('##'), '>' : /\n>\s/.test(rendered), '**': rendered.includes('**') }
console.log('marqueurs bruts visibles:', rawMarks)
console.log('zone AUB + AUst présente:', rendered.includes('AUB + AUst'))
await p.locator('[data-askbar]').screenshot({ path: OUT })
console.log('capture:', OUT)
await b.close()
