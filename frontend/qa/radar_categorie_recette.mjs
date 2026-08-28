// RADAR-CATÉGORIE (T6) — RECETTE du geste complet, sur le jeu [RADAR-TEST] (seed_recette.sql).
// Exerce : filtre commune réel · tri baisses · fiche rattachée + 6 tuiles · fiche non rattachée
// SANS outils · état vide filtré · veille externe créée qui matche (puis supprimée) · veille interne
// intacte. Usage : node qa/radar_categorie_recette.mjs  (vite dev + seed requis). Exit 1 si échec.
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://[::1]:5174/socle/'
let fails = 0
const check = (cond, label) => { console.log(`${cond ? '✓' : '✗'} ${label}`); if (!cond) fails++ }

const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
const go = async (h = '') => {
  await p.goto(BASE + h, { waitUntil: 'networkidle', timeout: 60000 })
  if (h.includes('radar')) await p.waitForSelector('[data-radar-commune]', { timeout: 20000 })
  await p.waitForTimeout(1200)
}

// ── Radar catégorie : plein écran, plus dans les Outils ──
await go('#radar=1')
check(await p.locator('[data-radar-panel]').count() === 1, 'la catégorie Radar s\'ouvre en plein écran (#radar=1)')
check((await p.locator('[data-radar-bien]').count()) >= 6, 'le listing affiche les biens du jeu de test')

// Radar a QUITTÉ le menu Outils
await p.locator('button[title="Outils"]').click(); await p.waitForTimeout(600)
check(await p.locator('[data-outil="radar"]').count() === 0, 'plus d\'entrée « Radar » dans le menu Outils')
// revenir à la catégorie Radar via le rail (l'entrée de premier niveau)
await p.locator('button[title="Radar"]').click(); await p.waitForSelector('[data-radar-commune]', { timeout: 20000 }); await p.waitForTimeout(1000)

// ── T2 : filtre commune réel (bug corrigé) ──
await p.locator('[data-radar-commune]').selectOption({ label: 'Les Avirons' }); await p.waitForTimeout(1200)
check(await p.locator('[data-radar-bien]').count() === 2, 'filtre commune « Les Avirons » → 2 biens')
await p.locator('[data-radar-commune]').selectOption(''); await p.waitForTimeout(1000)

// ── T2 : tri baisses (le bien 900001 a une baisse) ──
await p.locator('select').last().selectOption('baisses'); await p.waitForTimeout(1200)
check(await p.locator('[data-radar-bien="900001"]').count() === 1, 'tri « Baisses » remonte le bien en baisse (900001)')

// ── T2 : état vide filtré ──
await p.locator('[data-radar-panel] input[placeholder="Prix min"]').fill('99000000'); await p.waitForTimeout(1200)
check(await p.getByText('Aucun bien ne correspond').count() > 0, 'filtre impossible → « Aucun bien ne correspond »')
await p.locator('[data-radar-panel] input[placeholder="Prix min"]').fill(''); await p.waitForTimeout(1000)

// ── T3 : fiche d'un bien RATTACHÉ (900001) → 6 tuiles + parcelle + portail ──
await p.locator('[data-radar-bien="900001"]').click(); await p.waitForTimeout(2000)
check(await p.locator('[data-radar-fiche]').count() === 1, 'la fiche du bien rattaché s\'ouvre')
check(await p.locator('[data-radar-tuile]').count() === 6, 'ÉTUDIER CE BIEN : 6 tuiles')
check(await p.locator('[data-radar-parcelle]').count() === 1, 'bloc PARCELLE RATTACHÉE présent')
check(await p.locator('[data-radar-portail]').count() === 1, 'bouton « Voir l\'annonce » présent')
check(await p.getByText('Baisse du').count() > 0, 'mention de baisse affichée')

// fermer la fiche rattachée
await p.locator('[data-radar-fiche] button[aria-label="Fermer"]').click(); await p.waitForTimeout(600)

// ── T3 : fiche d'un bien NON RATTACHÉ (900003 appartement) → PAS d'outils ni de parcelle ──
await p.locator('[data-radar-bien="900003"]').click(); await p.waitForTimeout(1500)
check(await p.locator('[data-radar-fiche]').count() === 1, 'la fiche d\'un bien non rattaché s\'ouvre (s\'arrête aux faits)')
check(await p.locator('[data-radar-tuile]').count() === 0, 'bien non rattaché : AUCUNE tuile « Étudier ce bien »')
check(await p.locator('[data-radar-parcelle]').count() === 0, 'bien non rattaché : PAS de bloc parcelle')
check(await p.locator('[data-radar-portail]').count() === 1, 'bien non rattaché : bouton portail présent (seul chemin sortant)')
await p.locator('[data-radar-fiche] button[aria-label="Fermer"]').click(); await p.waitForTimeout(600)

// ── T4 : veille EXTERNE créée qui matche, puis supprimée ──
await p.locator('[data-rail-surveillance]').click(); await p.waitForTimeout(600)
await p.locator('[data-veille-porte="externe"]').click(); await p.waitForTimeout(800)
await p.locator('[data-veille-ext-commune]').selectOption({ label: 'Saint-Paul' }); await p.waitForTimeout(300)
await p.locator('[data-veille-ext-creer]').click(); await p.waitForTimeout(1500)
const nVeilles = await p.locator('[data-veille-ext-item]').count()
check(nVeilles >= 1, 'veille externe créée et listée')
// la supprimer (ne rien laisser)
if (nVeilles >= 1) { await p.locator('[data-veille-ext-item] button').first().click(); await p.waitForTimeout(1000) }
check(await p.locator('[data-veille-ext-item]').count() < nVeilles, 'veille externe supprimée (aucune donnée de test résiduelle)')

// ── T4 : veille INTERNE intacte ──
await p.locator('[data-veille-retour]').click(); await p.waitForTimeout(400)
await p.locator('[data-veille-porte="interne"]').click(); await p.waitForTimeout(800)
check(await p.locator('[data-surveillance-boucle]').count() === 1, 'veille interne (le foncier) intacte : boucle + volets')
check(await p.locator('[data-volet="parcelles"]').count() === 1, 'volet Parcelles présent (interne inchangée)')

await b.close()
console.log(fails === 0 ? 'RECETTE RADAR : VERTE' : `ÉCHECS : ${fails}`)
process.exit(fails === 0 ? 0 : 1)
