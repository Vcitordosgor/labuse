// NU5-F — Harnais d'accessibilité & de mise en page (lecture seule).
//
// Teste l'app LABUSE servie en dev (vite) sur deux axes automatisables :
//   1. LE VERROU MOBILE : un vrai téléphone/tablette (UA mobile + écran < 1024)
//      ne doit voir QUE l'écran « disponible sur ordinateur » (data-ecran-ordinateur).
//   2. L'app rendue (fenêtre de bureau rétrécie à 390 px — non verrouillée car
//      window.screen.width reste physique) : axe-core WCAG 2.2 AA + débordement
//      horizontal + cibles tactiles < 24/44 px + repères (main/h1/label).
//
// Prérequis :
//   - backend LABUSE sur 9780, vite sur 6980 (cf. RAPPORT.md §Méthode)
//   - `npm install` dans ce dossier (axe-core + playwright ; navigateurs déjà en cache)
// Lancement :  node audit_a11y.mjs   → écrit resultats.json et code de sortie ≠0 si échec « dur ».
//
// « Échec dur » = débordement horizontal à 390 px OU violation axe d'impact serious/critical
// OU verrou mobile absent. Ce sont les garde-fous qu'une CI ferait respecter.

import { chromium, devices } from 'playwright'
import { createRequire } from 'module'
import { writeFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const require = createRequire(import.meta.url)
const AXE = require.resolve('axe-core/axe.min.js')
const HERE = dirname(fileURLToPath(import.meta.url))
const BASE = process.env.LABUSE_SOCLE ?? 'http://127.0.0.1:6980/socle/'

// Vues atteignables depuis le rail (libellé = nom accessible du bouton).
const VUES = ['Carte', 'Copilote', 'Docs', 'Radar', 'Projets', 'CRM', 'Sources']
const VIEWPORTS = [
  { nom: 'mobile-390', w: 390, h: 844 },
  { nom: 'bureau-1440', w: 1440, h: 900 },
]
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

async function runAxe(page) {
  await page.addScriptTag({ path: AXE })
  return page.evaluate(async (tags) => {
    const r = await window.axe.run(document, { resultTypes: ['violations'], runOnly: { type: 'tag', values: tags } })
    return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, help: v.help,
      cibles: v.nodes.slice(0, 4).map((nd) => nd.target.join(' ')) }))
  }, AXE_TAGS)
}

async function mesureMiseEnPage(page) {
  return page.evaluate(() => {
    const de = document.documentElement
    const vw = window.innerWidth
    const vis = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el)
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' }
    const ctrls = [...document.querySelectorAll('button,a[href],[role="button"],input,select,textarea,[tabindex]')].filter(vis)
    let sous24 = 0, sous44 = 0
    for (const el of ctrls) { const r = el.getBoundingClientRect()
      if (r.height < 24 || r.width < 24) sous24++
      if (r.height < 44) sous44++ }
    const inputsSansNom = [...document.querySelectorAll('input:not([type=hidden]),textarea,select')].filter(vis).filter((el) => {
      const id = el.id
      return !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby') && !(id && document.querySelector(`label[for="${id}"]`))
    }).length
    return {
      debordementHorizontal: de.scrollWidth - de.clientWidth,
      controles: ctrls.length, ciblesSous24: sous24, ciblesSous44: sous44,
      main: document.querySelectorAll('main').length,
      h1: document.querySelectorAll('h1').length,
      roleHeading: document.querySelectorAll('[role="heading"]').length,
      skipLink: !!document.querySelector('a[href^="#"][class*="skip"], a[href="#main"], [class*="skip-link"]'),
      inputsSansNom,
      thSansScope: document.querySelectorAll('th:not([scope])').length,
      regionsLive: document.querySelectorAll('[aria-live],[role="log"],[role="status"]').length,
    }
  })
}

async function main() {
  const resultats = { base: BASE, verrouMobile: null, pages: [], echecsDurs: [] }
  // Navigateur : par défaut celui de Playwright ; sinon un binaire Chromium fourni via
  // LABUSE_CHROMIUM (utile quand le cache ms-playwright ne correspond pas à la version installée).
  const launchOpts = process.env.LABUSE_CHROMIUM ? { executablePath: process.env.LABUSE_CHROMIUM } : {}
  const browser = await chromium.launch(launchOpts)

  // ── 1. VERROU MOBILE : contexte vrai iPhone (écran < 1024 + UA mobile + tactile).
  for (const [dev, label] of [['iPhone 13', 'iPhone 13 (390, portrait)'], ['iPad (gen 7)', 'iPad gen7 (810, portrait)']]) {
    const ctx = await browser.newContext({ ...devices[dev] })
    const page = await ctx.newPage()
    await page.goto(BASE, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(600)
    const verrou = await page.evaluate(() => ({
      ecranOrdinateur: !!document.querySelector('[data-ecran-ordinateur]'),
      appMontee: !!document.querySelector('[data-rail], .rail-item, nav'),
      texte: (document.body.innerText || '').slice(0, 80),
    }))
    resultats.verrouMobile = resultats.verrouMobile || {}
    resultats.verrouMobile[label] = verrou
    if (!verrou.ecranOrdinateur) resultats.echecsDurs.push(`VERROU MOBILE absent sur ${label}`)
    await ctx.close()
  }

  // ── 2. APP RENDUE (fenêtre de bureau rétrécie — non verrouillée).
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)

  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.w, height: vp.h })
    for (const vue of VUES) {
      try {
        await page.getByRole('button', { name: vue, exact: true }).first().click({ timeout: 4000 })
        await page.waitForTimeout(800)
      } catch { /* vue inatteignable (ex. CRM vide) : on mesure quand même l'état courant */ }
      const axe = await runAxe(page)
      const mep = await mesureMiseEnPage(page)
      const serious = axe.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      resultats.pages.push({ vue, viewport: vp.nom, axeViolations: axe, miseEnPage: mep,
        axeSeriousPlus: serious.reduce((a, v) => a + v.n, 0) })
      if (vp.w <= 400 && mep.debordementHorizontal > 0)
        resultats.echecsDurs.push(`Débordement horizontal ${mep.debordementHorizontal}px — ${vue} @${vp.nom}`)
      for (const v of serious) resultats.echecsDurs.push(`axe ${v.id} (${v.impact}, ${v.n}) — ${vue} @${vp.nom}`)
    }
  }

  await browser.close()
  writeFileSync(join(HERE, 'resultats.json'), JSON.stringify(resultats, null, 2))
  const dur = [...new Set(resultats.echecsDurs)]
  console.log(`Pages mesurées : ${resultats.pages.length} · échecs durs (uniques) : ${dur.length}`)
  dur.slice(0, 40).forEach((e) => console.log('  ✗ ' + e))
  process.exit(dur.length ? 1 : 0)
}

main().catch((e) => { console.error(e); process.exit(2) })
