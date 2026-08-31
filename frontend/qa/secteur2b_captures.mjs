// SECTEUR-2b — captures de recette (build servi sous /socle/, backend :8000, auth désactivée en local).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/SECTEUR-2b/captures'
fs.mkdirSync(OUT, { recursive: true })
const IDU = process.env.IDU || '97411000AW0735'
const ECH = fs.readFileSync(new URL('../../qa/radar-html/ECH-1.html', import.meta.url), 'utf-8')

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

// ── U1 — couche VEFA : rampe jaune→magenta + légende + hachures
await go('')
await page.waitForTimeout(1200)
await page.click('[data-couches-toggle]').catch(() => {})
await page.waitForTimeout(500)
await page.click('[data-layer="vefa_neuf"]').catch(() => {})
await page.waitForTimeout(400)
await page.click('[data-couches-toggle]').catch(() => {})
await page.waitForTimeout(1400)
const legToggle = page.locator('[data-legend-toggle]').first()
if (await legToggle.count()) { await legToggle.click().catch(() => {}); await page.waitForTimeout(700) }
await shot('01-vefa-rampe-hachures-U1')
report.legende_hachure = await page.locator('[data-legend-vefa-hachure]').count()

// ── U1 — clic sur une commune → panneau de détail (clic dans le nord = Saint-Denis)
const box = await page.locator('.maplibregl-canvas, canvas').first().boundingBox()
if (box) { await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.22); await page.waitForTimeout(1400) }
await shot('02-vefa-detail-commune-U1')
report.detail_panel = await page.locator('[data-vefa-detail]').count()
report.detail_par_taille = await page.locator('[data-vefa-par-taille]').first().innerText().catch(() => null)

// ── U2 — le parcours de dépôt DANS l'app Radar (admin) : bouton + 4 étapes
await go('#radar=1')
await page.waitForTimeout(1400)
report.bouton_publier = await page.locator('[data-radar-publier]').count()
await page.click('[data-radar-publier]').catch(() => {})
await page.waitForTimeout(700)
await shot('03-depot-etape1-U2')
report.drapeau_ferme = await page.locator('[data-depot-drapeau-ferme]').count()

// étape 1 → 2 : coller le HTML d'exemple (2,1 Mo → setter natif + event React, fill tronque), analyser
await page.evaluate((html) => {
  const ta = document.querySelector('[data-depot-html]')
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set
  setter.call(ta, html)
  ta.dispatchEvent(new Event('input', { bubbles: true }))
}, ECH)
await page.waitForTimeout(300)
await page.click('[data-depot-analyser]').catch(() => {})
await page.waitForSelector('[data-depot-etape="2"]', { timeout: 30000 }).catch(() => {})
await page.waitForTimeout(600)
await shot('04-depot-etape2-U2')

// étape 2 → 3 : continuer vers l'adresse
await page.click('[data-depot-continuer-adresse]').catch(() => {})
await page.waitForSelector('[data-depot-etape="3"]', { timeout: 8000 }).catch(() => {})
await page.fill('[data-depot-adresse]', '200 Boulevard Jean Jaurès, 97490 Saint-Denis').catch(() => {})
await page.fill('[data-depot-parcelle]', IDU).catch(() => {})
await page.keyboard.press('Enter').catch(() => {})
await page.fill('[data-depot-agence-nom]', 'Agence Immo Transac').catch(() => {})
await page.waitForTimeout(700)
await shot('05-depot-etape3-U2')

// étape 3 → 4 : publier
await page.click('[data-depot-publier]').catch(() => {})
await page.waitForSelector('[data-depot-etape="4"]', { timeout: 15000 }).catch(() => {})
await page.waitForTimeout(600)
await shot('06-depot-etape4-U2')
report.etape4 = await page.locator('[data-depot-etape="4"]').count()

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
