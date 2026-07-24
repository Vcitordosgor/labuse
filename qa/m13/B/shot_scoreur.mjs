import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'
const BASE = 'http://127.0.0.1:8031/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-aac5ea7478102f189/qa/m13/B'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await chromium.launch()
const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage()
p.on('console', (m) => { if (m.type() === 'error') console.log('ERR:', m.text()) })
await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(1500)

// open Outils drawer (Rail)
await p.getByRole('button', { name: 'Outils' }).click()
await sleep(600)
// click « Scorer une adresse »
await p.getByText('Scorer une adresse', { exact: false }).first().click()
await sleep(700)
// type in the scoreur autocomplete
const inp = p.locator('[data-scoreur-adresse]')
await inp.click()
await inp.type('rue leperlier', { delay: 30 })
await sleep(1100)
const info = await p.evaluate(() => {
  const ul = document.querySelector('[role="listbox"]')
  return { opts: document.querySelectorAll('[role="option"]').length, ul: !!ul }
})
console.log('scoreur suggestions:', JSON.stringify(info))
await p.screenshot({ path: `${OUT}/b1_scoreur_suggestions.png` })
await b.close()
