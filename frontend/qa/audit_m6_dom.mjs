// AUDIT M6 §1.6 — étape 1 : ÉNUMÉRATION DOM (lecture seule).
// Parcourt les écrans via le rail de navigation et dumpe tous les éléments
// interactifs visibles (boutons, liens, toggles, selects, inputs) + capture.
// Usage : cd frontend && node qa/audit_m6_dom.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)) })
page.on('pageerror', (e) => errors.push('PAGEERROR ' + String(e).slice(0, 200)))

async function dump(label) {
  return await page.evaluate((label) => {
    const els = [...document.querySelectorAll('button, a, [role="button"], [role="tab"], select, input, textarea, summary')]
    return els.filter((el) => {
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0
    }).map((el) => ({
      screen: label,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || undefined,
      text: (el.innerText || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 90),
      title: el.getAttribute('title') || undefined,
      aria: el.getAttribute('aria-label') || undefined,
      placeholder: el.getAttribute('placeholder') || undefined,
      disabled: el.disabled || undefined,
      cls: (el.className || '').toString().slice(0, 60),
      rect: (() => { const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] })(),
    }))
  }, label)
}

const inventory = []
async function snap(name) {
  await page.screenshot({ path: `${OUT}/dom-${name}.png` })
  const d = await dump(name)
  inventory.push(...d)
  console.log(`── ${name}: ${d.length} éléments interactifs — hash=${await page.evaluate(() => location.hash)}`)
}

// 1. accueil mode commune
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(4000)
await snap('accueil-commune')

// 2. rail : énumérer les boutons du rail (colonne la plus à gauche, x < 60)
const railBtns = await page.evaluate(() => {
  return [...document.querySelectorAll('button, a, [role="button"]')]
    .filter((el) => { const r = el.getBoundingClientRect(); return r.x < 60 && r.width > 0 })
    .map((el) => ({ text: (el.innerText || '').trim().slice(0, 40), title: el.getAttribute('title') || el.getAttribute('aria-label') || '' }))
})
console.log('RAIL:', JSON.stringify(railBtns, null, 1))

// 3. cliquer chaque item du rail (par title) et dumper l'écran
for (const b of railBtns) {
  const sel = b.title ? `[title="${b.title}"]` : null
  if (!sel) continue
  try {
    await page.locator(sel).first().click()
    await page.waitForTimeout(2500)
    await snap('rail-' + b.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30))
  } catch (e) { console.log('rail KO', b.title, e.message.slice(0, 80)) }
}

// 4. retour accueil, popover filtres du header (bouton avec "filtre" dans title/texte)
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle' })
await page.waitForTimeout(3000)
const filterBtn = page.locator('header button, button').filter({ hasText: /filtre/i }).first()
try {
  await filterBtn.click(); await page.waitForTimeout(800)
  await snap('popover-filtres')
  await page.keyboard.press('Escape')
} catch (e) { console.log('popover filtres KO', e.message.slice(0, 80)) }

// 5. fiche parcelle : cliquer la 1re carte de résultat dans le panneau gauche
try {
  const card = page.locator('aside [class*="cursor-pointer"], aside li, aside article').first()
  await card.click(); await page.waitForTimeout(3000)
  await snap('fiche-parcelle')
  // dérouler la fiche (scroll) et dumper le bas
  await page.evaluate(() => { const f = document.querySelector('[class*="overflow-y"]'); })
} catch (e) { console.log('fiche KO', e.message.slice(0, 80)) }

writeFileSync('../reports/m6-audit/dom-inventory.json', JSON.stringify({ railBtns, inventory, errors }, null, 1))
console.log(`\nTOTAL éléments: ${inventory.length} ; erreurs console: ${errors.length}`)
for (const e of errors.slice(0, 10)) console.log('  ERR', e)
await browser.close()
