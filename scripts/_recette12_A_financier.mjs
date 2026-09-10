// RECETTE-12 A — PREUVE du garde Financier en VRAI navigateur. Front :5199 (/socle/), API :8031.
// A2 : capture de l'écran BLOQUÉ à 5 500, puis capture de l'écran FINAL à 3 800. Restaure 5 500 à la fin.
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5199/socle/'
const API = 'http://localhost:8031'
const OUT = new URL('../docs/audit-2026-09/captures-recette-12/', import.meta.url).pathname
const IDU = '97411000EL0157'
const BASELINE = { _usage: 'construction', regime_tva_saisi: 'assujetti_recuperation', bilan_demolition_eur: 20000,
  bilan_depollution_eur: 10000, logements_vises_saisi: 5, part_sociale_saisi_pct: 20, prix_demande_saisi_eur: 700000,
  typologie_moyenne_saisi: 'T2', prix_sortie_saisi_eur_m2: 4500, prix_vente_bailleur_saisi_eur_m2: 5500 }

const put = async (reponses) => {
  const r = await fetch(`${API}/financier/${IDU}/questionnaire`, { method: 'PUT',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reponses }) })
  console.log('PUT baseline bailleur=', reponses.prix_vente_bailleur_saisi_eur_m2, '→', r.status)
}
await put(BASELINE)  // garantir l'état « bug » (bailleur 5500) au départ

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 160)) })
const wait = (ms) => page.waitForTimeout(ms)
const shot = async (n) => { await page.screenshot({ path: `${OUT}${n}.png` }); console.log('CAPTURE', n) }
const present = async (sel) => ((await page.$(sel)) ? 'OUI' : 'non')
const btnDisabled = (label) => page.evaluate((l) => {
  const b = [...document.querySelectorAll('[data-financier-questionnaire] button')].find((x) => new RegExp(l).test(x.textContent))
  return b ? { disabled: b.disabled } : null
}, label)
const setBailleur = (v) => page.evaluate((val) => {
  const lab = [...document.querySelectorAll('[data-financier-questionnaire] label')].find((l) => /bailleur social/i.test(l.textContent || ''))
  if (!lab) return false
  const input = lab.closest('div').querySelector('input')
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(input, String(val)); input.dispatchEvent(new Event('input', { bubbles: true })); return true
}, v)

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await page.evaluate((i) => window.__labuse.select(i), IDU)
await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }).catch(() => {})
await wait(1200)
await page.click('[data-banquier-btn]').catch(() => {})
await page.waitForSelector('[data-financier-questionnaire]', { timeout: 10000 }).catch(() => {})
await wait(400)
if (await page.$('[data-usage="construction"]')) { await page.click('[data-usage="construction"]'); await wait(600) }
await page.waitForSelector('[data-financier-etapes] [data-etape]', { timeout: 8000 })
await wait(400)
const nEc = await page.evaluate(() => document.querySelectorAll('[data-financier-etapes] [data-etape]').length)
console.log('N écrans =', nEc)

// D'abord : sur l'écran 0, « Continuer » NE doit PAS être bloqué (le champ hors marché est ailleurs),
// mais la note « Corriger » ailleurs est présente et « Enregistrer » sera bloqué au bout.
console.log('écran 0 :', await page.locator('[data-financier-questionnaire] h2').first().textContent().catch(() => '?'),
  '· note ailleurs =', await present('[data-financier-garde-ailleurs]'),
  '· Continuer bloqué =', JSON.stringify(await btnDisabled('Continuer')))

// aller à l'écran qui PORTE le champ (bailleur) via le bouton « Corriger » de la note
await page.click('[data-financier-garde-ailleurs] button').catch(() => {})
await wait(700)
// l'accordéon « Affiner » doit s'ouvrir tout seul (effet hm) ; sinon on l'ouvre
if (await page.$('[data-financier-affiner-toggle][aria-expanded="false"]')) { await page.click('[data-financier-affiner-toggle]'); await wait(300) }
await wait(300)

console.log('--- ÉTAT BLOQUÉ (bailleur 5500) ---')
console.log('écran =', await page.locator('[data-financier-questionnaire] h2').first().textContent().catch(() => '?'))
console.log('message SOUS le champ (data-financier-garde) =', await present('[data-financier-garde]'))
console.log('Enregistrer =', JSON.stringify(await btnDisabled('Enregistrer')))
await shot('A-bloque-5500')

console.log('--- CORRECTION → 3800 ---')
await setBailleur(3800)
await wait(500)
console.log('message garde =', await present('[data-financier-garde]'), '· Enregistrer =', JSON.stringify(await btnDisabled('Enregistrer')))
const enr = await page.$('[data-financier-questionnaire] button:has-text("Enregistrer")')
if (enr) { await enr.click(); await wait(1400) }
console.log('Questionnaire enregistré =', await present('h2 >> text=Questionnaire enregistré') === 'OUI' ? 'OUI' : (await page.$('[data-financier-doc]') ? 'OUI' : 'non'),
  '· bouton doc =', await present('[data-financier-doc]'))
await shot('A-final-3800')

await browser.close()
await put(BASELINE)  // RESTAURE l'état 5500 (le PUT 3800 vient de l'enregistrer)
console.log('DONE')
