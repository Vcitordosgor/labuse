// FICHE-COUCHES-4 lot 1 — capture foret_publique (parcelle témoin de l'audit). node ... <avant|apres>
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'apres'
const IDU = '97415000AH0019'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/fiche-couches4/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse && !!window.__labuse_map, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(2500); await p.evaluate((i) => window.__labuse.select(i), IDU)
await p.waitForFunction((i) => { const bx = document.querySelector('.fiche-v6'); return bx && bx.textContent.includes(i) }, IDU, { timeout: 30000 }).catch(() => {})
await sleep(5000)
// ouvrir Constructibilité (avant : plante ; après : ok) puis Urbanisme (Situation)
await p.getByText('Constructibilité', { exact: false }).first().click({ timeout: 4000 }).catch(() => {})
await sleep(1500)
const crashed = await p.evaluate(() => document.body.textContent.includes('Une erreur est survenue'))
if (crashed) {
  console.log(PHASE, 'CRASH (fiche indisponible)')
  await p.screenshot({ path: OUT + `lot1_${PHASE}.png` })  // pleine page = l'écran d'erreur
} else {
  const u = p.locator('.fiche-v6').getByText('Urbanisme', { exact: false }).first()
  if (await u.count().catch(() => 0)) { await u.click({ timeout: 4000 }).catch(() => {}); await sleep(1500) }
  await p.evaluate(() => { const el = [...document.querySelectorAll('.fiche-v6 *')].find((e) => (e.textContent || '').includes('forêt domaniale') && e.querySelectorAll('*').length < 4); if (el) el.scrollIntoView({ block: 'center' }) })
  await sleep(500)
  const vis = await p.evaluate(() => (document.querySelector('.fiche-v6')?.textContent || '').includes('forêt domaniale'))
  console.log(PHASE, 'forêt domaniale visible =', vis)
  await p.screenshot({ path: OUT + `lot1_${PHASE}.png`, clip: { x: 1010, y: 0, width: 430, height: 1000 } })
}
await br.close()
