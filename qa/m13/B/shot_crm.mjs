import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'
const BASE = 'http://127.0.0.1:8031/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-aac5ea7478102f189/qa/m13/B'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await chromium.launch()
const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage()
p.on('console', (m) => { if (m.type() === 'error') console.log('ERR:', m.text()) })
await p.goto(BASE, { waitUntil: 'networkidle' }); await sleep(1200)

// go to CRM
await p.getByRole('button', { name: 'CRM' }).click()
await sleep(1200)

// enter edit mode
await p.getByRole('button', { name: 'Personnaliser' }).click()
await sleep(500)

// ── ADD a column (inline, no window.prompt) ──
await p.getByRole('button', { name: '+ Colonne' }).click()
await sleep(300)
const addInput = p.getByPlaceholder('Nom de la colonne…')
const colName = 'À relancer ' + Math.floor(Math.random() * 1000)
await addInput.fill(colName)
await sleep(300)
await p.screenshot({ path: `${OUT}/b3_ajout_saisie.png` })
await addInput.press('Enter')
await sleep(1200)
// the new column should now appear
const appears = await p.evaluate((n) => document.body.innerText.includes(n), colName)
console.log('added column visible:', appears, '(', colName, ')')
await p.screenshot({ path: `${OUT}/b3_ajout.png` })

// ── RENAME the new column: click its label (edit mode makes it a text button) ──
// find the new column header button and click to rename
await p.getByRole('button', { name: colName }).first().click()
await sleep(400)
const renameInput = p.getByLabel('Renommer la colonne')
const renamed = colName + ' (renom)'
await renameInput.fill(renamed)
await sleep(300)
await p.screenshot({ path: `${OUT}/b3_renommage.png` })
await renameInput.press('Enter')
await sleep(1200)
const renameOk = await p.evaluate((n) => document.body.innerText.includes(n), renamed)
console.log('rename visible:', renameOk)

// ── MOVE the column left (← button) ──
// screenshot the edit controls (arrows + delete) as move proof
await p.screenshot({ path: `${OUT}/b3_deplacement_avant.png` })
// click the ← on the renamed column
const colHeader = p.locator('div', { hasText: renamed }).last()
// find left-arrow buttons; click the one belonging to the renamed column via aria-label proximity
// simpler: capture order before/after by clicking a left arrow near the renamed col
const beforeOrder = await p.$$eval('[title="Cliquer pour renommer"]', (els) => els.map((e) => e.textContent))
console.log('order before move:', JSON.stringify(beforeOrder))
// click the last visible « Déplacer la colonne à gauche »
const leftBtns = await p.$$('[aria-label="Déplacer la colonne à gauche"]')
if (leftBtns.length) { await leftBtns[leftBtns.length - 1].click(); await sleep(1200) }
const afterOrder = await p.$$eval('[title="Cliquer pour renommer"]', (els) => els.map((e) => e.textContent))
console.log('order after move:', JSON.stringify(afterOrder))
await p.screenshot({ path: `${OUT}/b3_deplacement.png` })

// ── DELETE a POPULATED column → destination dropdown ──
// delete « Contact à préparer » (21 cards) to force the move-to dropdown
const delBtns = await p.$$('[aria-label="Supprimer la colonne"]')
// find index of « Contact à préparer »
const labels = await p.$$eval('[title="Cliquer pour renommer"]', (els) => els.map((e) => e.textContent))
let idx = labels.findIndex((l) => l && l.includes('Contact à préparer'))
if (idx < 0) idx = 2
await delBtns[idx].click()
await sleep(600)
await p.screenshot({ path: `${OUT}/b3_suppression_destination.png` })
const hasSelect = await p.evaluate(() => {
  const sel = document.querySelector('select')
  return sel ? { options: Array.from(sel.options).map((o) => o.textContent) } : null
})
console.log('delete dialog destination select:', JSON.stringify(hasSelect))

await b.close()
