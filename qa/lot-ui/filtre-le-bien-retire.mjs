// FILTRE — la section « Le bien » (4 facettes M137) est RETIRÉE du panneau. Prouve :
// (a) le panneau ne rend plus [data-le-bien] ; « Signaux de vie » reste ;
// (b) NETTOYAGE de l'état résiduel : un lien portant les 3 clés de la section (droitsResiduels 'drr',
//     proprietaireType 'pt=public', signal 'sv=assemblage') s'ouvre SANS que ces filtres restent actifs
//     — l'URL réécrite ne les porte plus ; un signal servi voisin ('friche') est CONSERVÉ (retrait ciblé).
// Usage : BASE=http://localhost:5174/socle/ node qa/lot-ui/filtre-le-bien-retire.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)

let ok = true
try {
  // (a) panneau sans la section « Le bien » — ouvrir le tiroir Filtres (replié par défaut)
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-filtres-toggle]', { state: 'visible', timeout: 15000 })
  if ((await page.locator('[data-filtres-toggle]').getAttribute('aria-expanded')) !== 'true') {
    await page.locator('[data-filtres-toggle]').click()
  }
  // le panneau EXPERT complet (avec Signaux de vie) est derrière « Tous les filtres → »
  const tous = page.getByText('Tous les filtres', { exact: false })
  if (await tous.count()) await tous.first().click().catch(() => {})
  await page.waitForSelector('[data-signaux-vie]', { state: 'visible', timeout: 15000 })
  const leBien = await page.locator('[data-le-bien]').count()
  const signaux = await page.locator('[data-signaux-vie]').count()
  console.log(`(a) [data-le-bien]=${leBien} (doit=0) · [data-signaux-vie]=${signaux} (doit≥1)`)
  if (leBien !== 0 || signaux < 1) ok = false
  await page.locator('aside').first().screenshot({ path: `${OUT}/f6-panneau-sans-le-bien.png` }).catch(async () => {
    await page.screenshot({ path: `${OUT}/f6-panneau-sans-le-bien.png` })
  })
  console.log('📸 f6-panneau-sans-le-bien.png')

  // (b) état résiduel : lien portant les 3 clés retirées + un signal voisin servi (friche).
  // about:blank d'abord → force un CHARGEMENT COMPLET (sinon un goto qui ne change que le hash est une
  // navigation same-document : les effets de montage ne re-tournent pas, la restauration d'URL non plus).
  await page.goto('about:blank')
  await page.goto(BASE + '#f=1&drr=encore,maximum&pt=public&sv=assemblage,friche', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1800)   // laisser la restauration + réécriture d'URL se faire
  const hash = await page.evaluate(() => window.location.hash)
  const hasDrr = /(?:^|&)drr=/.test(hash)
  const hasPtPublic = /(?:^|&|=|,)public(?:$|&|,)/.test(hash) && /(?:^|&)pt=/.test(hash)
  const hasAssemblage = /assemblage/.test(hash)
  const hasFriche = /(?:^|&)sv=[^&]*friche/.test(hash)
  const hasAnalyse = /(?:^|[#&])al=1(?:$|&)/.test(hash)   // analyse orpheline ? (allumée par une facette retirée)
  console.log(`(b) hash réécrit = "${hash}"`)
  console.log(`    drr présent=${hasDrr} (doit=false) · pt=public présent=${hasPtPublic} (doit=false) · assemblage présent=${hasAssemblage} (doit=false) · friche conservé=${hasFriche} (doit=true)`)
  console.log(`    analyse orpheline al=1 présent=${hasAnalyse} (doit=false — plus aucun critère d'opinion restant)`)
  if (hasDrr || hasPtPublic || hasAssemblage || !hasFriche || hasAnalyse) ok = false

  console.log(ok ? '\n✅ FILTRE « Le bien » retiré + état résiduel nettoyé : OK' : '\n❌ échec d\'au moins une assertion')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 400))
  await page.screenshot({ path: `${OUT}/f6-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
