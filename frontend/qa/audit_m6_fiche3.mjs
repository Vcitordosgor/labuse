// AUDIT M6 §1.6 — étape 4ter : recherche interne fiche, SourceDrawer, calculette, IA popover.
// LECTURE SEULE. Usage : cd frontend && node qa/audit_m6_fiche3.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = []
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || /pbf|basemap|cartocdn|nolabels/.test(u)) return
  net.push({ url: u.slice(0, 180), status: r.status() })
})
const out = {}

await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.fill('input[title^="Recherche du dashboard"]', 'AC 0253')
await page.keyboard.press('Enter')
await page.waitForTimeout(4500)

// 1. recherche interne — placeholder exact
try {
  await page.locator('button[title^="Rechercher dans cette fiche"]').click({ timeout: 8000 })
  const inp = page.locator('input[placeholder^="Chercher dans cette fiche"]')
  await inp.fill('PLU'); await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-recherche-interne.png` })
  out.recherche = await page.evaluate(() => (document.body.innerText.match(/\d+ résultats?[^\n]*/) || ['(compteur non trouvé)'])[0])
  await inp.fill(''); await page.waitForTimeout(400)
  await page.locator('button[title^="Rechercher dans cette fiche"]').click(); await page.waitForTimeout(800)
} catch (e) { out.recherche = 'KO ' + e.message.slice(0, 80) }
console.log('recherche interne:', out.recherche)

// 2. déplier « Qualité » puis ouvrir le SourceDrawer sur une référence source
try {
  await page.locator('button:has-text("Qualité")').first().click(); await page.waitForTimeout(1000)
  await page.locator('button.truncate', { hasText: /Géorisques|BD TOPO|Cerema|PLU\/GPU/ }).first().click({ timeout: 8000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-source-drawer.png` })
  out.drawer = await page.evaluate(() => {
    const a = [...document.querySelectorAll('aside')].map((x) => x.innerText)
    return (a.find((t) => /SOURCE|EXTRAIT/i.test(t)) || '(non trouvé)').slice(0, 600)
  })
  out.toutes_sources = (await page.locator('button:has-text("Toutes les sources")').count()) ? 'présent' : 'absent'
  const ov = page.locator('div.fixed.inset-0')
  if (await ov.count()) { await ov.last().click({ position: { x: 200, y: 400 }, force: true }); await page.waitForTimeout(600) }
} catch (e) { out.drawer = 'KO ' + e.message.slice(0, 90) }
console.log('drawer:', String(out.drawer).slice(0, 250).replace(/\n/g, ' | '), '· toutes_sources:', out.toutes_sources)

// 3. calculette (onglet Bilan)
try {
  await page.locator('button:text-is("Bilan")').first().click({ timeout: 8000 }); await page.waitForTimeout(2200)
  const nums = page.locator('input[type="number"]')
  const n = await nums.count()
  console.log('inputs number :', n)
  if (n) {
    await nums.nth(0).fill('2200'); await page.waitForTimeout(1000)
    await nums.nth(n - 1).fill('150000'); await page.waitForTimeout(1800)
  }
  await page.screenshot({ path: `${OUT}/fiche-calculette-verdict.png` })
  out.calculette = await page.evaluate(() => (document.body.innerText.match(/(charge foncière|Supportable|Trop cher|Négociable)[^\n]{0,160}/i) || ['(pas de verdict)'])[0])
  out.calculette_ctx = await page.evaluate(() => (document.body.innerText.match(/CALCULETTE[\s\S]{0,700}/) || [''])[0])
} catch (e) { out.calculette = 'KO ' + e.message.slice(0, 90) }
console.log('calculette:', out.calculette)

// 4. IA popover (bouton « IA » barre d'actions)
try {
  net = []
  await page.locator('button[title="Analyse IA"]').click({ timeout: 8000 })
  await page.waitForTimeout(3000)
  await page.screenshot({ path: `${OUT}/fiche-ia-popover.png` })
  out.ia = { net: net.slice(0, 5), texte: await page.evaluate(() => (document.body.innerText.match(/(Pourquoi ce score[\s\S]{0,300}|Synthèse IA[\s\S]{0,300})/) || ['?'])[0].slice(0, 400)) }
} catch (e) { out.ia = 'KO ' + e.message.slice(0, 90) }
console.log('IA:', JSON.stringify(out.ia).slice(0, 400))

writeFileSync('../reports/m6-audit/fiche-extras2.json', JSON.stringify(out, null, 1))
await browser.close()
