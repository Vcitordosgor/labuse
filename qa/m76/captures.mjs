// M76 — capture de la fiche ENTIÈRE déroulée + vérification programmatique des garde-fous :
// zéro date de millésime (hors « Données et méthode »), zéro score brut, bloc IA PLU masqué sur A/N.
// Usage : BASE=http://127.0.0.1:8000/socle/ node qa/m76/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const OUT = 'qa/m76/captures'
mkdirSync(OUT, { recursive: true })

// canari + 1 zone U (bloc IA présent) + 1 zone A (bloc IA masqué) + 1 RNU (Saint-Philippe)
const PARCELS = [
  ['97414000CV0907', 'canari-saint-louis'],
  ['97415000AC0253', 'saint-paul-U'],
  ['97410000BV0120', 'saint-benoit-A'],
  ['97417000AE0003', 'saint-philippe-RNU'],
]

const DATE_RE = /\b\d{2}\/\d{2}\/20\d{2}\b/g          // JJ/MM/AAAA
const SCORE_RE = /(^|\s)[+\-]\d+(\.\d+)?(\s|$)|\/100\b|\blog_hazard\b/g

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 480, height: 3200 } })
page.setDefaultTimeout(20000)
await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('[data-omnibox]')

const report = []
for (const [idu, name] of PARCELS) {
  try {
    await page.fill('[data-omnibox]', idu)
    await page.keyboard.press('Enter')
    await page.waitForSelector('[data-fiche-adresse]', { timeout: 25000 })
    // demander le verdict (déplie l'analyse + les tiroirs) si l'opt-in est là
    const optin = await page.$('[data-verdict-on]')
    if (optin) { await optin.click(); await page.waitForTimeout(2500) }
    // accordéon : ouvrir CHAQUE tiroir [data-drawer] un par un, cumuler le texte + capturer
    const drawers = await page.$$('[data-drawer]')
    let texteTiroirs = '', texteDonnees = '', traducteurVu = false, drawersOuverts = 0
    for (const dr of drawers) {
      const id = await dr.getAttribute('data-drawer')
      try {
        const head = await dr.$('button, [role="button"]')
        if (head) { await head.click(); await page.waitForTimeout(700); drawersOuverts++ }
      } catch {}
      const t = await dr.evaluate((el) => el.textContent || '')
      if (/Données et méthode/i.test(t)) texteDonnees += t; else texteTiroirs += ' ' + t
      if (await dr.$('[data-traducteur]')) traducteurVu = true
      await page.screenshot({ path: `${OUT}/${name}-${id}.png`, fullPage: false }).catch(() => {})
    }
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true }).catch(() => {})
    const dates = [...texteTiroirs.matchAll(DATE_RE)].map((m) => m[0])
    const scores = [...texteTiroirs.matchAll(SCORE_RE)].map((m) => m[0].trim()).filter(Boolean)
    report.push({ idu, name, drawers_ouverts: drawersOuverts, dates_hors_donnees: [...new Set(dates)], scores_bruts: [...new Set(scores)], traducteur_present: traducteurVu })
  } catch (e) {
    report.push({ idu, name, erreur: String(e).slice(0, 80) })
  }
}
console.log(JSON.stringify(report, null, 1))
await browser.close()
