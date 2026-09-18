// PAGES-AUDIT-1 — une capture par page cliente + une par section admin de premier niveau.
// node qa/pages_audit.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/pages-audit/'
mkdirSync(BASE + 'client', { recursive: true })
mkdirSync(BASE + 'admin', { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
// intro éventuelle
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) { await explore.first().click().catch(() => {}); await sleep(1500) }

// ── PAGES CLIENTES (rail) ──
const CLIENT = [
  ['cartes', 'cartes'],
  ['outils', 'outils'],
  ['copilote', 'copilote'],
  ['radar', 'radar'],
  ['veille', 'veille'],
  ['projets', 'projets'],
  ['crm', 'crm'],
  ['sources', 'sources'],
]
for (const [name, rail] of CLIENT) {
  const btn = p.locator(`[data-rail="${rail}"]`)
  if (await btn.count()) { await btn.first().click().catch(() => {}) } else { console.log('  RAIL INTROUVABLE', rail) }
  // laisser charger (carte = tuiles ; listes = fetch)
  await sleep(name === 'cartes' ? 3500 : 2200)
  if (name === 'cartes') { await p.waitForFunction(() => window.__labuse_map?.areTilesLoaded?.() ?? true, { timeout: 15000 }).catch(() => {}) }
  await p.screenshot({ path: `${BASE}client/${String(CLIENT.indexOf([name, rail]) + 1).padStart(2, '0')}_${name}.png` }).catch((e) => console.log('shot err', name, e.message))
  console.log('CLIENT', name, 'OK')
}

// ── ADMIN (Tour de contrôle) ──
const adminBtn = p.locator('[data-rail-admin]')
if (await adminBtn.count()) { await adminBtn.first().click().catch(() => {}); await sleep(2500) }
else { console.log('  ADMIN RAIL INTROUVABLE'); }

const SECTIONS = ['pilotage', 'licences', 'donnees', 'courrier', 'radar', 'produit', 'ia', 'contacts']
let i = 1
for (const s of SECTIONS) {
  const b = p.locator(`[data-admin-section="${s}"]`)
  if (await b.count()) { await b.first().click().catch(() => {}) } else { console.log('  ADMIN SECTION INTROUVABLE', s) }
  await sleep(2200)
  await p.screenshot({ path: `${BASE}admin/${String(i).padStart(2, '0')}_${s}.png` }).catch((e) => console.log('shot err', s, e.message))
  console.log('ADMIN', s, 'OK'); i++
}
// cron (Horloge) — hors menu : atteint via la jauge « Système » du Pilotage
const pil = p.locator('[data-admin-section="pilotage"]')
if (await pil.count()) { await pil.first().click().catch(() => {}); await sleep(2000) }
const sysJauge = p.getByRole('button', { name: /Système/ })
if (await sysJauge.count()) { await sysJauge.first().click().catch(() => {}); await sleep(2000)
  await p.screenshot({ path: `${BASE}admin/09_cron.png` }).catch((e) => console.log('shot err cron', e.message))
  console.log('ADMIN cron OK (via jauge Système)')
} else { console.log('  JAUGE SYSTÈME INTROUVABLE — cron non capturé') }

await br.close()
console.log('DONE')
