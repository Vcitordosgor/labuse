// AUDIT M6 §1.6 — étape 2quater : toolbar carte restante (LECTURE SEULE).
// Overlay systématiquement refermé AVANT chaque action ; diff pixel du canvas.
// Usage : cd frontend && node qa/audit_m6_boutons4.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })
const CLIP = { x: 320, y: 60, width: 1080, height: 800 }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)) })
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || u === '/events?limit=100' || /dark_nolabels|wmts|cartocdn/.test(u)) return
  net.push({ url: u.slice(0, 200), status: r.status() })
})
const results = []
async function clean() {
  // referme tout popover par son overlay, autant de fois que nécessaire
  for (let i = 0; i < 3; i++) {
    const ov = page.locator('div.fixed.inset-0')
    if (!(await ov.count())) break
    await ov.last().click({ position: { x: 500, y: 500 }, force: true })
    await page.waitForTimeout(400)
  }
}
const mapShot = () => page.screenshot({ clip: CLIP })

async function act(label, attendu, fn, { shot = null, wait = 2600 } = {}) {
  await clean()
  net = []; errs = []
  const before = await mapShot()
  let clickErr = null
  try { await fn() } catch (e) { clickErr = e.message.slice(0, 110) }
  await page.waitForTimeout(wait)
  const px = !(await mapShot()).equals(before)
  const bad = net.filter((n) => n.status >= 400)
  let statut = 'OK'
  if (clickErr) statut = 'CASSÉ (clic: ' + clickErr + ')'
  else if (bad.length) statut = 'CASSÉ'
  else if (!px && net.length === 0) statut = 'MORT?'
  results.push({ label, attendu, statut, px, net: net.slice(0, 5), errs: errs.slice(0, 2) })
  console.log(`[${statut}] ${label} — px:${px} net:${net.length}`)
  for (const n of net.slice(0, 4)) console.log('   ', n.status, n.url)
  if (shot) await page.screenshot({ path: `${OUT}/${shot}` })
}

await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3500)

await act('Basemap Ortho IGN', 'fond ortho', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(700)
  await page.locator('button:has-text("Ortho IGN")').click()
}, { wait: 3500 })
await act('Ortho "1950-1965"', 'ortho historique 1950', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(700)
  await page.locator('button:has-text("1950-1965")').click()
}, { shot: 'btn-ortho-1950.png', wait: 4000 })
await act('Retour "Sombre (Carto)"', 'fond sombre', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(700)
  await page.locator('button:has-text("Sombre (Carto)")').last().click()
}, { wait: 3200 })
await act('"3D" on', 'relief MNT', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { shot: 'btn-3d.png', wait: 3500 })
await act('"3D" off', 'plat', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { wait: 2800 })

const mapC = { x: 800, y: 450 }
await act('Outil Distance', 'trace + mesure', async () => {
  await page.locator('button[title^="Distance"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(400)
  await page.mouse.click(mapC.x + 80, mapC.y + 40); await page.waitForTimeout(400)
  await page.mouse.dblclick(mapC.x + 80, mapC.y + 40)
}, { shot: 'btn-mesure-distance.png' })
await page.keyboard.press('Escape'); await page.waitForTimeout(600)
await act('Outil Surface', 'polygone + m²', async () => {
  await page.locator('button[title^="Surface"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 90, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 50, mapC.y + 70); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x + 50, mapC.y + 70)
}, { shot: 'btn-mesure-surface.png' })
await page.keyboard.press('Escape'); await page.waitForTimeout(600)
await act('Outil Altitude', 'altitude RGE ALTI au point', async () => {
  await page.locator('button[title^="Altitude"]').click()
  await page.mouse.click(mapC.x, mapC.y)
}, { shot: 'btn-altitude.png', wait: 3200 })
await page.keyboard.press('Escape'); await page.waitForTimeout(600)
await act('Outil Zone', 'polygone filtre les résultats', async () => {
  await page.locator('button[title^="Zone"]').click()
  await page.mouse.click(mapC.x - 100, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y + 90); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x - 100, mapC.y + 90)
}, { shot: 'btn-zone-filtre.png', wait: 3400 })
const zoneBadge = await page.locator('button:has-text("Zone active")').count()
console.log('badge "Zone active" présent :', zoneBadge)
await act('"Zone active ×"', 'retire le filtre', async () => { await page.locator('button:has-text("Zone active")').click() }, { wait: 2400 })

// « Tout voir » : compter les cartes AVANT/APRÈS (le sig 4000 chars ne le voyait pas)
const nCards = () => page.locator('aside button').filter({ hasText: /m² ·/ }).count()
const avant = await nCards()
await page.locator('button:has-text("Tout voir")').click()
await page.waitForTimeout(3500)
const apres = await nCards()
results.push({ label: '"Tout voir →" (recompte)', attendu: 'plus de cartes listées', statut: apres > avant ? 'OK' : 'MORT', avant, apres })
console.log(`Tout voir : ${avant} → ${apres} cartes`)

// chip "Tout" après Écartées (recompte)
await page.locator('aside button:has-text("Écartées")').first().click(); await page.waitForTimeout(2600)
const ecartees1 = await page.locator('aside button').filter({ hasText: /Écartée ·/ }).count()
await page.locator('aside button').filter({ hasText: /^Tout[\s\d]/ }).first().click(); await page.waitForTimeout(2600)
const toutTxt = await page.evaluate(() => (document.querySelector('aside')?.innerText.match(/\d[\d\s  ]*visibles[^\n]*/) || ['?'])[0])
results.push({ label: 'Chip "Tout" (recompte)', attendu: 'retour au périmètre complet', statut: 'voir compte', ecartees_listees: ecartees1, apres_tout: toutTxt })
console.log('chip Écartées → cartes badge "Écartée":', ecartees1, '; après Tout :', toutTxt)

writeFileSync('../reports/m6-audit/boutons-cartes4.json', JSON.stringify(results, null, 1))
console.log(`\n${results.length} actions (part 4)`)
await browser.close()
