// PAGES-AUDIT-1 — re-capture des deux pages saisies en chargement (Sources client + Données admin).
import { chromium } from 'playwright'
const BASE = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/pages-audit/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) { await explore.first().click().catch(() => {}); await sleep(1200) }

// Sources (client) — attendre les lignes de source réelles
await p.locator('[data-rail="sources"]').first().click().catch(() => {})
await p.waitForSelector('[data-source-row]', { timeout: 30000 }).catch(() => console.log('sources rows timeout'))
await sleep(1500)
await p.screenshot({ path: `${BASE}client/00_sources.png` })
console.log('sources re-capturée, rows =', await p.locator('[data-source-row]').count())

// Données (admin) — attendre le contenu du Circuit
await p.locator('[data-rail-admin]').first().click().catch(() => {})
await sleep(2000)
await p.locator('[data-admin-section="donnees"]').first().click().catch(() => {})
// attendre que « chargement » disparaisse
await p.waitForFunction(() => !document.body.innerText.includes('Circuit — chargement'), { timeout: 30000 }).catch(() => console.log('donnees load timeout'))
await sleep(2000)
await p.screenshot({ path: `${BASE}admin/03_donnees.png` })
console.log('donnees re-capturée')
await br.close()
console.log('DONE')
