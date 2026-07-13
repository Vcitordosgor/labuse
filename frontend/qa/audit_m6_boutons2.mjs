// AUDIT M6 §1.6 — étape 2bis : reprise des boutons panneau/toolbar (LECTURE SEULE).
// Correctif : le popover Notifications ne se ferme PAS à Échap (constat consigné) —
// on le referme en re-cliquant la cloche ; page rechargée entre sections.
// Usage : cd frontend && node qa/audit_m6_boutons2.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
let page
let net = [], errs = []
const results = []

async function freshPage() {
  if (page) await page.close()
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  net = []; errs = []
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })
  page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)))
  page.on('response', (r) => {
    const u = r.url().replace(/^https?:\/\/[^/]+/, '')
    if (u.startsWith('/socle') || u.includes('.pbf') || u.includes('basemap') || u === '/events?limit=100') return
    net.push({ url: u.slice(0, 200), status: r.status() })
  })
  await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(3500)
}

const stateSig = () => page.evaluate(() => ({
  hash: location.hash,
  panel: (document.querySelector('aside')?.innerText || '').slice(0, 4000),
}))

async function act(label, attendu, fn, { shot = null, wait = 2200 } = {}) {
  net = []; errs = []
  const before = await stateSig()
  let clickErr = null
  try { await fn() } catch (e) { clickErr = e.message.slice(0, 110) }
  await page.waitForTimeout(wait)
  const after = await stateSig()
  const httpBad = net.filter((n) => n.status >= 400)
  const changed = before.hash !== after.hash || before.panel !== after.panel
  let statut = 'OK'
  if (clickErr) statut = 'CASSÉ (clic: ' + clickErr + ')'
  else if (errs.length || httpBad.length) statut = 'CASSÉ'
  else if (!changed && net.length === 0) statut = 'MORT?'
  results.push({ label, attendu, statut, net: net.slice(0, 6), errs: errs.slice(0, 3), changed })
  console.log(`[${statut}] ${label} — net:${net.length} chg:${changed}`)
  for (const n of net.slice(0, 5)) console.log(`    ${n.status} ${n.url}`)
  if (shot) await page.screenshot({ path: `${OUT}/${shot}` })
}

const btn = (t) => page.locator(`button:has-text("${t}")`).first()

// ═══ section A : chips + tri + entonnoir + toggle copro + tout voir + carte résultat ═══
await freshPage()
await act('Chip tier "Brûlantes v2"', 'liste filtrée tiers=brulante', async () => { await btn('Brûlantes v2').click() }, { shot: 'btn-chip-brulantes.png', wait: 2800 })
await act('Chip tier "Chaudes"', 'tiers=chaude', async () => { await btn('Chaudes').click() }, { wait: 2600 })
await act('Chip tier "Réserve foncière"', 'tiers=reserve_fonciere', async () => { await btn('Réserve foncière').click() }, { wait: 2600 })
await act('Chip tier "À creuser"', 'tiers=a_creuser', async () => { await btn('À creuser').click() }, { wait: 2600 })
await act('Chip tier "Écartées"', 'tiers=ecartee', async () => { await btn('Écartées').click() }, { shot: 'btn-chip-ecartees.png', wait: 2600 })
await act('Chip "Tout"', 'retour périmètre hors étage 0', async () => { await page.locator('aside button').filter({ hasText: /^Tout\b/ }).first().click() }, { wait: 2600 })
await act('Tri "×N"', 'tri par multiplicateur', async () => { await page.locator('button[title="Trier par ×N"]').click() }, { wait: 2600 })
await act('Tri "surface"', 'tri par surface', async () => { await page.locator('button[title="Trier par surface"]').click() }, { wait: 2600 })
await act('Tri "commune"', 'tri par commune', async () => { await page.locator('button[title="Trier par commune"]').click() }, { wait: 2600 })
await act('Tri "rang P"', 'tri par rang (défaut)', async () => { await page.locator('button[title^="Rang P"]').click() }, { wait: 2600 })
await act('"pourquoi ? ▾" entonnoir', 'déplie l’entonnoir par motif', async () => { await page.locator('button[title*="entonnoir"]').click() }, { shot: 'btn-entonnoir.png', wait: 2600 })
const entonnoirTxt = await page.evaluate(() => (document.body.innerText.match(/pourquoi[\s\S]{0,600}/i) || [''])[0])
writeFileSync('../reports/m6-audit/entonnoir-texte.txt', entonnoirTxt)
await act('"pourquoi ?" replier', 'replie', async () => { await page.locator('button[title*="entonnoir"]').click() })
await act('Toggle "masquer les copropriétés" (panneau)', 'hors_copro=true', async () => { await page.locator('aside input[type="checkbox"]').first().click() }, { shot: 'btn-toggle-copro.png', wait: 2600 })
await act('Toggle copro — retour', 'retire le filtre', async () => { await page.locator('aside input[type="checkbox"]').first().click() }, { wait: 2200 })
await act('"Tout voir →"', 'étend la liste au-delà du cap', async () => { await btn('Tout voir').click() }, { shot: 'btn-tout-voir.png', wait: 3200 })
await act('Carte de résultat (1re)', 'ouvre la fiche', async () => { await page.locator('aside button').filter({ hasText: /m²/ }).first().click() }, { shot: 'btn-carte-resultat-fiche.png', wait: 3500 })
await act('Fermer la fiche (✕)', 'referme', async () => { await page.locator('button[title="Fermer la fiche"], button[title*="Fermer"]').first().click() })

// ═══ section B : masquer analyse + replier panneau ═══
await freshPage()
await act('"masquer" (analyse LABUSE)', 'cadastre brut', async () => { await page.locator('button[title*="Masquer l" i]').click() }, { shot: 'btn-masquer-analyse.png' })
await act('"Afficher l’analyse LABUSE →"', 'ré-affiche', async () => { await page.locator('button').filter({ hasText: /analyse LABUSE/i }).first().click() }, { wait: 2600 })
await act('Replier le panneau "‹"', 'panneau replié', async () => { await page.locator('button[title="Replier le panneau"]').click() }, { shot: 'btn-replier.png' })
await act('Déplier le panneau "›"', 'panneau rouvert', async () => { await page.locator('button[title="Déplier le panneau"]').click() })

// ═══ section C : toolbar carte ═══
await freshPage()
await act('Zoom "+"', 'zoom avant', async () => { await page.locator('button[title="Zoomer"]').click() })
await act('Zoom "−"', 'zoom arrière', async () => { await page.locator('button[title="Dézoomer"]').click() })
await act('Fond de plan (popover)', 'popover des basemaps + Remonter le temps', async () => { await page.locator('button[title="Fond de plan"]').click() }, { shot: 'btn-fond-plan-popover.png' })
await act('Basemap "Ortho IGN"', 'bascule le fond en ortho', async () => { await btn('Ortho IGN').click() }, { shot: 'btn-fond-ortho.png', wait: 3500 })
await act('Ortho année "1950-1965"', 'ortho historique', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(600)
  await btn('1950-1965').click()
}, { shot: 'btn-ortho-1950.png', wait: 3500 })
await act('Retour basemap "Sombre (Carto)"', 'fond sombre', async () => {
  await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(600)
  await btn('Sombre (Carto)').click()
}, { wait: 2500 })
await act('"3D" on', 'relief MNT', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { shot: 'btn-3d.png', wait: 3000 })
await act('"3D" off', 'désactive', async () => { await page.locator('button[title^="Relief 3D"]').click() })
const mapC = { x: 800, y: 450 }
await act('Outil Distance', '2 points + double-clic → mesure', async () => {
  await page.locator('button[title^="Distance"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(400)
  await page.mouse.click(mapC.x + 80, mapC.y + 40); await page.waitForTimeout(400)
  await page.mouse.dblclick(mapC.x + 80, mapC.y + 40)
}, { shot: 'btn-mesure-distance.png' })
await page.keyboard.press('Escape')
await act('Outil Surface', 'polygone → surface', async () => {
  await page.locator('button[title^="Surface"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 90, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 50, mapC.y + 70); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x + 50, mapC.y + 70)
}, { shot: 'btn-mesure-surface.png' })
await page.keyboard.press('Escape')
await act('Outil Altitude', 'clic = altitude RGE ALTI', async () => {
  await page.locator('button[title^="Altitude"]').click()
  await page.mouse.click(mapC.x, mapC.y)
}, { shot: 'btn-altitude.png', wait: 2800 })
await page.keyboard.press('Escape')
await act('Outil Zone', 'polygone → filtre résultats', async () => {
  await page.locator('button[title^="Zone"]').click()
  await page.mouse.click(mapC.x - 100, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y + 90); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x - 100, mapC.y + 90)
}, { shot: 'btn-zone-filtre.png', wait: 3200 })
await act('"Zone active ×"', 'retire le filtre zone', async () => { await btn('Zone active').click() }, { wait: 2200 })

// ═══ section D : notifications — ouverture/fermeture + Échap (constat) ═══
await freshPage()
await act('Notifications — ouvrir', 'popover événements + veilles', async () => { await page.locator('button[title="Notifications"]').click() }, { shot: 'btn-notifications.png' })
const notifTxt = await page.evaluate(() => {
  const els = [...document.querySelectorAll('div')].filter((d) => /NOTIFICATIONS|VEILLES/i.test(d.innerText || '') && d.innerText.length < 4000)
  return els.sort((a, b) => a.innerText.length - b.innerText.length)[0]?.innerText || '(non trouvé)'
})
writeFileSync('../reports/m6-audit/notifications-contenu.txt', notifTxt)
console.log('NOTIF:', notifTxt.slice(0, 400).replace(/\n/g, ' | '))
await page.keyboard.press('Escape'); await page.waitForTimeout(700)
const stillOpen = await page.evaluate(() => /NOTIFICATIONS/.test(document.body.innerText))
results.push({ label: 'Notifications — Échap', attendu: 'ferme le popover', statut: stillOpen ? 'ANOMALIE (Échap ne ferme pas)' : 'OK' })
console.log('Échap ferme le popover notifications ?', !stillOpen)
await act('Notifications — re-clic cloche', 'referme le popover', async () => { await page.locator('button[title="Notifications"]').click() })

// ═══ section E : légende (verdict + mutabilité) ═══
await freshPage()
async function dumpLegend(name) {
  const legend = await page.evaluate(() => {
    const el = [...document.querySelectorAll('div')].find((d) => {
      const t = (d.innerText || '').trim()
      return (t.startsWith('VERDICT') || t.startsWith('MUTABILITÉ')) && t.length < 300 && d.querySelector('span')
    })
    if (!el) return null
    const items = [...el.querySelectorAll('div')].map((row) => {
      const dot = row.querySelector('span.rounded-full, span[style*="background"]')
      const label = [...row.querySelectorAll('span')].map((s) => s.innerText.trim()).filter(Boolean).join(' ')
      return { label, bg: dot ? getComputedStyle(dot).backgroundColor : null }
    }).filter((i) => i.label || i.bg)
    return { titre: el.innerText.split('\n')[0], texte: el.innerText, items }
  })
  console.log(`LÉGENDE ${name}:`, JSON.stringify(legend))
  return legend
}
const legVerdict = await dumpLegend('verdict')
await page.screenshot({ path: `${OUT}/legende-verdict.png`, clip: { x: 1100, y: 620, width: 340, height: 280 } })
await btn('Mutabilité').click(); await page.waitForTimeout(1500)
const legMut = await dumpLegend('mutabilite')
await page.screenshot({ path: `${OUT}/legende-mutabilite.png`, clip: { x: 1100, y: 620, width: 340, height: 280 } })
writeFileSync('../reports/m6-audit/legende-dom.json', JSON.stringify({ verdict: legVerdict, mutabilite: legMut }, null, 1))

writeFileSync('../reports/m6-audit/boutons-cartes2.json', JSON.stringify(results, null, 1))
console.log(`\n${results.length} actions testées (reprise)`)
await browser.close()
