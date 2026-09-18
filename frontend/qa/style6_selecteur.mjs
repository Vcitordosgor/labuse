// COUCHES-STYLE-6 — preuve : sélecteur de fond SANS « Clair » ; Sombre inchangé.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const URL = 'http://localhost:5255/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/style6/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const CENTER = [55.2735, -21.0095, 16.2]   // même viewport que STYLE-5 pour comparer Sombre
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(3500)
await p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
const jump = async () => { for (let i = 0; i < 6; i++) { await p.evaluate(([a, b, c]) => window.__labuse_map.jumpTo({ center: [a, b], zoom: c }), CENTER); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - CENTER[2]) < 0.3) break } await sleep(2000) }
await jump()

// 1) Sombre inchangé (fond défaut) — même viewport que captures/style5/apres/sombre.png
await p.screenshot({ path: OUT + 'sombre_inchange.png' })

// 2) Sélecteur ouvert — la liste des fonds NE contient PLUS « Clair »
const bm = p.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first()
await bm.click().catch(() => {}); await sleep(600)
// lire les libellés d'option réellement présents
const options = await p.evaluate(() => {
  const panels = [...document.querySelectorAll('div')].filter((d) => d.querySelector('p') && /Fond de plan/.test(d.textContent || ''))
  return null
})
const hasClair = await p.getByRole('button', { name: 'Clair', exact: true }).count().catch(() => 0)
console.log('option « Clair » présente dans le sélecteur ?', hasClair > 0)
await p.screenshot({ path: OUT + 'selecteur_sans_clair.png' })
// crop resserré sur le menu (haut-droite)
await p.screenshot({ path: OUT + 'selecteur_sans_clair_crop.png', clip: { x: 1040, y: 40, width: 400, height: 520 } })

await br.close()
console.log('OK style6')
