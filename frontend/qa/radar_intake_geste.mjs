// RETOURS-1 R7 (Vic) — TEST NAVIGATEUR DU GESTE DE DÉPÔT (admin Radar) :
// ajouter une image → le champ lien prend le focus (label visible) → Déposer sans lien = erreur
// claire (bordure + message) → coller un lien → Déposer → la fiche apparaît en file d'extraction.
//
// Les endpoints /admin/radar/deposer et /admin/radar/extraction sont INTERCEPTÉS (page.route) :
// l'extraction réelle passe par la vision IA (clé LIVE requise + vraie capture d'annonce), non
// simulable en local — le pipe back est couvert par la suite pytest pige. ICI on prouve le GESTE.
// Usage : node qa/radar_intake_geste.mjs   (vite dev sur :5174 requis). Sort en code 1 si échec.
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://localhost:5174/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/docs/audit-2026-08/RETOURS-VISUELS/captures'

// PNG 1×1 valide (le fichier déposé)
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64')

const BROUILLON = {
  bien_id: 9901, commune: 'Saint-Paul', type_bien: 'maison', rattachement_niveau: 'estime',
  prix: 315000, surface_hab: 92, surface_terrain: 480, dpe_classe: 'D', pieces: 4,
  particulier_pro: 'particulier', etiquettes: {}, a_verifier: ['prix'],
  portail: 'leboncoin', url_sortante: 'https://www.leboncoin.fr/ad/ventes_immobilieres/test-geste',
  created_at: '2026-08-28T08:00:00Z',
}

let fails = 0
const check = (cond, label) => {
  console.log(`${cond ? '✓' : '✗'} ${label}`)
  if (!cond) fails++
}

const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })

let depose = false
await p.route('**/admin/radar/deposer', async (route) => {
  depose = true
  await route.fulfill({ json: { statut: 'a_valider', bien_id: BROUILLON.bien_id } })
})
await p.route('**/admin/radar/extraction', async (route) => {
  await route.fulfill({ json: depose ? { file: [BROUILLON], n: 1 } : { file: [], n: 0 } })
})

await p.goto(BASE + '#admin=1', { waitUntil: 'networkidle', timeout: 60000 })
await p.waitForTimeout(1500)
await p.locator('button').filter({ hasText: 'Radar' }).first().click()
await p.waitForTimeout(1000)

// 1) ajouter une image → une ligne apparaît, le champ lien a le FOCUS, le label est visible
await p.locator('[data-radar-fichier]').setInputFiles({ name: 'annonce.png', mimeType: 'image/png', buffer: PNG })
await p.waitForTimeout(600)
check(await p.locator('[data-radar-ligne]').count() === 1, 'la capture ajoutée crée une ligne de dépôt')
check(await p.evaluate(() => document.activeElement?.getAttribute('data-radar-lien') != null),
  'le champ lien prend le focus automatiquement')
check(await p.getByText('Lien de l’annonce *').isVisible(), 'label visible au-dessus du champ (pas un placeholder seul)')

// 2) Déposer SANS lien → bordure d'erreur + message clair, rien n'est envoyé
await p.locator('[data-radar-deposer]').click()
await p.waitForTimeout(400)
check(await p.locator('[data-radar-lien][aria-invalid="true"]').count() === 1, 'bordure d’erreur sur le champ lien vide')
check(await p.getByText('Collez le lien de l’annonce').isVisible(), 'message d’erreur clair (Déposer sans lien)')
check(!depose, 'aucun dépôt envoyé sans lien')

// 3) coller le lien → Déposer → retour ✓ et fiche dans la file d'extraction
await p.locator('[data-radar-lien]').fill(BROUILLON.url_sortante)
await p.locator('[data-radar-deposer]').click()
await p.waitForTimeout(1200)
check(depose, 'le dépôt part au backend')
check(await p.getByText('✓ en file d’extraction').isVisible(), 'retour visible « ✓ en file d’extraction »')
check(await p.getByText('Saint-Paul').first().isVisible() && await p.getByText('315').first().isVisible(),
  'la fiche apparaît dans la file d’extraction (commune + prix)')

await p.screenshot({ path: `${OUT}/r7_geste_preuve.png` })
await b.close()
console.log(fails === 0 ? 'GESTE COMPLET : VERT' : `ÉCHECS : ${fails}`)
process.exit(fails === 0 ? 0 : 1)
