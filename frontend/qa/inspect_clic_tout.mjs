// INSPECTION HOSTILE — protocole « clique sur tout », écran par écran.
// Pour chaque écran : inventaire DOM des interactifs → clic souris RÉEL au centre → verdict :
//   ✓ effet visible (mutation DOM ≥ seuil, ou URL, ou requête réseau, ou nouvel onglet)
//   ✗ MORT (aucun effet ET pas visiblement désactivé)
//   ⚠ DOUTEUX (désactivé sans le montrer, effet minuscule, erreur console pendant le clic)
// Sortie : rapport JSONL + captures des ✗/⚠. AUCUN fix ici — on constate.
import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../docs/design/captures/inspection'
mkdirSync(OUT, { recursive: true })
const REPORT = `${OUT}/rapport.jsonl`
// reprise : rapport conservé (cartes + fiche_synthese déjà inspectés)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let consoleErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 160)) })
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + e.message.slice(0, 160)))
let netCount = 0
page.on('request', () => netCount++)
let popupCount = 0
page.on('popup', async (p) => { popupCount++; await p.close().catch(() => {}) })

const stats = { total: 0, ok: 0, dead: 0, doubt: 0 }
const suspects = []

async function freshTo(setup) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForSelector('text=chaudes', { timeout: 15000 })
  await page.waitForTimeout(1100)
  if (setup) await setup()
  await page.waitForTimeout(600)
}

const domSig = () => page.evaluate(() => {
  const b = document.body.innerHTML
  let h = 0
  for (let i = 0; i < b.length; i += 3) h = (h * 31 + b.charCodeAt(i)) | 0
  return { h, len: b.length, url: location.href }
})

async function inventory(scope = null) {
  return page.evaluate((scopeSel) => {
    const root = scopeSel ? (document.querySelector(scopeSel) || document) : document
    const els = [...root.querySelectorAll('button, a[href], [role="button"], select, input[type="range"], input[type="checkbox"], [draggable="true"]')]
    return els.map((el, i) => {
      const r = el.getBoundingClientRect()
      const s = getComputedStyle(el)
      const visible = r.width > 4 && r.height > 4 && s.visibility !== 'hidden' && s.display !== 'none'
        && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth
      // rogné par un ancêtre overflow (la leçon du popover)
      let clipped = false
      let n = el.parentElement
      while (n && n !== document.body) {
        const cs = getComputedStyle(n)
        const scrollable = (/(auto|scroll)/.test(cs.overflowY + cs.overflow) && n.scrollHeight > n.clientHeight + 4)
          || (/(auto|scroll)/.test(cs.overflowX + cs.overflow) && n.scrollWidth > n.clientWidth + 4)
        if (scrollable) break // atteignable en défilant : les ancêtres au-delà rognent LÉGITIMEMENT
        if (/(auto|scroll|hidden)/.test(cs.overflow + cs.overflowX + cs.overflowY)) {
          const rr = n.getBoundingClientRect()
          if (Math.min(r.bottom, rr.bottom) - Math.max(r.top, rr.top) < r.height * 0.5) { clipped = true; break }
        }
        n = n.parentElement
      }
      el.setAttribute('data-inspect', String(i))
      const label = (el.getAttribute('title') || el.getAttribute('aria-label') || el.innerText || el.getAttribute('placeholder') || el.tagName)
        .trim().replace(/\s+/g, ' ').slice(0, 60)
      const disabledVisible = (el.disabled || el.getAttribute('aria-disabled') === 'true')
        && (Number(s.opacity) < 0.75 || s.cursor === 'not-allowed' || s.cursor === 'default')
      const activeLook = /mint|B497F0/.test(el.className) || el.getAttribute('aria-current') != null
      return { i, label, tag: el.tagName, visible: visible && !clipped, clipped, activeLook,
               disabled: !!(el.disabled || el.getAttribute('aria-disabled') === 'true'), disabledVisible,
               x: r.x + r.width / 2, y: r.y + r.height / 2 }
    })
  }, scope)
}

async function inspectScreen(screen, setup, opts = {}) {
  try { await _inspectScreen(screen, setup, opts) } catch (e) {
    console.log(`  !! écran ${screen} : ${String(e).slice(0, 120)}`)
    appendFileSync(REPORT, JSON.stringify({ screen, label: '(écran)', verdict: 'DOUTEUX', why: 'inspection interrompue : ' + String(e).slice(0, 80) }) + '\n')
  }
}

async function _inspectScreen(screen, setup, { skipLabels = [], max = 90, probe = null, scope = null } = {}) {
  console.log(`\n━━ ${screen} ━━`)
  await freshTo(setup)
  const items = (await inventory(scope)).filter((e) => e.visible || e.clipped)
  let clicked = 0
  const seenShape = new Map() // squelette de libellé → nb de clics (2 max par motif répétitif)
  for (const it of items) {
    if (clicked >= max) break
    if (skipLabels.some((s) => it.label.includes(s))) continue
    const shape = it.label.replace(/[\d]/g, '#').replace(/#+/g, '#').replace(/\b[A-Z]{1,3}\b/g, '@')
    const n = seenShape.get(shape) ?? 0
    if (n >= 2) continue
    seenShape.set(shape, n + 1)
    clicked++
    stats.total++
    if (it.clipped) {
      stats.doubt++
      suspects.push({ screen, label: it.label, verdict: '⚠', why: 'ROGNÉ par un ancêtre overflow (présent au DOM, mal visible)' })
      appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict: 'DOUTEUX', why: 'rogné overflow' }) + '\n')
      continue
    }
    if (it.disabled) {
      if (it.disabledVisible) { stats.ok++; appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict: 'OK', why: 'désactivé VISIBLE' }) + '\n') }
      else {
        stats.doubt++
        suspects.push({ screen, label: it.label, verdict: '⚠', why: 'désactivé SANS le montrer' })
        appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict: 'DOUTEUX', why: 'désactivé invisible' }) + '\n')
      }
      continue
    }
    const before = await domSig()
    const netBefore = netCount
    const popBefore = popupCount
    const errBefore = consoleErrors.length
    // re-résoudre : React recrée les nœuds → ré-inventaire et retrouvaille par libellé
    await page.locator(`[data-inspect="${it.i}"]`).scrollIntoViewIfNeeded().catch(() => {})
    let fresh = await page.locator(`[data-inspect="${it.i}"]`).boundingBox().catch(() => null)
    if (!fresh) {
      const re = (await inventory(scope)).find((e) => e.label === it.label && e.visible)
      if (re) fresh = { x: re.x - 1, y: re.y - 1, width: 2, height: 2 }
    }
    if (!fresh) { appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict: 'NEUTRE', why: 'recréé/disparu (React) — revérifié par les suites ciblées' }) + '\n'); continue }
    // occlusion : si un AUTRE élément recouvre le centre (fiche par-dessus la toolbar), on saute
    const cx = fresh.x + fresh.width / 2
    const cy = fresh.y + fresh.height / 2
    const occluded = await page.evaluate(([x, y, idx]) => {
      const el = document.querySelector(`[data-inspect="${idx}"]`)
      const hit = document.elementFromPoint(x, y)
      return el && hit ? !(el === hit || el.contains(hit) || hit.contains(el)) : false
    }, [cx, cy, it.i])
    if (occluded) { appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict: 'NEUTRE', why: 'occulté par un panneau (non cliquable à cet instant — normal)' }) + '\n'); continue }
    await page.mouse.click(cx, cy).catch(() => {})
    await page.waitForTimeout(340)
    const after = await domSig()
    const effect = after.h !== before.h || after.url !== before.url || netCount > netBefore || popupCount > popBefore
    const newErrors = consoleErrors.slice(errBefore)
    let verdict = effect ? 'OK' : (it.activeLook ? 'OK' : 'MORT')
    let why = effect ? '' : (it.activeLook ? 'no-op volontaire (déjà actif)' : 'aucun effet visible (DOM/URL/réseau/onglet inchangés)')
    if (effect && newErrors.length) { verdict = 'DOUTEUX'; why = 'erreur console pendant le clic : ' + newErrors[0] }
    if (verdict === 'OK') stats.ok++
    else {
      if (verdict === 'MORT') stats.dead++
      else stats.doubt++
      const snap = `${OUT}/${screen.replace(/[^a-z0-9]/gi, '_')}_${stats.dead + stats.doubt}.png`
      await page.screenshot({ path: snap }).catch(() => {})
      suspects.push({ screen, label: it.label, verdict: verdict === 'MORT' ? '✗' : '⚠', why, snap })
    }
    appendFileSync(REPORT, JSON.stringify({ screen, label: it.label, verdict, why }) + '\n')
    // repartir d'un état propre si l'écran inspecté a disparu (navigation, fermeture)
    const lost = probe ? (await page.locator(probe).count()) === 0 : (after.url !== before.url)
    if (lost || after.len < before.len * 0.35) await freshTo(setup).catch(() => {})
  }
  console.log(`  ${clicked} éléments cliqués`)
}

const openModule = (label) => async () => {
  await page.locator('nav button[title="Outils"]').click()
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: new RegExp(label) }).first().click()
  await page.waitForTimeout(1600)
}
const openFiche = (tab) => async () => {
  await page.waitForSelector('.overflow-y-auto > button', { timeout: 20000 }) // données chargées
  await page.keyboard.press('/')
  await page.keyboard.type('AC0253')
  await page.keyboard.press('Enter')
  await page.waitForTimeout(1200)
  if (tab) { await page.getByRole('button', { name: tab, exact: true }).click(); await page.waitForTimeout(400) }
}

// ═══════════ écrans ═══════════
// (fait) cartes
// (fait) fiche_synthese
for (const t of ['Règles', 'Risques', 'Marché', 'Proprio', 'Bilan']) {
  await inspectScreen(`fiche_${t.toLowerCase()}`, openFiche(t), { max: 30, probe: 'text=97415000AC0253', scope: 'aside' })
}
await inspectScreen('cloche', async () => { await page.locator('button[title="Notifications"]').click(); await page.waitForTimeout(700) }, { max: 50 })
await inspectScreen('filtre_popover', async () => { await page.getByRole('button', { name: '+ Filtre' }).click(); await page.waitForTimeout(400) }, { max: 45 })
await inspectScreen('crm', async () => { await page.locator('nav button[title="CRM"]').click(); await page.waitForTimeout(1000) })
await inspectScreen('sources', async () => { await page.locator('button[title*="Fraîcheur"]').click(); await page.waitForTimeout(900) }, { max: 60 })
await inspectScreen('ia', async () => { await page.locator('nav button[title="IA"]').click(); await page.waitForTimeout(600) })
await inspectScreen('tiroir_outils', async () => { await page.locator('nav button[title="Outils"]').click(); await page.waitForTimeout(400) }, { max: 30 })
const MODULES = [['m01', 'Division parcellaire'], ['m02', 'Scan patrimoine'], ['m03', 'Radar permis'],
  ['m04', 'Promesses mortes'], ['m05', 'Vélocité admin'], ['m06', 'Mode bailleur'], ['m07', 'Foncier fantôme'],
  ['m08', 'Remonter le temps'], ['m09', 'Courrier propriétaire'], ['m10', 'Due diligence'],
  ['m15', 'Simulateur PLU'], ['m16', 'Assemblage'], ['m17', 'Simulateur ZAN'], ['m18', 'Baromètre foncier'],
  ['m19', 'Matching promoteurs']]
for (const [key, label] of MODULES) {
  await inspectScreen(`module_${key}`, openModule(label), { max: 35, probe: 'text=· MODULE', scope: 'aside' })
}

console.log('\n═══════════════ SYNTHÈSE ═══════════════')
console.log(`${stats.total} éléments cliqués · ${stats.dead} MORTS · ${stats.doubt} DOUTEUX · ${stats.ok} OK`)
for (const s of suspects) console.log(`  ${s.verdict} [${s.screen}] ${s.label} — ${s.why}`)
writeFileSync(`${OUT}/synthese.json`, JSON.stringify({ stats, suspects }, null, 2))
await browser.close()
