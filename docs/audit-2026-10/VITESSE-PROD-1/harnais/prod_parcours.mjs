// VITESSE-PROD-1 — parcours PRODUCTION (https://app.labuse.immo), Chrome réel NON headless.
// Mesure, pour chaque geste du mandat : temps jusqu'au réseau calme (500 ms sans requête),
// nombre et poids des requêtes, et les 10 plus lentes (URL, durée, taille).
// Gestes : ouverture île · zoom commune · pans z13/z15 · 3 couches (PLU calibré, SUP, PPR) ·
// clic parcelle → fiche · ouverture d'un outil. 2 contextes : cache FROID puis CHAUD, 3 passages.
//
// AUTHENTIFICATION : cookie de session applicative fourni par l'environnement — AUCUN secret ici.
//   LABUSE_COOKIE='<valeur du cookie labuse_session>' BASE=https://app.labuse.immo \
//     node prod_parcours.mjs > ../mesures/prod_parcours.csv
// Sans LABUSE_COOKIE : le script mesure la page /login (préuve de fonctionnement) et s'arrête.
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
const HERE = dirname(fileURLToPath(import.meta.url))
// playwright : node_modules du front du worktree, sinon celui du dépôt principal (~/Desktop/labuse)
const { homedir } = await import('node:os')
let chromium
for (const base of [join(HERE, '..', '..', '..', '..', 'frontend'), join(homedir(), 'Desktop', 'labuse', 'frontend')]) {
  try { chromium = createRequire(base + '/').call(null, 'playwright').chromium; break } catch { /* suivant */ }
}
if (!chromium) throw new Error('playwright introuvable (frontend/node_modules)')

const BASE = process.env.BASE ?? 'https://app.labuse.immo'
const COOKIE = process.env.LABUSE_COOKIE ?? ''
const PASSES = Number(process.env.PASSES ?? 3)

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

function collecteur(page) {
  const reqs = []
  page.on('requestfinished', async (rq) => {
    try {
      const resp = await rq.response()
      const t = rq.timing()
      reqs.push({
        url: rq.url().replace(BASE, ''),
        ms: t.responseEnd >= 0 ? t.responseEnd : 0,
        octets: Number((await resp.allHeaders())['content-length'] || 0),
        status: resp.status(),
      })
    } catch { /* requête annulée pendant le zoom : comptée nulle part */ }
  })
  return reqs
}

async function calme(page, reqs, timeout = 60000) {
  // réseau calme = 500 ms sans NOUVELLE requête terminée (tuiles comprises)
  const t0 = Date.now()
  let n = -1
  for (;;) {
    if (Date.now() - t0 > timeout) return timeout
    const avant = reqs.length
    await sleep(500)
    if (reqs.length === avant && avant === n) return Date.now() - t0 - 1000
    n = reqs.length
  }
}

function bilan(tag, passe, reqs, depuis, ms) {
  const vagues = reqs.slice(depuis)
  const octets = vagues.reduce((s, r) => s + r.octets, 0)
  console.log(`${tag};${passe};${ms};${vagues.length};${Math.round(octets / 1024)}`)
  const lentes = [...vagues].sort((a, b) => b.ms - a.ms).slice(0, 10)
  for (const r of lentes) console.error(`  [${tag}/${passe}] ${r.ms.toFixed(0)}ms ${Math.round(r.octets / 1024)}ko ${r.status} ${r.url.slice(0, 110)}`)
}

async function geste(page, reqs, tag, passe, action) {
  const depuis = reqs.length
  const t0 = Date.now()
  await action()
  const ms = await calme(page, reqs)
  bilan(tag, passe, reqs, depuis, Date.now() - t0 - 1000 > ms ? Date.now() - t0 - 1000 : ms)
}

async function parcours(browser, passe, chaud, ctxPartage) {
  const ctx = chaud ? ctxPartage : await browser.newContext()
  if (!chaud && COOKIE) {
    await ctx.addCookies([{ name: 'labuse_session', value: COOKIE, url: BASE }])
  }
  const page = await ctx.newPage()
  const reqs = collecteur(page)
  const canvas = () => page.locator('canvas').first()

  await geste(page, reqs, `ouverture_ile_${chaud ? 'chaud' : 'froid'}`, passe, async () => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  })
  if (!COOKIE) { console.error('— LABUSE_COOKIE absent : arrêt après la page de login —'); return ctx }

  // zoom commune (Saint-Paul) : molette sur le canvas jusqu'à ~z11
  await geste(page, reqs, 'zoom_commune', passe, async () => {
    const b = await canvas().boundingBox()
    for (let i = 0; i < 4; i++) { await page.mouse.move(b.x + b.width * 0.35, b.y + b.height * 0.5); await page.mouse.wheel(0, -400); await sleep(250) }
  })
  // pans à z13 puis z15
  await geste(page, reqs, 'pan_z13', passe, async () => {
    const b = await canvas().boundingBox()
    for (let i = 0; i < 2; i++) { await page.mouse.wheel(0, -400); await sleep(250) }
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down()
    await page.mouse.move(b.x + b.width / 2 - 300, b.y + b.height / 2, { steps: 10 }); await page.mouse.up()
  })
  await geste(page, reqs, 'pan_z15', passe, async () => {
    const b = await canvas().boundingBox()
    for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -400); await sleep(250) }
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down()
    await page.mouse.move(b.x + b.width / 2 + 250, b.y + b.height / 2, { steps: 10 }); await page.mouse.up()
  })
  // 3 couches : PLU calibré, SUP, PPR (libellés du panneau Couches)
  for (const lib of ['PLU calibré', 'SUP', 'PPR']) {
    await geste(page, reqs, `couche_${lib.replace(/ /g, '_')}`, passe, async () => {
      try {
        const panneau = page.getByText('Couches', { exact: false }).first()
        if (await panneau.isVisible().catch(() => false)) await panneau.click().catch(() => {})
        await page.getByText(lib, { exact: false }).first().click({ timeout: 5000 })
      } catch (e) { console.error(`  couche ${lib} introuvable : ${e.message.split('\n')[0]}`) }
    })
  }
  // clic parcelle → fiche complète
  await geste(page, reqs, 'clic_parcelle_fiche', passe, async () => {
    const b = await canvas().boundingBox()
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2)
  })
  // un outil (premier bouton du menu Outils si présent)
  await geste(page, reqs, 'ouverture_outil', passe, async () => {
    try {
      await page.getByText('Outils', { exact: false }).first().click({ timeout: 5000 })
      await sleep(500)
    } catch (e) { console.error(`  outil introuvable : ${e.message.split('\n')[0]}`) }
  })
  await page.close()
  return ctx
}

async function run() {
  const browser = await chromium.launch({ headless: false, channel: process.env.CHROME_CHANNEL ?? 'chrome' })
    .catch(() => chromium.launch({ headless: false }))
  console.log('geste;passe;ms_jusqu_au_calme;n_requetes;ko')
  let ctxChaud = null
  for (let p = 1; p <= PASSES; p++) {
    ctxChaud = await parcours(browser, p, false, null)       // cache froid (contexte neuf)
    if (COOKIE) await parcours(browser, p, true, ctxChaud)   // cache chaud (même contexte)
  }
  await browser.close()
}

run().catch((e) => { console.error(e); process.exit(1) })
