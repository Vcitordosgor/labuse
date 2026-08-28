// RETOURS VISUELS 1 — captures avant/après pour R1-R8 (+R9).
// Usage : LABEL=avant node qa/retours1_shots.mjs   (puis LABEL=apres après les correctifs)
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = '/Users/openclaw/Desktop/labuse/docs/audit-2026-08/RETOURS-VISUELS/captures'
mkdirSync(OUT, { recursive: true })
const LABEL = process.env.LABEL || 'avant'
const BASE = process.env.BASE || 'http://localhost:5174/socle/'
const IDU = '97401000AB0001' // Les Avirons — historique PM réel (7 millésimes, 1 changement)

const b = await chromium.launch({ channel: 'chrome' })

async function scene(name, fn) {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  try {
    await fn(p)
    await p.screenshot({ path: `${OUT}/${name}_${LABEL}.png` })
    console.log(`✓ ${name}`)
  } catch (e) {
    try { await p.screenshot({ path: `${OUT}/${name}_${LABEL}.png` }) } catch {}
    console.log(`⚠ ${name}: ${String(e).split('\n')[0]}`)
  } finally {
    await p.close()
  }
}

const go = async (p, hash = '') => {
  await p.goto(BASE + hash, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2500)
}

// R1 — menu « Mon compte »
await scene('r1_menu_compte', async (p) => {
  await go(p)
  await p.locator('[data-account-btn]').click()
  await p.waitForTimeout(600)
})

// R2a — panneau de recherche, section Propriétaire
await scene('r2_filtres_proprietaire', async (p) => {
  await go(p)
  const sec = p.locator('button, [role="button"]').filter({ hasText: /^Propriétaire$/ }).first()
  if (await sec.count()) { await sec.scrollIntoViewIfNeeded(); await sec.click(); await p.waitForTimeout(500) }
})

// R2b — sélecteur de commune du header
await scene('r2_selecteur_commune', async (p) => {
  await go(p)
  await p.locator('button').filter({ hasText: 'Toute l’île' }).first().click()
  await p.waitForTimeout(600)
})

// R3 — outil Communes (écran d'entrée)
await scene('r3_outil_communes', async (p) => {
  await go(p, '#m=communes')
  await p.waitForTimeout(1000)
})

// R4a — fiche commune de l'OUTIL (via tableau comparaison → clic ligne)
await scene('r4_fiche_outil', async (p) => {
  await go(p, '#m=communes')
  await p.locator('[data-o6-row]').filter({ hasText: 'Saint-Paul' }).first().click()
  await p.waitForTimeout(2500)
})

// R4b — fiche commune de CONTEXTE (panneau droit)
await scene('r4_fiche_contexte', async (p) => {
  await go(p)
  await p.locator('button').filter({ hasText: 'Toute l’île' }).first().click()
  await p.waitForTimeout(400)
  const voir = p.locator('button, a').filter({ hasText: /voir la fiche/ }).first()
  await voir.click()
  await p.waitForTimeout(1500)
})

// R5 — outil taxe d'aménagement
await scene('r5_taxe', async (p) => {
  await go(p, '#m=taxe-amenagement')
  await p.waitForTimeout(1000)
})

// R5b/R6 — fiche parcelle, tiroir Propriétaire
await scene('r6_fiche_proprietaire', async (p) => {
  await go(p, `#idu=${IDU}`)
  await p.waitForTimeout(2000)
  const dr = p.locator('aside button, aside summary, aside [role="button"]').filter({ hasText: /Propriétaire/ }).first()
  if (await dr.count()) { await dr.scrollIntoViewIfNeeded(); await dr.click(); await p.waitForTimeout(800) }
})

// R7 — intake admin Radar
await scene('r7_admin_radar', async (p) => {
  await go(p, '#admin=1')
  await p.waitForTimeout(800)
  const z = p.locator('button, a, [role="tab"]').filter({ hasText: /Radar/ }).first()
  if (await z.count()) { await z.click(); await p.waitForTimeout(1200) }
})

// R8a — carte : pastille bas-gauche + barre d'outils (Zone)
await scene('r8_carte', async (p) => {
  await go(p)
  await p.waitForTimeout(2500)
})

// R8b — rail : Veille ouverte PUIS Sources (bug : les deux visibles)
await scene('r8_rail_veille_sources', async (p) => {
  await go(p)
  await p.locator('[data-rail-surveillance]').click()
  await p.waitForTimeout(800)
  await p.locator('button').filter({ hasText: /^Sources$/ }).first().click()
  await p.waitForTimeout(1200)
})

// R9 — Radar client, onglet Marché
await scene('r9_radar_marche', async (p) => {
  await go(p, '#m=radar')
  await p.waitForTimeout(1000)
  const t = p.locator('button, [role="tab"]').filter({ hasText: /Marché/ }).first()
  if (await t.count()) { await t.click(); await p.waitForTimeout(2000) }
})

await b.close()
console.log('done:', LABEL)
