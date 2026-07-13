// AUDIT M6 §1.6 — étape 2 : BOUTONS de l'écran Cartes + header (LECTURE SEULE).
// Chaque clic : écoute réseau + console, diff DOM/pixel, verdict OK/MORT/CASSÉ.
// AUCUN clic sur les actions d'écriture (veille, tout lire, renommer, archiver…).
// Usage : cd frontend && node qa/audit_m6_boutons.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const results = []
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })
page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)))
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || u.includes('.pbf') || u.includes('basemaps') || u.includes('tile')) return
  net.push({ url: u.slice(0, 180), status: r.status() })
})

const stateSig = () => page.evaluate(() => ({
  hash: location.hash,
  panel: (document.querySelector('aside')?.innerText || '').slice(0, 4000),
  body: document.body.innerText.length,
}))

async function act(label, attendu, fn, { shot = null, wait = 1800 } = {}) {
  net = []; errs = []
  const before = await stateSig()
  let clickErr = null
  try { await fn() } catch (e) { clickErr = e.message.slice(0, 120) }
  await page.waitForTimeout(wait)
  const after = await stateSig()
  const httpBad = net.filter((n) => n.status >= 400)
  const changed = before.hash !== after.hash || before.panel !== after.panel || Math.abs(before.body - after.body) > 5
  let statut = 'OK'
  if (clickErr) statut = 'CASSÉ (clic impossible : ' + clickErr + ')'
  else if (errs.length || httpBad.length) statut = 'CASSÉ'
  else if (!changed && net.length === 0) statut = 'MORT?'
  const r = { label, attendu, statut, net: net.slice(0, 8), errs: errs.slice(0, 3), changed, hash: after.hash }
  results.push(r)
  console.log(`[${statut}] ${label} — net:${net.length} err:${errs.length} chg:${changed}`)
  for (const n of r.net) console.log(`    ${n.status} ${n.url}`)
  if (shot) await page.screenshot({ path: `${OUT}/${shot}` })
  return r
}

const btn = (t) => page.locator(`button:has-text("${t}")`).first()
const btnTitle = (t) => page.locator(`button[title*="${t}"]`).first()

// ═══ boot ═══
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(4000)

// ═══ HEADER ═══
await act('Omnibox — recherche commune "Saint-Denis" + Entrée', 'bascule le périmètre commune', async () => {
  await page.fill('input[title^="Recherche du dashboard"]', 'Saint-Denis')
  await page.keyboard.press('Enter')
}, { shot: 'btn-omnibox-commune.png', wait: 3500 })

await act('Omnibox — recherche IDU "AC 0253"', 'ouvre la fiche de la parcelle', async () => {
  await page.fill('input[title^="Recherche du dashboard"]', 'AC 0253')
  await page.keyboard.press('Enter')
}, { shot: 'btn-omnibox-idu.png', wait: 3500 })
// referme la fiche éventuelle
await page.keyboard.press('Escape'); await page.waitForTimeout(800)

// retour Saint-Paul
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle' }); await page.waitForTimeout(2500)

await act('Bouton loupe "Lancer la recherche"', 'même action que Entrée', async () => {
  await page.fill('input[title^="Recherche du dashboard"]', 'Sainte-Marie')
  await page.locator('button[title="Lancer la recherche"]').click()
}, { wait: 3000 })
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle' }); await page.waitForTimeout(2500)

await act('Sélecteur commune (header)', 'ouvre un menu de communes', async () => {
  await page.locator('button[title^="Changer de commune"]').click()
}, { shot: 'btn-commune-menu.png' })
await page.keyboard.press('Escape'); await page.waitForTimeout(500)

await act('ⓘ Contexte', 'ouvre le panneau contexte commune (SRU, ANRU, PLH…)', async () => {
  await btn('ⓘ Contexte').click()
}, { shot: 'btn-contexte.png', wait: 2500 })
await page.keyboard.press('Escape'); await page.waitForTimeout(500)
// referme si toujours ouvert (bouton ✕ éventuel)
try { await page.locator('button:has-text("✕")').first().click({ timeout: 1500 }) } catch {}

await act('Header — bouton "Verdict"', 'mode couleur carte = verdict', async () => { await btn('Verdict').click() }, { shot: 'btn-mode-verdict.png' })
await act('Header — bouton "Mutabilité"', 'mode couleur carte = mutabilité (dégradé ×N ?)', async () => { await btn('Mutabilité').click() }, { shot: 'btn-mode-mutabilite.png' })
await act('Header — retour mode "Verdict"', 'retour couleur verdict', async () => { await btn('Verdict').click() })

await act('Notifications (badge 17)', 'ouvre le centre de notifications', async () => {
  await page.locator('button[title="Notifications"]').click()
}, { shot: 'btn-notifications.png', wait: 2500 })
// dump du contenu notifications pour véracité (sans cliquer "tout lire" = écriture)
const notifText = await page.evaluate(() => {
  const els = [...document.querySelectorAll('div,section')].filter((e) => e.innerText?.includes('Veille') || e.innerText?.includes('DÉMO') || e.innerText?.includes('Digest'))
  const el = els.sort((a, b) => a.innerText.length - b.innerText.length)[0]
  return el ? el.innerText.slice(0, 3000) : '(non trouvé)'
})
writeFileSync('../reports/m6-audit/notifications-contenu.txt', notifText)
await page.keyboard.press('Escape'); await page.waitForTimeout(600)

// ═══ PANNEAU GAUCHE ═══
await act('Chip tier "Brûlantes v2"', 'filtre liste+carte tiers=brulante', async () => { await btn('Brûlantes v2').click() }, { shot: 'btn-chip-brulantes.png', wait: 2500 })
await act('Chip tier "Chaudes"', 'tiers=chaude', async () => { await btn('Chaudes').click() }, { wait: 2500 })
await act('Chip tier "Réserve foncière"', 'tiers=reserve_fonciere', async () => { await btn('Réserve foncière').click() }, { wait: 2500 })
await act('Chip tier "À creuser"', 'tiers=a_creuser', async () => { await btn('À creuser').click() }, { wait: 2500 })
await act('Chip tier "Écartées"', 'tiers=ecartee (étage 0 dur)', async () => { await btn('Écartées').click() }, { shot: 'btn-chip-ecartees.png', wait: 2500 })
await act('Chip "Tout"', 'retour périmètre complet hors étage 0', async () => { await page.locator('button', { hasText: /^Tout/ }).first().click() }, { wait: 2500 })

await act('Tri "×N"', 'liste triée par multiplicateur', async () => { await btnTitle('Trier par ×N').click() }, { wait: 2500 })
await act('Tri "surface"', 'liste triée par surface', async () => { await btnTitle('Trier par surface').click() }, { wait: 2500 })
await act('Tri "commune"', 'liste triée par commune', async () => { await btnTitle('Trier par commune').click() }, { wait: 2500 })
await act('Tri "rang P" (défaut)', 'liste triée par rang', async () => { await btnTitle('Rang P (scoring v2)').click() }, { wait: 2500 })

await act('"pourquoi ? ▾" (entonnoir)', 'déplie l’entonnoir par motif (stats/entonnoir)', async () => { await btnTitle('entonnoir par motif').click() }, { shot: 'btn-entonnoir.png', wait: 2500 })
await act('"pourquoi ? ▴" (replier)', 'replie l’entonnoir', async () => { await page.locator('button[title*="entonnoir"]').first().click() })

// checkbox du panneau (identifier son libellé par le parent)
const cbLabel = await page.evaluate(() => {
  const cb = document.querySelector('aside input[type="checkbox"]')
  return cb ? (cb.closest('label')?.innerText || cb.parentElement?.innerText || '').slice(0, 80) : '(absent)'
})
await act(`Checkbox panneau "${cbLabel}"`, 'toggle filtre', async () => { await page.locator('aside input[type="checkbox"]').first().click() }, { wait: 2500 })
await act('Checkbox panneau — retour', 'retour état initial', async () => { await page.locator('aside input[type="checkbox"]').first().click() }, { wait: 2000 })

// lien CSV : href seulement (pas de download)
const csvHref = await page.evaluate(() => document.querySelector('a[title*="CSV"], a[download]')?.getAttribute('href'))
results.push({ label: 'Lien "⬇ CSV"', attendu: 'export CSV mêmes filtres', statut: 'OK (href relevé, non cliqué)', net: [{ url: csvHref || '(href absent)', status: '-' }] })
console.log('[OK] lien CSV →', csvHref)

await act('"Tout voir →"', 'ouvre la liste complète (page Vues/segment ?)', async () => { await btn('Tout voir').click() }, { shot: 'btn-tout-voir.png', wait: 3000 })
await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle' }); await page.waitForTimeout(2500)

await act('Carte de résultat (1er de la liste)', 'ouvre la fiche parcelle', async () => {
  await page.locator('aside button:has-text("m²")').first().click()
}, { shot: 'btn-carte-resultat-fiche.png', wait: 3500 })
await page.keyboard.press('Escape'); await page.waitForTimeout(800)

await act('Bouton "masquer" (analyse)', 'revient au cadastre brut (couleurs off)', async () => { await btnTitle("Masquer l'analyse").click() }, { shot: 'btn-masquer-analyse.png' })
await act('Bouton "afficher" (analyse)', 'ré-affiche l’analyse', async () => {
  const b = page.locator('button[title*="analyse"], button:has-text("afficher")').first(); await b.click()
})

await act('Replier le panneau "‹"', 'replie le panneau gauche', async () => { await page.locator('button[title="Replier le panneau"]').click() }, { shot: 'btn-replier.png' })
await act('Déplier le panneau', 'ré-ouvre', async () => { await page.locator('button[title*="panneau"]').first().click() })

// ═══ TOOLBAR CARTE ═══
await act('Zoom "+"', 'zoom avant', async () => { await page.locator('button[title="Zoomer"]').click() })
await act('Zoom "−"', 'zoom arrière', async () => { await page.locator('button[title="Dézoomer"]').click() })
await act('Fond de plan "Sombre (Carto)"', 'cycle le fond de plan', async () => { await page.locator('button[title="Fond de plan"]').click() }, { shot: 'btn-fond-plan.png', wait: 2500 })
const fondLabel = await page.locator('button[title="Fond de plan"]').innerText()
console.log('   fond de plan devenu :', fondLabel)
await act('Fond de plan — cycle retour', 'revient au sombre', async () => {
  for (let i = 0; i < 3; i++) { const t = await page.locator('button[title="Fond de plan"]').innerText(); if (t.includes('Sombre')) break; await page.locator('button[title="Fond de plan"]').click(); await page.waitForTimeout(1200) }
})
await act('Bouton "3D"', 'active le relief MNT', async () => { await page.locator('button[title^="Relief 3D"]').click() }, { shot: 'btn-3d.png', wait: 3000 })
await act('Bouton "3D" off', 'désactive', async () => { await page.locator('button[title^="Relief 3D"]').click() })

// outils de mesure : activer, cliquer 2-3 points sur la carte, terminer
const mapC = { x: 800, y: 450 }
await act('Outil Distance', 'mesure une distance (2 clics + double-clic)', async () => {
  await page.locator('button[title^="Distance"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(400)
  await page.mouse.click(mapC.x + 80, mapC.y + 40); await page.waitForTimeout(400)
  await page.mouse.dblclick(mapC.x + 80, mapC.y + 40)
}, { shot: 'btn-mesure-distance.png' })
await page.keyboard.press('Escape')
await act('Outil Surface', 'mesure une surface (3 sommets + double-clic)', async () => {
  await page.locator('button[title^="Surface"]').click()
  await page.mouse.click(mapC.x, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 90, mapC.y); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 50, mapC.y + 70); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x + 50, mapC.y + 70)
}, { shot: 'btn-mesure-surface.png' })
await page.keyboard.press('Escape')
await act('Outil Altitude', 'clic = altitude RGE ALTI au point', async () => {
  await page.locator('button[title^="Altitude"]').click()
  await page.mouse.click(mapC.x, mapC.y)
}, { shot: 'btn-altitude.png', wait: 2500 })
await page.keyboard.press('Escape')
await act('Outil Zone (polygone filtre)', 'dessine un polygone → résultats filtrés à la zone', async () => {
  await page.locator('button[title^="Zone"]').click()
  await page.mouse.click(mapC.x - 100, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y - 80); await page.waitForTimeout(300)
  await page.mouse.click(mapC.x + 120, mapC.y + 90); await page.waitForTimeout(300)
  await page.mouse.dblclick(mapC.x - 100, mapC.y + 90)
}, { shot: 'btn-zone-filtre.png', wait: 3000 })
await act('Zone — annuler (Échap / re-clic)', 'retire le filtre zone', async () => {
  await page.keyboard.press('Escape')
  try { await page.locator('button[title^="Zone"]').click({ timeout: 1500 }) } catch {}
})

// clic direct sur une parcelle de la carte
await act('Clic carte sur une parcelle', 'ouvre fiche ou popup', async () => {
  await page.mouse.click(mapC.x, mapC.y)
}, { shot: 'btn-clic-carte.png', wait: 3000 })
await page.keyboard.press('Escape')

// ═══ VIGNETTE LÉGENDE (bas droite) — DOM ═══
const legend = await page.evaluate(() => {
  const cand = [...document.querySelectorAll('div')].filter((d) => {
    const r = d.getBoundingClientRect()
    return r.right > window.innerWidth - 260 && r.bottom > window.innerHeight - 320 && d.innerText?.length > 10 && d.innerText.length < 700
  })
  const el = cand.sort((a, b) => a.innerText.length - b.innerText.length).find((d) => /carte|l[ée]gende|Brûlante|Chaude|verdict/i.test(d.innerText))
  if (!el) return null
  const swatches = [...el.querySelectorAll('span,i,div')].map((s) => {
    const st = getComputedStyle(s)
    return { text: (s.innerText || '').trim().slice(0, 40), bg: st.backgroundColor, border: st.borderColor, w: s.getBoundingClientRect().width }
  }).filter((s) => s.bg !== 'rgba(0, 0, 0, 0)' || s.text)
  return { text: el.innerText, swatches }
})
writeFileSync('../reports/m6-audit/legende-dom.json', JSON.stringify(legend, null, 1))
console.log('LÉGENDE:', legend ? legend.text.replace(/\n/g, ' | ') : 'NON TROUVÉE')
await page.screenshot({ path: `${OUT}/legende-vignette.png`, clip: { x: 1440 - 340, y: 900 - 360, width: 340, height: 360 } })

writeFileSync('../reports/m6-audit/boutons-cartes.json', JSON.stringify(results, null, 1))
console.log(`\n${results.length} actions testées`)
await browser.close()
