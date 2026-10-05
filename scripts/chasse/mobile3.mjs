// CHASSE-3 angle 6 — mobile 390×844 sur le BUILD : 10 fiches + 3 outils.
// Deux garanties : (1) les CHIFFRES visibles en mobile = ceux du desktop (aucun nombre
// perdu/changé par le responsive) ; (2) rien de TRONQUÉ qui change le sens (détection
// scrollWidth > clientWidth sur les éléments porteurs de chiffres, « 1 2 » coupé de « 1 250 »).
// Les URLs jouées sont celles que l'APP écrit elle-même (#f=1&…) — le « #idu= » nu n'est
// pas une URL émise par l'app (vérifié : seule la forme #f=1&idu= se réhydrate).
// Sorties : docs/audit-2026-10/CHASSE-3/MOBILE.csv + captures mobiles (gitignorées si lourdes).
// Rejouable : node scripts/chasse/mobile3.mjs   (API build : LABUSE_CHASSE3_API, défaut :6015)
import fs from 'node:fs'
import pkg from '../../frontend/node_modules/playwright/index.js'
const { chromium } = pkg

const BASE = (process.env.LABUSE_CHASSE3_API || 'http://127.0.0.1:6015') + '/socle/'
const OUT = new URL('../../docs/audit-2026-10/CHASSE-3/', import.meta.url).pathname
fs.mkdirSync(OUT + 'captures', { recursive: true })

const FICHES = ['97411000BZ1065', '97415000ES0266', '97402000AB1117', '97401000AD0069',
  '97401000AC0537', '97412000BY1019', '97411000DE0285', '97415000AB0858',
  '97401000AD0435', '97416000ES0266']
const OUTILS = [['marche', '#f=1&m=marche&c=Saint-Denis'],
  ['calculette-fonciere', '#f=1&m=calculette-fonciere&idu=97411000BZ1065'],
  ['comparer', '#f=1&m=comparer&idu=97411000BZ1065']]

const browser = await chromium.launch({
  executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell',
})

// nombres « porteurs de sens » du texte visible : ≥ 2 chiffres ou décimal (écarte z/x/y de
// tuiles absents du DOM de toute façon ; garde surfaces, prix, %, hauteurs).
const extractionJS = `(() => {
  const t = document.body.innerText
  const nums = (t.match(/\\d[\\d\\u202f\\u00a0 ]*(?:[.,]\\d+)?/g) || [])
    .map(s => s.replace(/[\\u202f\\u00a0 ]/g, ''))
    .filter(s => s.replace(/[.,]/g, '').length >= 2)
  const compte = {}
  for (const n of nums) compte[n] = (compte[n] || 0) + 1
  return { compte, longueur: t.length }
})()`

const tronquesJS = `(() => {
  const vus = []
  for (const el of document.querySelectorAll('body *')) {
    if (el.children.length) continue
    const txt = (el.textContent || '').trim()
    if (!/\\d\\d/.test(txt)) continue
    const st = getComputedStyle(el)
    const cache = (st.overflow === 'hidden' || st.overflowX === 'hidden' || st.textOverflow === 'ellipsis')
    if (cache && el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0)
      vus.push(txt.slice(0, 60))
  }
  return [...new Set(vus)].slice(0, 20)
})()`

async function jouer(page, nom, hash, mobile) {
  await page.goto(BASE + hash, { waitUntil: 'domcontentloaded' })
  await page.reload({ waitUntil: 'domcontentloaded' })   // la réhydratation du hash se joue au boot
  try {
    await page.waitForFunction(
      () => document.body.innerText.length > 2000, { timeout: 45000 })
  } catch { /* page restée maigre : l'extraction le dira */ }
  await page.waitForTimeout(4000)
  const ex = await page.evaluate(extractionJS)
  const tronques = mobile ? await page.evaluate(tronquesJS) : []
  if (mobile) await page.screenshot({ path: `${OUT}captures/mobile_${nom}.png` })
  return { ...ex, tronques }
}

const resultats = {}
for (const [label, vp] of [['desktop', { width: 1280, height: 800 }],
                           ['mobile', { width: 390, height: 844 }]]) {
  const page = await browser.newPage({ viewport: vp })
  for (const idu of FICHES)
    (resultats[`fiche_${idu}`] ||= {})[label] = await jouer(page, `fiche_${idu}`, `#f=1&idu=${idu}`, label === 'mobile')
  for (const [k, hash] of OUTILS)
    (resultats[`outil_${k}`] ||= {})[label] = await jouer(page, `outil_${k}`, hash, label === 'mobile')
  await page.close()
  console.log(label, 'joué')
}
await browser.close()

const lignes = [['page', 'verdict', 'desktop_seulement', 'mobile_seulement', 'tronques_mobile']]
let ecarts = 0
for (const [nom, r] of Object.entries(resultats)) {
  const d = r.desktop?.compte || {}, m = r.mobile?.compte || {}
  const dSeul = Object.keys(d).filter(n => !(n in m))
  const mSeul = Object.keys(m).filter(n => !(n in d))
  const tronques = r.mobile?.tronques || []
  const verdict = (dSeul.length === 0 && tronques.length === 0) ? 'OK'
    : (tronques.length ? 'TRONQUE' : 'NOMBRES-MANQUANTS')
  if (verdict !== 'OK') ecarts++
  lignes.push([nom, verdict, dSeul.slice(0, 15).join(' '), mSeul.slice(0, 15).join(' '),
    tronques.join(' | ')])
  console.log(nom, verdict, 'd-seul:', dSeul.length, 'm-seul:', mSeul.length, 'tronqués:', tronques.length)
}
fs.writeFileSync(OUT + 'MOBILE.csv', lignes.map(l => l.join(';')).join('\n') + '\n')
console.log(`\n${ecarts} page(s) en écart → ${OUT}MOBILE.csv`)
