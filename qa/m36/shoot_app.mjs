// M36 — captures app : légende « Classement servi », infobulle marqueurs (dump DOM),
// fiche commune avec compteur en dur. Usage : node ../qa/m36/shoot_app.mjs <url>
import { writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.argv[2]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForSelector('[data-commune-marker]', { timeout: 30000 })
await p.click('[data-verdict-on]')
await p.waitForTimeout(4500)
// dump VERBATIM des infobulles (DOM réel) — preuve de l'étiquette corrigée
const titles = await p.$$eval('[data-commune-marker]', (els) => els.map((e) => e.getAttribute('title')))
writeFileSync('../qa/m36/screens/1b_infobulles_corrigees.txt',
  ['# Infobulles RÉELLES des marqueurs communes (M36 Lot A — étiquette vraie)',
   `# ${new Date().toISOString()}`, '', ...titles.sort()].join('\n'))
// légende dépliée (badge « Verdict · Classement servi ») + marqueurs à l'écran
await p.click('[data-legend-verdict-toggle]').catch(() => {})
await p.waitForTimeout(600)
await p.screenshot({ path: '../qa/m36/screens/1_legende_classement_servi_et_marqueurs.png' })
// fiche commune Saint-Denis : compteur en dur
await p.click('[data-commune-marker="Saint-Denis"]')
await p.waitForSelector('[data-classement-commune]', { timeout: 15000 })
await p.waitForTimeout(800)
await p.screenshot({ path: '../qa/m36/screens/6_fiche_commune_compteur_en_dur.png' })
console.log('OK ·', titles.filter((t) => t && t.includes('Saint-Denis'))[0])
await b.close()
