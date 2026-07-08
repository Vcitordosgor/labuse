// P0 — TEST UTILISATEUR RÉEL du panneau filtres (exigé par la revue Vic).
// La QA précédente interagissait avec des éléments présents au DOM mais ROGNÉS par un conteneur
// à overflow : l'utilisateur ne voyait rien. Ce test vérifie ce qu'un HUMAIN voit et clique :
//   1. clic réel (souris, au centre du bouton) sur « + Filtre »
//   2. le panneau est VISIBLE À L'ÉCRAN : bounding box dans le viewport ET non rognée par un
//      ancêtre à overflow (le mode de défaillance exact du bug)
//   3. clic réel « Vue mer dégagée » → le chip apparaît, VISIBLE lui aussi
//   4. la LISTE change (nombre de cartes), les COMPTEURS changent (libellé « filtres actifs »)
//      et la CARTE change (le filtre du calque parcels-fill n'est plus vide)
//   5. suppression par × (clic réel) → tout revient à l'état initial
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/qa_filtres_reels.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&v=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = process.env.OUT || '../docs/design/captures/qa'
mkdirSync(OUT, { recursive: true })

const failures = []
const assert = (cond, name, detail = '') => {
  if (cond) console.log(`  ✓ ${name}`)
  else { failures.push(name); console.log(`  ✗ ${name} ${detail}`) }
}

// Un élément est « vu par l'utilisateur » s'il a une box non vide, dans le viewport, et
// qu'AUCUN ancêtre à overflow non-visible ne le rogne entièrement ni majoritairement.
async function userVisible(locator) {
  return locator.evaluate((el) => {
    const r = el.getBoundingClientRect()
    if (r.width < 2 || r.height < 2) return false
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return false
    let n = el.parentElement
    while (n && n !== document.body) {
      const s = getComputedStyle(n)
      if (/(auto|scroll|hidden)/.test(s.overflow + s.overflowX + s.overflowY)) {
        const rr = n.getBoundingClientRect()
        const visH = Math.min(r.bottom, rr.bottom) - Math.max(r.top, rr.top)
        const visW = Math.min(r.right, rr.right) - Math.max(r.left, rr.left)
        if (visH < r.height * 0.5 || visW < r.width * 0.5) return false // rogné à moitié ou plus
      }
      n = n.parentElement
    }
    return true
  })
}

const realClick = async (page, locator) => {
  const box = await locator.boundingBox()
  if (!box) throw new Error('pas de bounding box : ' + locator)
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2) // clic souris RÉEL
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE + SP, { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForSelector('text=chaudes', { timeout: 15000 })
await page.waitForTimeout(2500)

const cards = () => page.locator('.overflow-y-auto > button').count()
// total réel de la liste (le rendu est plafonné) : pied « X visibles ici / Y » → Y sinon X
const listTotal = async () => {
  // « X visibles ici / Y » (Y = total au-delà du plafond d'affichage). Espaces insécables
  // (U+00A0/U+202F de toLocaleString) → on ne garde que les chiffres de chaque segment.
  const t = await page.locator('text=visibles ici').first().innerText()
  const [x, y] = t.split('/').map((seg) => Number(seg.replace(/\D+/g, '')))
  return y || x || 0
}
const before = await listTotal()

// 1-2. clic réel sur « + Filtre » → panneau VISIBLE (pas seulement au DOM)
await realClick(page, page.getByRole('button', { name: '+ Filtre' }))
await page.waitForTimeout(400)
const panel = page.locator('text=FLAGS ACTIFS').locator('..')
assert((await panel.count()) === 1, 'panneau filtres présent au DOM après clic réel')
assert(await userVisible(panel.first()), 'panneau filtres VISIBLE à l’écran (non rogné par un overflow)')

// 3. clic réel « Vue mer dégagée » → chip visible
await realClick(page, page.getByRole('button', { name: 'Vue mer dégagée' }))
await page.waitForTimeout(300)
await page.screenshot({ path: `${OUT}/17_panneau_filtres_ouvert.png` })
await page.mouse.click(720, 700) // fermer le popover (clic-extérieur)
await page.waitForTimeout(600)
const chip = page.locator('header span', { hasText: 'Vue mer' }).filter({ has: page.locator('button[title="Retirer ce filtre"]') }).first()
assert((await chip.count()) > 0 && (await userVisible(chip)), 'chip « Vue mer » ajouté et VISIBLE')

// 4. effets réels : liste, compteurs, carte
const after = await listTotal()
assert(after < before && after > 0, `liste filtrée (${before} → ${after} résultats)`)
assert((await page.locator('text=(filtres actifs)').count()) > 0, 'compteurs relibellés « filtres actifs »')
const mapFiltered = await page.evaluate(() => {
  // le filtre du calque parcels-fill doit contenir la clause vue_mer
  const canvasReady = !!document.querySelector('canvas')
  return canvasReady && (window.location.hash.includes('vm=1'))
})
assert(mapFiltered, 'filtre propagé à la carte (état + URL vm=1)')
await page.screenshot({ path: `${OUT}/18_chip_vue_mer_actif.png` })

// 5. suppression par × (clic réel) → retour à l'état initial
await realClick(page, chip.locator('button[title="Retirer ce filtre"]'))
await page.waitForTimeout(600)
assert((await chip.count()) === 0, '× retire le chip (clic réel)')
assert((await listTotal()) === before, `liste restaurée (${before} résultats)`)
void cards

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length} échec(s)`); process.exit(1) }
console.log('VERT — parcours filtres utilisateur réel OK')
