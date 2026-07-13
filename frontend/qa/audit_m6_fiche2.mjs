// AUDIT M6 §1.6 — étape 4bis : extras fiche (recherche interne, source drawer, calculette, IA).
// LECTURE SEULE. Usage : cd frontend && node qa/audit_m6_fiche2.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })
const IDU = process.env.IDU_Q || 'AC 0253'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 180)) })
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || /pbf|basemap|cartocdn|nolabels/.test(u)) return
  net.push({ url: u.slice(0, 180), status: r.status() })
})
const out = {}

await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.fill('input[title^="Recherche du dashboard"]', IDU)
await page.keyboard.press('Enter')
await page.waitForTimeout(4500)

// 1. recherche interne
try {
  await page.locator('button[title^="Rechercher dans cette fiche"]').click({ timeout: 8000 })
  await page.locator('input[placeholder*="fiche" i], input[placeholder*="Chercher" i]').first().fill('PLU')
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-recherche-interne.png` })
  out.recherche = await page.evaluate(() => (document.body.innerText.match(/\d+ résultat[^\n]*/) || ['?'])[0])
  await page.keyboard.press('Escape'); await page.waitForTimeout(600)
} catch (e) { out.recherche = 'KO ' + e.message.slice(0, 80) }
console.log('recherche interne:', out.recherche)

// 2. source drawer : cliquer la référence source d'une ligne (span cliquable)
try {
  const srcBtn = page.locator('text=/spatial_layers#|parcel_residuel#/').first()
  await srcBtn.click({ timeout: 8000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-source-drawer.png` })
  out.drawer = await page.evaluate(() => {
    const a = [...document.querySelectorAll('aside')].map((x) => x.innerText).sort((p, q) => q.length - p.length)
    return (a.find((t) => /SOURCE|EXTRAIT/i.test(t)) || a[0] || '').slice(0, 700)
  })
  // « Toutes les sources → »
  const ts = page.locator('button:has-text("Toutes les sources")')
  out.toutes_sources = (await ts.count()) ? 'présent' : 'absent'
  await page.keyboard.press('Escape'); await page.waitForTimeout(500)
  const ov = page.locator('div.fixed.inset-0'); if (await ov.count()) await ov.last().click({ position: { x: 200, y: 400 }, force: true })
} catch (e) { out.drawer = 'KO ' + e.message.slice(0, 80) }
console.log('drawer:', (out.drawer || '').slice(0, 200).replace(/\n/g, ' | '))

// 3. calculette : Bilan, remplir coût + prix demandé
try {
  await page.locator('button:text-is("Bilan")').first().click(); await page.waitForTimeout(2000)
  const nums = page.locator('input[type="number"]')
  console.log('inputs number visibles :', await nums.count())
  await nums.nth(0).fill('2200'); await page.waitForTimeout(900)
  const n = await nums.count()
  await nums.nth(n - 1).fill('150000'); await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-calculette-verdict.png` })
  out.calculette = await page.evaluate(() => (document.body.innerText.match(/(Supportable|Trop cher|NÉGATIVE|non calculable)[^\n]{0,140}/) || ['(pas de verdict)'])[0])
} catch (e) { out.calculette = 'KO ' + e.message.slice(0, 90) }
console.log('calculette:', out.calculette)

// 4. IA popover
try {
  net = []
  await page.locator('button[title="Analyse IA"]').click({ timeout: 8000 })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/fiche-ia-popover.png` })
  out.ia = {
    net: net.slice(0, 5),
    texte: await page.evaluate(() => (document.body.innerText.match(/(Synthèse[\s\S]{0,300}Pourquoi[\s\S]{0,400})/) || ['?'])[0].slice(0, 500)),
  }
} catch (e) { out.ia = 'KO ' + e.message.slice(0, 90) }
console.log('IA:', JSON.stringify(out.ia).slice(0, 400))

// 5. hrefs des exports (non cliqués)
out.hrefs = await page.evaluate(() => [...document.querySelectorAll('a')].map((a) => ({ t: a.innerText.trim(), href: a.getAttribute('href') })).filter((x) => x.t && x.href && !x.href.startsWith('#')))
console.log('hrefs:', JSON.stringify(out.hrefs))
out.errs = errs.slice(0, 5)

// 6. ANRU muette — page NEUVE en mode commune Entre-Deux (aucun périmètre ANRU)
const p2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net2 = []
p2.on('response', async (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (!u.includes('layers.geojson')) return
  const e = { url: u.slice(0, 160), status: r.status(), n: null }
  try { const j = await r.json(); e.n = j?.features?.length ?? null } catch {}
  net2.push(e)
})
await p2.goto(BASE + '#f=1&v=1&c=Entre-Deux', { waitUntil: 'networkidle', timeout: 60000 })
await p2.waitForTimeout(3500)
await p2.locator('button:has(span:text-is("ANRU (NPNRU)"))').first().click()
await p2.waitForTimeout(3000)
await p2.screenshot({ path: `${OUT}/etat-anru-muet.png` })
out.anru = {
  net: net2,
  feedback: await p2.evaluate(() => (document.body.innerText.match(/[Aa]ucun[^\n]{0,120}ANRU[^\n]{0,80}|ANRU[^\n]{0,120}aucun[^\n]{0,80}/) || ['(aucun message utilisateur)'])[0]),
}
console.log('ANRU Entre-Deux:', JSON.stringify(out.anru))
await p2.close()

// 7. IA — recherche NL (page neuve) : saisie manuelle puis Chercher
const p3 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net3 = []
p3.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || /pbf|basemap|nolabels/.test(u)) return
  net3.push({ url: u.slice(0, 180), status: r.status() })
})
await p3.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await p3.waitForTimeout(2500)
await p3.locator('button[title="IA"]').click(); await p3.waitForTimeout(1200)
await p3.screenshot({ path: `${OUT}/ia-page.png` })
net3 = []
try {
  await p3.locator('input[placeholder*="chaudes avec vue mer"]').fill('les chaudes avec vue mer de plus de 1 000 m²')
  await p3.locator('button:has-text("Chercher")').first().click()
  await p3.waitForTimeout(6000)
  await p3.screenshot({ path: `${OUT}/ia-recherche.png` })
  out.ia_search = { net: net3.slice(0, 6), texte: (await p3.evaluate(() => document.body.innerText)).slice(0, 900) }
} catch (e) { out.ia_search = 'KO ' + e.message.slice(0, 100) }
console.log('IA search:', JSON.stringify(out.ia_search).slice(0, 500))
await p3.close()

writeFileSync('../reports/m6-audit/fiche-extras.json', JSON.stringify(out, null, 1))
await browser.close()
