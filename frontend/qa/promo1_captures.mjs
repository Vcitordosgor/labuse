// PROMO-1 — captures de recette (build servi sous /socle/, backend :8000, auth désactivée en local).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/PROMO-1/captures'
fs.mkdirSync(OUT, { recursive: true })
const CBO_SIREN = process.env.CBO_SIREN || '452038805'
const CBO_URL = 'https://www.cbo-immobilier.com/programme/974-reunion/1'

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

// ── P4 — l'outil : une opération CBO RATTACHÉE affiche le programme + « voir sur le site » (Saint-Paul)
await go('#m=veille-promoteurs')
await page.selectOption('[data-vp-commune]', 'Saint-Paul').catch(() => {})
await page.fill('[data-vp-depuis]', '2021-01-01').catch(() => {})
await page.waitForTimeout(1600)
// amener le bloc « programme rattaché » d'une opération CBO dans la vue (preuve visuelle P4)
await page.locator('[data-vp-programme]').first().scrollIntoViewIfNeeded().catch(() => {})
await page.waitForTimeout(500)
await shot('01-outil-operation-rattachee-P4')
report.operations_rattachees = await page.locator('[data-vp-programme]').count()
report.lien_site = await page.locator('[data-vp-programme-lien]').first().getAttribute('href').catch(() => null)
// ouvrir la frise CBO (un promoteur avec programmes)
const frise = page.locator('[data-vp-frise]').first()
if (await frise.count()) { await frise.click().catch(() => {}); await page.waitForTimeout(1400) }
await shot('02-outil-frise-noms-P4')

// ── P2/P3 — la page admin « Programmes » : le référentiel (CBO déjà collecté, rattachement visible)
await go('#admin=1')
await page.waitForTimeout(700)
const btn = page.locator('[data-admin-section="programmes"]').first()
if (await btn.count()) { await btn.click().catch(() => {}); await page.waitForTimeout(1200) }
await shot('03-admin-referentiel-P3')
report.prog_rows = await page.locator('[data-prog-row]').count()

// ── P2 — la collecte assistée EN ACTION (appel IA réel sur le portfolio CBO)
await page.fill('[data-prog-siren]', CBO_SIREN).catch(() => {})
await page.fill('[data-prog-url]', CBO_URL).catch(() => {})
await page.click('[data-prog-collecter]').catch(() => {})
// l'appel modèle prend quelques secondes — on attend les lignes de proposition
await page.waitForSelector('[data-prog-ligne]', { timeout: 30000 }).catch(() => {})
await page.waitForTimeout(800)
await shot('04-admin-collecte-propositions-P2')
report.prog_lignes = await page.locator('[data-prog-ligne]').count()

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
