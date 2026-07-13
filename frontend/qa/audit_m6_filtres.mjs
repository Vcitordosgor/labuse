// AUDIT M6 §1.6 — étape 3 : FILTRES du popover « + Filtre » (LECTURE SEULE).
// Applique chaque filtre un à un, capture la requête réseau et le compteur affiché,
// à confronter aux comptes SQL (script parent).
// Usage : cd frontend && node qa/audit_m6_filtres.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
let page
let net = []
async function hookPage() {
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.on('response', async (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (!/\/(parcels|stats|map\/parcels)/.test(u)) return
  const e = { url: u.slice(0, 240), status: r.status(), n: null }
  try {
    const ct = r.headers()['content-type'] || ''
    if (ct.includes('json')) {
      const j = await r.json()
      e.n = Array.isArray(j) ? j.length : (j?.features?.length ?? null)
    }
  } catch {}
  net.push(e)
  })
}

const results = []
async function resetApp() {
  if (page) await page.close()
  await hookPage()
  await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(3000)
}

async function applyFilter(label, fn, shot) {
  await resetApp()
  await page.locator('button:has-text("+ Filtre")').click()
  await page.waitForTimeout(600)
  net = []
  await fn()
  await page.keyboard.press('Escape')
  await page.waitForTimeout(3500)
  const panelTxt = await page.evaluate(() => (document.querySelector('aside')?.innerText || ''))
  // compteurs : chips + ligne du bas
  const compte = (panelTxt.match(/[\d\s  ]+visibles.*|Tout[\s\S]{0,20}/g) || []).map((s) => s.replace(/\s+/g, ' ').trim())
  const chips = (panelTxt.match(/(Tout|Brûlantes v2|Chaudes|Réserve foncière|À creuser|Écartées)\s*[\d\s  ]+/g) || []).map((s) => s.replace(/[\s  ]+/g, ' ').trim())
  const r = { filtre: label, chips, compte, net: net.filter((n) => n.url.includes('parcels') || n.url.includes('stats')).slice(0, 6) }
  results.push(r)
  console.log(`\n■ ${label}`)
  console.log('  chips:', chips.join(' | '))
  console.log('  compte:', compte.slice(0, 3).join(' | '))
  for (const n of r.net) console.log(`  ${n.status} ${n.url}${n.n != null ? ' — n=' + n.n : ''}`)
  if (shot) await page.screenshot({ path: `${OUT}/${shot}` })
}

const exact = (name) => page.getByRole('button', { name, exact: true }).first()

await applyFilter('Avec événement (BODACC)', async () => {
  await exact('Avec événement (BODACC)').click()
}, 'filtre-evenement.png')

await applyFilter('Masquer les copropriétés', async () => {
  await exact('Masquer les copropriétés').click()
}, 'filtre-hors-copro.png')

await applyFilter('Signal proprio « Procédure collective »', async () => {
  await page.locator('button[title*="Procédure collective"]').click()
}, 'filtre-vsignal-pc.png')

await applyFilter('Flag ⚑ Risques (PPR/aléa)', async () => {
  await exact('⚑ Risques (PPR/aléa)').click()
}, 'filtre-flag-risques.png')

await applyFilter('Tier v2 « Brûlante v2 » (popover)', async () => {
  await exact('Brûlante v2').click()
}, 'filtre-tier-brulante.png')

await applyFilter('Score Q ≥ 70', async () => {
  await page.locator('input[placeholder="70"]').fill('70')
  await page.waitForTimeout(800)
}, 'filtre-score-q.png')

await applyFilter('Réinitialiser tous les filtres (après vue mer)', async () => {
  await exact('Vue mer dégagée').click()
  await page.waitForTimeout(1200)
  await exact('Réinitialiser tous les filtres').click()
}, 'filtre-reset.png')

writeFileSync('../reports/m6-audit/filtres-resultats.json', JSON.stringify(results, null, 1))
console.log('\n→ reports/m6-audit/filtres-resultats.json')
await browser.close()
