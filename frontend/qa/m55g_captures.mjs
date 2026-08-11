// M55-G — captures avant/après des 10 points (dev server :5173, reflète le working tree).
// Usage : cd frontend && node qa/m55g_captures.mjs avant   (ou apres)
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const TAG = process.argv[2] || 'avant'
const BASE = process.env.BASE || 'http://localhost:5173/socle/'
const OUT = process.env.OUT || `../reports/m55-g/captures/${TAG}`
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
const shot = (loc, name) => loc.screenshot({ path: `${OUT}/${name}.png` }).catch((e) => console.log(`✗ ${name}: ${e.message.split('\n')[0]}`))
const shotPage = (name) => page.screenshot({ path: `${OUT}/${name}.png` })

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)

// ── P10 (état initial) : carte île, aucune parcelle peinte — la légende s'affiche-t-elle ? ──
await shotPage('p10_carte_ile_initiale')
const legend = page.locator('.floating').last()
await shot(legend, 'p10_legende_zoom')

// ── P1 : contrôles d'entête du panneau (croix + chevrons) ──
const aside = page.locator('aside').first()
await shot(aside, 'p1_panneau')
await shot(page.locator('aside > div').first(), 'p1_entete_croix_zoom')
await shot(page.locator('[data-couches-toggle]'), 'p1_couches_entete_zoom')
await shot(page.locator('[data-filtres-toggle]'), 'p1_filtres_entete_zoom')

// ── ouvrir la section Filtres ──
await page.locator('[data-filtres-toggle]').click()
await page.waitForTimeout(1200)
await shot(aside, 'p2_panneau_filtres_ouvert')

// ── P2 : les deux boutons de fin de filtres (état appel) + P9 : bouton reset ──
const drawer = page.locator('[data-filtres-drawer]')
await shot(page.locator('[data-appel]'), 'p2_deux_boutons_zoom')
const reset = drawer.locator('button', { hasText: 'Réinitialiser' }).last()
await reset.scrollIntoViewIfNeeded().catch(() => {})
await shot(reset, 'p9_bouton_reset_zoom')

// ── lancer l'analyse (rituel 3 s) puis « Voir les parcelles » ──
await page.locator('[data-analyser-btn]').click()
await page.waitForTimeout(3600)
await page.locator('[data-voir-parcelles]').click({ timeout: 10000 }).catch(async () => {
  console.log('! bouton voir-parcelles absent, état :', await page.locator('[data-appel],[data-phrase],[data-decompte]').count())
})
await page.waitForTimeout(2500)

// ── P3 : barre TRIER · P4 : ligne « pourquoi ? » · P5 : ligne propriétaires ──
await shot(aside, 'p3_resultats_panneau')
await shot(page.locator('[data-tri-bar]'), 'p3_tri_bar_zoom')
await shot(page.locator('[data-entonnoir-btn]').locator('..'), 'p4_ligne_pourquoi_zoom')
await shot(page.locator('[data-dossiers-detail]'), 'p5_ligne_proprietaires_zoom')

// ── P10 : légende avec analyse active (zoom île → parcelles peintes ?) ──
await shotPage('p10_analyse_carte_ile')

// ── P6 : la modale « Comprendre le classement » ──
await page.locator('[data-algo-open]').click()
await page.waitForTimeout(600)
await shot(page.locator('[data-algo-overlay] > div'), 'p6_modale_zoom')
await page.locator('[data-algo-overlay]').click({ position: { x: 10, y: 10 } })
await page.waitForTimeout(400)

// ── P7 : le panneau Filtres RÉ-OUVERT après analyse (reliquats) ──
await page.locator('[data-filtres-toggle]').click()
await page.waitForTimeout(1200)
await shot(aside, 'p7_panneau_post_analyse')
// scroller le tiroir pour voir les tiroirs pédagogiques
await drawer.evaluate((el) => { el.scrollTop = el.scrollHeight })
await page.waitForTimeout(400)
await shot(aside, 'p7_panneau_post_analyse_bas')

// ── P8 : le mode factuel (« Voir les N parcelles ») ──
// repartir propre : désactiver l'analyse puis choisir la voie factuelle
const desactiver = page.locator('[data-desactiver]')
if (await desactiver.count()) { await desactiver.click(); await page.waitForTimeout(800) }
await page.locator('[data-voir-factuel]').click({ timeout: 5000 }).catch(() => console.log('! bouton voir-factuel introuvable'))
await page.waitForTimeout(2500)
await shotPage('p8_mode_factuel_ecran')
await shot(aside, 'p8_mode_factuel_panneau')
await shot(page.locator('[data-tri-bar]'), 'p8_mode_factuel_tris_zoom')

// ── P11 : signaux deux niveaux (après) · P12 : libellés communes ──
await page.locator('[data-filtres-toggle]').click()
await page.waitForTimeout(1000)
await shot(page.locator('[data-signaux-vie]'), 'p11_signaux_niveau1')
const plus = page.locator('[data-signaux-plus]')
if (await plus.count()) {
  await plus.click(); await page.waitForTimeout(400)
  await shot(page.locator('[data-signaux-vie]'), 'p11_signaux_niveau2_ouvert')
}
await shot(page.locator('[data-communes-filtre]'), 'p12_communes_libelles')

// ── P13 : flash du bouton zoom (capture pendant les 180 ms) ──
const zoomBtn = page.locator('button[title="Zoomer"]')
await zoomBtn.click()
await shot(zoomBtn, 'p13_zoom_flash')
await page.waitForTimeout(400)
await shot(zoomBtn, 'p13_zoom_repos')

// ── Non-régression : rituel 3,0 s (mesuré) ──
await page.reload({ waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(800)
const t0 = Date.now()
await page.locator('[data-analyser-btn]').click()
await page.locator('[data-voir-parcelles]').waitFor({ timeout: 10000 })
console.log('rituel (clic → bouton Voir) :', Date.now() - t0, 'ms')

// ── Non-régression : VIEUX LIEN (clés des tiroirs retirés + niche sv) ──
await page.goto(BASE + '#f=1&sv=nu_pm,procedure&mm=5&bud=500000&smin=1000&al=1', { waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(1000)
const nicheVisible = await page.locator('[data-signaux-vie] :text("Nu détenu par société")').count()
const compteur = await page.locator('[data-compteur-vivant]').innerText().catch(() => 'absent')
console.log('vieux lien — niche auto-ouverte :', nicheVisible, '· compteur :', compteur)
await shot(aside, 'nr_vieux_lien')

// ── Non-régression : mobile 375 px ──
await page.setViewportSize({ width: 375, height: 720 })
await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
await shotPage('nr_mobile_accueil')
await page.locator('[data-couches-mobile]').click(); await page.waitForTimeout(800)
await shotPage('nr_mobile_tiroir')

console.log(`captures ${TAG} OK →`, OUT, '· console errors:', errors.length)
console.log(errors.slice(0, 5).join('\n'))
await browser.close()
