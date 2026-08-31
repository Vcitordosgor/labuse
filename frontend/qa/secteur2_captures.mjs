// SECTEUR-2 — captures de recette (build servi sous /socle/, backend :8000, auth désactivée en local).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/SECTEUR-2/captures'
fs.mkdirSync(OUT, { recursive: true })
const IDU = process.env.IDU || '97411000AW0735'   // Saint-Denis (secteur bâti fourni)

const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

let _n = 0
const go = async (hash) => { await page.goto(`${BASE}?c=${++_n}${hash}`, { waitUntil: 'networkidle' }); await page.waitForTimeout(1000) }
const shot = async (name) => { await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false }); console.log('  shot', name) }
const report = {}

// ── T1 — Mon secteur par IDU : bandeau .stats (nombres non coupés) + écart commune + distribution
await go('#m=mon-secteur')
await page.fill('[data-mon-secteur-input]', IDU).catch(() => {})
await page.keyboard.press('Enter').catch(() => {})
await page.waitForTimeout(1600)
await shot('01-mon-secteur-idu-T1')
report.secteur_stats = await page.locator('[data-secteur-bati-stats]').count()
report.ecart_commune = await page.locator('[data-secteur-ecart-commune]').first().innerText().catch(() => null)

// ── T1 — Mon secteur par adresse
await go('#m=mon-secteur')
await page.fill('[data-mon-secteur-input]', 'Boulevard Jean Jaurès Saint-Denis').catch(() => {})
await page.waitForTimeout(1400)
await shot('02-mon-secteur-adresse-T1')

// ── T2 — Veille promoteurs = opérations : liste + points carte + frise CBO
await go('#m=veille-promoteurs')
await page.fill('[data-vp-depuis]', '2023-01-01').catch(() => {})
await page.waitForTimeout(1600)
await shot('03-veille-operations-carte-T2')
report.vp_operations = await page.locator('[data-vp-operation]').count()
// ouvrir la frise d'un promoteur (CBO/SIDR selon l'ordre) : clic « sa frise »
const frise = page.locator('[data-vp-frise]').first()
if (await frise.count()) { await frise.click().catch(() => {}); await page.waitForTimeout(1400) }
await shot('04-veille-frise-T2')

// ── T3 — Radar : bouton « Publier une annonce » dans l'en-tête (admin)
await go('#radar=1')
await page.waitForTimeout(1600)
await shot('05-radar-bouton-publier-T3')
report.radar_publier = await page.locator('[data-radar-publier]').count()

// ── T4 — Couche « Prix du logement neuf (VEFA) » : choropleth commune + légende
await go('')
await page.waitForTimeout(1200)
await page.click('[data-couches-toggle]').catch(() => {})
await page.waitForTimeout(500)
await page.click('[data-layer="vefa_neuf"]').catch(() => {})
await page.waitForTimeout(400)
await page.click('[data-couches-toggle]').catch(() => {})   // refermer le tiroir
await page.waitForTimeout(1600)
report.vefa_layer = await page.locator('[data-layer="vefa_neuf"]').count()
// déplier la légende pour montrer les tranches VEFA
const legToggle = page.locator('[data-legend-toggle]').first()
if (await legToggle.count()) { await legToggle.click().catch(() => {}); await page.waitForTimeout(700) }
await shot('06-vefa-neuf-carte-T4')
report.vefa_legend = await page.locator('[data-legend-vefa]').count()

// ── T5 — Zonage par parcelle + sous-option « afficher les limites officielles »
await go('')
await page.waitForTimeout(1200)
await page.click('[data-couches-toggle]').catch(() => {})
await page.waitForTimeout(500)
await page.click('[data-layer="zonage_parcelle"]').catch(() => {})
await page.waitForTimeout(500)
await shot('07-plu-sous-option-T5')
report.sous_option = await page.locator('[data-layer-sub="zonage"]').count()
report.zonage_dans_menu = await page.locator('[data-layer="zonage"]').count()   // doit être 0 (retirée du menu)

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
