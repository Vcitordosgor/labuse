// AUDIT M6 §1.6 — étape 4 : FICHE PARCELLE + ÉTATS VIDES (LECTURE SEULE).
// Fiche riche (brûlante avec événement), fiche pauvre (écartée), IDU inexistant,
// couche ANRU muette. Aucune action d'écriture (pipeline/suivre/partage non cliqués).
// Usage : cd frontend && node qa/audit_m6_fiche.mjs [IDU_RICHE] [IDU_PAUVRE]
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })
const IDU_RICHE = process.argv[2] || '97415000AC0253'
const IDU_PAUVRE = process.argv[3] || ''

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })
page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)))
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || u.includes('.pbf') || u.includes('basemap')) return
  net.push({ url: u.slice(0, 180), status: r.status() })
})

const report = { fiches: [], anru: null, erreurs_console: [] }

async function openFiche(idu, tag) {
  await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(2500)
  net = []; errs = []
  const short = idu.slice(8, 10) + ' ' + idu.slice(10)
  await page.fill('input[title^="Recherche du dashboard"]', idu)
  await page.keyboard.press('Enter')
  await page.waitForTimeout(4000)
  const f = { tag, idu, tabs: {}, header: '', actions: [], net: [], errs: [] }
  f.header = await page.evaluate(() => {
    const el = [...document.querySelectorAll('div,section,aside')].filter((d) => /m²/.test(d.innerText || '') && d.querySelector('button'))
    return (document.body.innerText.match(/[A-Z]{1,2} \d{4}[\s\S]{0,300}/) || [''])[0].slice(0, 300)
  })
  // onglets
  for (const tab of ['Synthèse', 'Règles', 'Risques', 'Marché', 'Proprio', 'Solaire', 'Bilan']) {
    try {
      await page.locator(`button:text-is("${tab}")`).first().click()
      await page.waitForTimeout(1800)
      const txt = await page.evaluate(() => {
        // le conteneur de la fiche = le plus à droite contenant les onglets
        const asides = [...document.querySelectorAll('aside, section, div')]
          .filter((d) => { const r = d.getBoundingClientRect(); return r.x > 900 && r.width > 260 && d.innerText?.length > 100 })
        const el = asides.sort((a, b) => b.innerText.length - a.innerText.length)[0]
        return el ? el.innerText.slice(0, 2600) : document.body.innerText.slice(-2600)
      })
      f.tabs[tab] = txt
      await page.screenshot({ path: `${OUT}/fiche-${tag}-${tab.toLowerCase().normalize('NFD').replace(/[^a-z]/g, '')}.png` })
    } catch (e) { f.tabs[tab] = 'ERREUR clic: ' + e.message.slice(0, 100) }
  }
  // barre d'actions : libellés + hrefs (sans cliquer les écritures)
  f.actions = await page.evaluate(() => {
    return [...document.querySelectorAll('button, a')].filter((el) => {
      const r = el.getBoundingClientRect()
      return r.x > 950 && r.y > 700 && r.width > 0
    }).map((el) => ({ tag: el.tagName, text: (el.innerText || '').trim().slice(0, 40), title: el.getAttribute('title') || '', href: el.getAttribute('href') || undefined, disabled: el.disabled || undefined }))
  })
  f.net = net.filter((n) => n.status >= 400).slice(0, 10)
  f.errs = errs.slice(0, 5)
  report.fiches.push(f)
  console.log(`\n■ fiche ${tag} (${idu}) — onglets ok, actions: ${f.actions.map((a) => a.text || a.title).join(' · ')}`)
  if (f.net.length) console.log('  HTTP>=400:', JSON.stringify(f.net))
  return f
}

// 1. fiche riche : déplier les scores + source drawer + recherche fiche + calculette
const rich = await openFiche(IDU_RICHE, 'riche')
// retour Synthèse, dépliage scores
await page.locator('button:text-is("Synthèse")').first().click(); await page.waitForTimeout(1200)
for (const sb of ['Qualité', 'Accessibilité', 'Signaux vendeur']) {
  try {
    await page.locator(`button:has-text("${sb}")`).first().click()
    await page.waitForTimeout(900)
  } catch {}
}
await page.screenshot({ path: `${OUT}/fiche-riche-scores-deplies.png` })
// source drawer : cliquer la 1re source cliquable
try {
  const src = page.locator('button[title*="source" i], span[title*="Source" i], button:has-text("↗")').first()
  await src.click({ timeout: 4000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${OUT}/fiche-source-drawer.png` })
  const drawerTxt = await page.evaluate(() => [...document.querySelectorAll('aside')].map((a) => a.innerText).sort((a, b) => b.length - a.length)[0]?.slice(0, 600))
  report.source_drawer = drawerTxt
  await page.keyboard.press('Escape')
} catch (e) { report.source_drawer = 'non ouvert: ' + e.message.slice(0, 80) }
// recherche dans la fiche
try {
  await page.locator('button[title*="Chercher" i], button[title*="Rechercher" i]').first().click({ timeout: 3000 })
  await page.fill('input[placeholder*="Chercher" i]', 'PLU')
  await page.waitForTimeout(1200)
  await page.screenshot({ path: `${OUT}/fiche-recherche-interne.png` })
  await page.keyboard.press('Escape')
} catch (e) { console.log('recherche fiche KO', e.message.slice(0, 80)) }
// calculette (onglet Bilan) : remplir prix demandé
try {
  await page.locator('button:text-is("Bilan")').first().click(); await page.waitForTimeout(1500)
  const inputs = page.locator('input[type="number"]')
  const n = await inputs.count()
  if (n >= 3) { await inputs.nth(2).fill('150000'); await page.waitForTimeout(1500) }
  await page.screenshot({ path: `${OUT}/fiche-calculette-verdict.png` })
  report.calculette = await page.evaluate(() => (document.body.innerText.match(/(Supportable|Trop cher|non calculable)[\s\S]{0,180}/) || ['(pas de verdict)'])[0])
  console.log('calculette:', report.calculette.slice(0, 120))
} catch (e) { console.log('calculette KO', e.message.slice(0, 80)) }
// bouton IA (observation du repli stub / crédits)
try {
  net = []
  await page.locator('button[title="Analyse IA"]').first().click({ timeout: 3000 })
  await page.waitForTimeout(1000)
  await page.screenshot({ path: `${OUT}/fiche-ia-popover.png` })
  report.ia_popover_net = net.slice(0, 5)
  await page.keyboard.press('Escape')
} catch (e) { report.ia_popover_net = 'bouton IA non trouvé: ' + e.message.slice(0, 60) }

// 2. fiche pauvre (écartée étage 0, aucun signal)
if (IDU_PAUVRE) await openFiche(IDU_PAUVRE, 'pauvre')

// 3. IDU inexistant via omnibox
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
net = []; errs = []
await page.fill('input[title^="Recherche du dashboard"]', '97499000ZZ9999')
await page.keyboard.press('Enter')
await page.waitForTimeout(3500)
await page.screenshot({ path: `${OUT}/etat-idu-inexistant.png` })
report.idu_inexistant = {
  net: net.slice(0, 6), errs: errs.slice(0, 4),
  message: await page.evaluate(() => (document.body.innerText.match(/(introuvable|inconnu|erreur|Aucun)[^\n]{0,120}/i) || ['(aucun message)'])[0]),
}
console.log('IDU inexistant →', report.idu_inexistant.message, JSON.stringify(report.idu_inexistant.net))

// 4. couche ANRU muette : commune sans périmètre ANRU (Entre-Deux)
await page.goto(BASE + '#f=1&v=1&c=Entre-Deux', { waitUntil: 'networkidle' }); await page.waitForTimeout(3000)
net = []
await page.locator('button:has(span:text-is("ANRU (NPNRU)"))').first().click()
await page.waitForTimeout(3000)
await page.screenshot({ path: `${OUT}/etat-anru-muet.png` })
report.anru = {
  net: net.filter((n) => n.url.includes('layers')).slice(0, 4),
  message: await page.evaluate(() => (document.body.innerText.match(/(ANRU[^\n]{0,140})/g) || []).join(' | ').slice(0, 400)),
}
console.log('ANRU Entre-Deux →', JSON.stringify(report.anru))

writeFileSync('../reports/m6-audit/fiche-etats.json', JSON.stringify(report, null, 1))
console.log('\n→ reports/m6-audit/fiche-etats.json')
await browser.close()
