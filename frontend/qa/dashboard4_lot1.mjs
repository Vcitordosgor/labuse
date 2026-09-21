// DASHBOARD-4 Lot 1 — preuve navigateur du Pilotage v5 : 5 tuiles pleines cliquables + « À faire, dans
// l'ordre » calculée + Journal 3 jours. Vérifie aussi la charte (mauve=IA, rouge=retard) et la navigation.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5335/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1700'] })
const ctx = await br.newContext({ viewport: { width: 1400, height: 1700 } })
const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('PAGEERR', e.message))
await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
// on est sur Pilotage par défaut. Attendre les tuiles.
await p.waitForFunction(() => document.querySelectorAll('[data-tuile]').length >= 5, { timeout: 30000 }).catch(() => {})
// la tuile Tâches lit /admin/circuit (~7 s, 512 Ko) — attendre qu'elle affiche un nombre.
await p.waitForFunction(() => {
  const t = [...document.querySelectorAll('[data-tuile]')].find((b) => b.getAttribute('data-tuile') === 'Tâches à effectuer')
  return t && /\d/.test(t.querySelector('.font-display')?.textContent || '')
}, { timeout: 30000 }).catch(() => {})
await sleep(600)
const info = await p.evaluate(() => {
  const tuiles = [...document.querySelectorAll('[data-tuile]')].map((b) => {
    const cs = getComputedStyle(b)
    return { label: b.getAttribute('data-tuile'), num: (b.querySelector('.font-display')?.textContent || '').trim(), bg: cs.backgroundColor }
  })
  const todos = [...document.querySelectorAll('[data-todo]')].map((d) => ({
    cle: d.getAttribute('data-todo'), tone: d.getAttribute('data-tone'),
    titre: (d.querySelector('.flex-1')?.childNodes[0]?.textContent || '').trim(),
  }))
  const hasStripeChip = (document.body.innerText || '').includes('Stripe daté du')
  const journalTitle = [...document.querySelectorAll('h2')].some((h) => h.textContent.includes('Journal'))
  return { tuiles, todos, hasStripeChip, journalTitle }
})
console.log('=== TUILES (5) ===')
info.tuiles.forEach((t) => console.log(` ${t.label} = ${t.num}  bg=${t.bg}`))
console.log('=== À FAIRE ===')
info.todos.forEach((t) => console.log(` [${t.tone}] ${t.cle} : ${t.titre}`))
console.log('en-tête Stripe présent ?', info.hasStripeChip, '(doit être false)')
console.log('titre Journal présent ?', info.journalTitle)
await p.screenshot({ path: OUT + 'lot1-pilotage-apres.png', fullPage: true })
// navigation : cliquer la tuile IA doit ouvrir la section IA
await p.locator('[data-tuile="Coût IA du mois"]').click().catch(() => {})
await sleep(1000)
const surIA = await p.evaluate(() => (document.body.innerText || '').includes('SURFACE IA'))
console.log('clic tuile IA → section IA ?', surIA)
await br.close(); console.log('DONE')
