// AUDIT M6 §1.6 — étape 2ter : boutons restants (LECTURE SEULE).
// Correctif harnais : chaque popover ouvert est refermé par clic sur son overlay
// (compClick sur .fixed.inset-0) ; les actions carte sont jugées au diff pixel du canvas.
// Usage : cd frontend && node qa/audit_m6_boutons3.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })
const CLIP = { x: 320, y: 60, width: 1080, height: 800 }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })
page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)))
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || u === '/events?limit=100') return
  net.push({ url: u.slice(0, 200), status: r.status() })
})
const results = []
const closeOverlay = async () => {
  const ov = page.locator('div.fixed.inset-0')
  if (await ov.count()) { await ov.last().click({ position: { x: 400, y: 500 }, force: true }); await page.waitForTimeout(500) }
}
const mapShot = () => page.screenshot({ clip: CLIP })
const panelTxt = () => page.evaluate(() => (document.querySelector('aside')?.innerText || '').slice(0, 4000))

async function act(label, attendu, fn, { shot = null, wait = 2400, pixel = false } = {}) {
  net = []; errs = []
  const beforeP = await panelTxt()
  const beforePx = pixel ? await mapShot() : null
  let clickErr = null
  try { await fn() } catch (e) { clickErr = e.message.slice(0, 110) }
  await page.waitForTimeout(wait)
  const afterP = await panelTxt()
  const pxChanged = pixel ? !(await mapShot()).equals(beforePx) : null
  const httpBad = net.filter((n) => n.status >= 400)
  const changed = beforeP !== afterP || pxChanged === true
  let statut = 'OK'
  if (clickErr) statut = 'CASSÉ (clic: ' + clickErr + ')'
  else if (errs.length || httpBad.length) statut = 'CASSÉ'
  else if (!changed && net.length === 0) statut = 'MORT?'
  results.push({ label, attendu, statut, net: net.slice(0, 5).filter((n) => !/dark_nolabels|wmts/.test(n.url)), pxChanged, errs: errs.slice(0, 3) })
  console.log(`[${statut}] ${label} — net:${net.length} px:${pxChanged} chgPanel:${beforeP !== afterP}`)
  if (shot) await page.screenshot({ path: `${OUT}/${shot}` })
}

await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3500)

// entonnoir : ouvrir → lire → fermer par overlay
await act('"pourquoi ? ▾" entonnoir (ouvrir)', 'popover motifs SQL-exacts', async () => {
  await page.locator('button[title*="entonnoir"]').click()
}, { shot: 'btn-entonnoir.png' })
const entonnoirTxt = await page.evaluate(() => {
  const el = [...document.querySelectorAll('div')].filter((d) => /analysé|écart|motif/i.test(d.innerText || '') && d.innerText.length < 1500)
  return el.sort((a, b) => a.innerText.length - b.innerText.length).pop()?.innerText?.slice(0, 900) || '(vide)'
})
writeFileSync('../reports/m6-audit/entonnoir-texte.txt', entonnoirTxt)
await act('Entonnoir — clic hors popover', 'referme', async () => { await closeOverlay() })

// toggle copro
await act('Toggle "masquer les copropriétés"', 'hors_copro=true, compteurs recalculés', async () => {
  await page.locator('aside input[type="checkbox"]').first().click()
}, { shot: 'btn-toggle-copro.png', wait: 2800 })
await act('Toggle copro — retour', 'filtre retiré', async () => { await page.locator('aside input[type="checkbox"]').first().click() })

// tout voir + carte résultat + fermer fiche
await act('"Tout voir →"', 'étend la liste', async () => { await page.locator('button:has-text("Tout voir")').click() }, { shot: 'btn-tout-voir.png', wait: 3200 })
await act('Carte de résultat (1re)', 'ouvre la fiche', async () => {
  await page.locator('aside button').filter({ hasText: /m² ·/ }).first().click()
}, { shot: 'btn-carte-resultat-fiche.png', wait: 3800 })
await act('Fermer la fiche', 'referme', async () => {
  await page.locator('button[title*="Fermer" i]').first().click()
})

// toolbar : fond de plan (fermer par overlay), 3D, mesures
await act('Zoom "−" (diff pixel)', 'dézoome', async () => { await page.locator('button[title="Dézoomer"]').click() }, { pixel: true, wait: 2600 })
await act('Fond de plan → "Ortho IGN" puis "1950-1965"', 'ortho historique', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(600)
  await page.locator('button:has-text("Ortho IGN")').click(); await page.waitForTimeout(2500)
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(600)
  await page.locator('button:has-text("1950-1965")').click()
}, { shot: 'btn-ortho-1950.png', pixel: true, wait: 4000 })
await act('Retour fond "Sombre (Carto)"', 'fond sombre', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(600)
  await page.locator('button:has-text("Sombre (Carto)")').last().click()
}, { pixel: true, wait: 3000 })
await act('"3D" on', 'relief', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { shot: 'btn-3d.png', pixel: true, wait: 3200 })
await act('"3D" off', 'plat', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { pixel: true, wait: 2500 })

const mapC = { x: 800, y: 450 }
await act('Outil Distance', 'mesure affichée', async () => {
  await page.locator('button[title^="Distance"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(400)
  await page.mouse.click(mapC.x + 80, mapC.y + 40); await page.waitForTimeout(400)
  await page.mouse.dblclick(mapC.x + 80, mapC.y + 40)
}, { shot: 'btn-mesure-distance.png', pixel: true })
await page.keyboard.press('Escape'); await page.waitForTimeout(500)
await act('Outil Surface', 'surface affichée', async () => {
  await page.locator('button[title^="Surface"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 90, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 50, mapC.y + 70); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x + 50, mapC.y + 70)
}, { shot: 'btn-mesure-surface.png', pixel: true })
await page.keyboard.press('Escape'); await page.waitForTimeout(500)
await act('Outil Altitude', 'altitude au point (API)', async () => {
  await page.locator('button[title^="Altitude"]').click()
  await page.mouse.click(mapC.x, mapC.y)
}, { shot: 'btn-altitude.png', pixel: true, wait: 3000 })
await page.keyboard.press('Escape'); await page.waitForTimeout(500)
await act('Outil Zone (polygone)', 'résultats filtrés à la zone', async () => {
  await page.locator('button[title^="Zone"]').click()
  await page.mouse.click(mapC.x - 100, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y + 90); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x - 100, mapC.y + 90)
}, { shot: 'btn-zone-filtre.png', pixel: true, wait: 3400 })
await act('"Zone active ×"', 'retire le filtre zone', async () => {
  await page.locator('button:has-text("Zone active")').click()
}, { wait: 2400 })

// notifications : re-clic cloche pour fermer (après ouverture)
await act('Notifications — ouvrir', 'popover', async () => { await page.locator('button[title="Notifications"]').click() })
await act('Notifications — clic hors popover', 'referme (l’overlay)', async () => { await closeOverlay() })

writeFileSync('../reports/m6-audit/boutons-cartes3.json', JSON.stringify(results, null, 1))
console.log(`\n${results.length} actions (part 3)`)
await browser.close()
