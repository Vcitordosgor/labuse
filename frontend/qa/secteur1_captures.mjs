// SECTEUR-1 — captures de recette (build servi sous /socle/, backend :8000, auth désactivée en local).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/SECTEUR-1/captures'
fs.mkdirSync(OUT, { recursive: true })
const IDU = process.env.IDU || '97411000AW0735'   // Saint-Denis (secteur bâti fourni)

const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

// rechargement COMPLET à chaque étape (un simple changement de hash est une nav same-document : la SPA
// ne relit le deep-link qu'au montage). Le cache-buster dans la query force un vrai reload.
let _n = 0
const go = async (hash) => { await page.goto(`${BASE}?c=${++_n}${hash}`, { waitUntil: 'networkidle' }); await page.waitForTimeout(1000) }
const shot = async (name) => { await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false }); console.log('  shot', name) }
const report = {}

// ── S1 — Mon secteur : par IDU
await go('#m=mon-secteur')
await page.fill('[data-mon-secteur-input]', IDU).catch(() => {})
await page.keyboard.press('Enter').catch(() => {})
await page.waitForTimeout(1600)
await shot('01-mon-secteur-idu-S1')
report.secteur_bati = await page.locator('[data-secteur-bati]').count()
report.secteur_bati_txt = await page.locator('[data-secteur-bati]').first().innerText().catch(() => null)

// ── S1 — Mon secteur : par adresse (autocomplétion)
await go('#m=mon-secteur')
await page.fill('[data-mon-secteur-input]', 'Boulevard Jean Jaurès Saint-Denis').catch(() => {})
await page.waitForTimeout(1400)
await shot('02-mon-secteur-adresse-S1')

// ── S3 — Veille promoteurs : liste
await go('#m=veille-promoteurs')
await page.waitForTimeout(1400)
await shot('03-veille-promoteurs-S3')
report.vp_permis = await page.locator('[data-vp-permis]').count()

// ── S3 — Veille promoteurs : un promoteur, ses acquisitions
const acq = page.locator('[data-vp-acquisitions]').first()
if (await acq.count()) { await acq.click().catch(() => {}); await page.waitForTimeout(1400) }
await shot('04-veille-promoteurs-acquisitions-S3')

// ── S4 — Légende repliée puis dépliée : sur la carte pleine (sans fiche, l'overlay bottom-right est
// dégagé). La légende ne liste QUE les groupes de couches actives → on en active quelques-unes.
await go('')
await page.waitForTimeout(1400)
await page.click('[data-couches-toggle]').catch(() => {})
await page.waitForTimeout(500)
const layers = await page.locator('[data-layer]').all()
for (const l of layers.slice(0, 6)) { await l.click().catch(() => {}); await page.waitForTimeout(120) }
await page.click('[data-couches-toggle]').catch(() => {})   // refermer le tiroir pour dégager la carte
await page.waitForTimeout(1400)
await shot('05-legende-repliee-S4')
report.legende_ligne = await page.locator('[data-legend-toggle]').count()
report.legende_texte = await page.locator('[data-legend-toggle]').first().innerText().catch(() => null)
await page.click('[data-legend-toggle]').catch(() => {})
await page.waitForTimeout(700)
await shot('06-legende-depliee-S4')
report.legende_groupes = await page.locator('[data-legend-groupe]').count().catch(() => 0)

// ── S5 — Dépôt agence visible pour l'admin (drapeau fermé)
await go('#admin=1')
await page.waitForTimeout(800)
const radarBtn = page.locator('[data-admin-section="radar"]').first()
if (await radarBtn.count()) { await radarBtn.click().catch(() => {}); await page.waitForTimeout(1200) }
await shot('07-admin-radar-depot-S5')
report.depot_drapeau_ferme = await page.locator('[data-depot-drapeau-ferme]').count()

// ── S2 — Contacts institutionnels (admin)
await go('#admin=1')
await page.waitForTimeout(600)
const contactsBtn = page.locator('[data-admin-section="contacts"]').first()
if (await contactsBtn.count()) { await contactsBtn.click().catch(() => {}); await page.waitForTimeout(1400) }
await shot('08-contacts-institutionnels-S2')
report.contacts_mairies = await page.locator('[data-contacts-mairie]').count()
report.contacts_epci = await page.locator('[data-contacts-epci]').count()
report.contacts_autres = await page.locator('[data-contacts-autre]').count()
// tri par courriel (clic en-tête)
const triEmail = page.locator('[data-contacts-tri="email"]').first()
if (await triEmail.count()) { await triEmail.click().catch(() => {}); await page.waitForTimeout(500) }
await shot('09-contacts-tri-courriel-S2')

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
