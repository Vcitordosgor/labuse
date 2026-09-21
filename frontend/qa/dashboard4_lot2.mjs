// DASHBOARD-4 Lot 2 — preuve navigateur de la page Données (Circuit) : D1 compteurs = verrous,
// D2 verrous jouables (Résumé), D5 boutons agents/vérifier hors Résumé, D6 Destinations en bas,
// D7 plafond agents. On joue vraiment les verrous (tâche détachée) et on attend les 30 lignes.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5335/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,2100'] })
const ctx = await br.newContext({ viewport: { width: 1400, height: 2100 } })
const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('PAGEERR', e.message))
await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
await p.evaluate(() => document.querySelector('aside button[data-admin-section="donnees"]')?.click())
// le Circuit charge (~7 s)
await p.waitForFunction(() => (document.body.innerText || '').includes('Les compteurs, tels que les verrous'), { timeout: 30000 }).catch(() => {})
await sleep(1000)
// D1 — la bande des compteurs
const d1 = await p.evaluate(() => {
  const s = document.querySelector('.cc-strip')?.textContent || ''
  return s.replace(/\s+/g, ' ').trim()
})
console.log('D1 compteurs:', d1)
// D5 — sur le Résumé, PAS de boutons agents/vérifier
const d5 = await p.evaluate(() => {
  const onResume = document.querySelector('.tabs button.on')?.textContent || ''
  const actions = !!document.querySelector('.cxp .actions')
  return { onglet: onResume, actionsVisibles: actions }
})
console.log('D5 onglet actif:', d5.onglet, '| boutons actions visibles:', d5.actionsVisibles, '(doit être false sur Résumé)')
// D2 — rejouer les verrous
await p.evaluate(() => {
  const b = [...document.querySelectorAll('.verrous-tete button')].find((x) => /Rejouer les verrous/.test(x.textContent))
  if (b) b.click()
})
console.log('verrous lancés — attente des 30 lignes…')
await p.waitForFunction(() => {
  const t = document.body.innerText || ''
  return /verrous joués|À corriger/.test(t) && document.querySelectorAll('.verrous-bloc details.item').length >= 30
}, { timeout: 120000 }).catch(() => {})
await sleep(800)
const d2 = await p.evaluate(() => {
  const lignes = [...document.querySelectorAll('.verrous-bloc details.item')].map((d) => (d.querySelector('.num')?.textContent || '').trim())
  const has = (id) => lignes.includes(id)
  return { n: lignes.length, six: ['V5d','V5e','V5f','V6a','V7a','G8'].filter(has),
           resume: (document.querySelector('.verrous-bloc .sub')?.textContent || '').trim() }
})
console.log('D2 lignes verrous:', d2.n, '| les 6 ajoutés depuis 9/09 présents:', d2.six.join(','), '|', d2.resume)
await p.screenshot({ path: OUT + 'lot2-donnees-resume-apres.png', fullPage: true }); console.log('capté résumé')
// D5/D7 — onglet Circuit : boutons présents + plafond agents
await p.evaluate(() => { const b=[...document.querySelectorAll('.tabs button')].find(x=>/^Circuit/.test(x.textContent)); if(b)b.click() })
await sleep(1500)
const d7 = await p.evaluate(() => {
  const actions = !!document.querySelector('.cxp .actions')
  const agents = (document.querySelector('.agents-info')?.textContent || '').replace(/\s+/g,' ').trim()
  return { actionsVisibles: actions, agents }
})
console.log('D5 boutons sur Circuit:', d7.actionsVisibles, '(doit être true) | D7 agents:', d7.agents)
await p.screenshot({ path: OUT + 'lot2-donnees-circuit-apres.png', fullPage: true }); console.log('capté circuit')
// D6 — Destinations en bas
await p.evaluate(() => { const b=[...document.querySelectorAll('.tabs button')].find(x=>/Résumé/.test(x.textContent)); if(b)b.click() })
await sleep(500)
const d6 = await p.evaluate(() => {
  const btns = [...document.querySelectorAll('button')].filter(b=>/Destinations PLU/.test(b.textContent))
  return btns.length ? btns[0].textContent.replace(/\s+/g,' ').trim() : 'ABSENT'
})
console.log('D6 entrée Destinations:', d6)
await br.close(); console.log('DONE lot2')
