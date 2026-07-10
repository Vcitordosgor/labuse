// AUTO-QA — page SEGMENTS (mandat moteur-segments-habitat, Lot 5).
//   BASE=http://127.0.0.1:8011/socle/ node qa/qa_segments.mjs
// Critères du mandat : la page charge, 3 presets (dont ≥ 1 « partiel ») filtrent et
// exportent non-vide, l'admin sauvegarde un preset dupliqué.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8011/socle/'
const API = new URL('/', BASE).href.replace(/\/$/, '')
const OUT = process.env.OUT || '../docs/design/captures/segments'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

// ── API d'abord : les 3 presets du parcours + export non-vide ──
const home = await (await fetch(`${API}/segments`)).json()
assert(home.presets.length >= 18, `GET /segments : ${home.presets.length} presets`)
const partiels = home.presets.filter((p) => p.disponibilite === 'partiel')
assert(partiels.length >= 1, `au moins un preset « partiel » (${partiels.length})`)

for (const slug of ['cuisinistes', 'termites-charpente', 'pv-residentiel']) {
  const rep = await (await fetch(`${API}/segments/query`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slug, limit: 5 }),
  })).json()
  assert(rep.count > 0, `${slug} : count ${rep.count} > 0`)
  const csv = await (await fetch(`${API}/segments/export`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slug }),
  })).text()
  const lignes = csv.trim().split('\n')
  assert(lignes.length > 1, `${slug} : export CSV non-vide (${lignes.length - 1} lignes)`)
  assert(/Parcelle \(IDU\);Commune/.test(lignes[0]), `${slug} : en-têtes CSV en français`)
  assert(!/propri[ée]taire|d[ée]nomination|siren/i.test(lignes[0]), `${slug} : zéro colonne nominative`)
}
// filtres modifiés à la volée (jamais persistés) : resserrer cuisinistes
const volee = await (await fetch(`${API}/segments/query`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ slug: 'cuisinistes', filtres: [{ cle: 'anciennete_mutation_mois', max: 3 }] }),
})).json()
const base = await (await fetch(`${API}/segments/query`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ slug: 'cuisinistes' }),
})).json()
assert(volee.count > 0 && volee.count <= base.count, `query à la volée resserre (${volee.count} ≤ ${base.count})`)
// clé inconnue → 422, jamais de SQL libre
const inj = await fetch(`${API}/segments/query`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ filtres: [{ cle: 'surface; DROP TABLE parcels--', min: 1 }] }),
})
assert(inj.status === 422, `clé de filtre inconnue → 422 (${inj.status})`)

// ── UI ──
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(2500)

// 1 — la page Segments charge depuis le rail
await page.locator('nav button[title="Segments"]').click()
await page.waitForSelector('[data-seg-page]', { timeout: 15000 })
assert((await page.locator('[data-seg-preset]').count()) >= 18, 'galerie : les presets s\'affichent')
assert((await page.locator('[data-seg-badge]', { hasText: 'partiel' }).count()) >= 1, 'badge « partiel » visible')
await page.screenshot({ path: `${OUT}/segments_galerie.png`, fullPage: true })

// 2 — preset COMPLET : builder, compteur, table, pas d'erreur
await page.locator('[data-seg-preset="cuisinistes"] [data-seg-preset-open]').click()
await page.waitForSelector('[data-seg-count]', { timeout: 20000 })
await page.waitForFunction(() => {
  const c = document.querySelector('[data-seg-count]')
  return c && c.textContent !== '—' && c.textContent.trim() !== '0'
}, { timeout: 20000 })
assert((await page.locator('[data-seg-row]').count()) > 0, 'cuisinistes : table remplie')
assert((await page.locator('[data-seg-map]').count()) === 1, 'cuisinistes : carte présente')
await page.screenshot({ path: `${OUT}/segments_builder.png` })

// 3 — export CSV depuis l'UI (téléchargement non-vide)
const dl = page.waitForEvent('download', { timeout: 20000 })
await page.locator('[data-seg-export]').click()
const file = await dl
assert((await file.createReadStream()) !== null && file.suggestedFilename().includes('occupants'),
  `export UI : ${file.suggestedFilename()}`)

// 4 — preset PARTIEL : filtres grisés « disponible prochainement », zéro crash
await page.locator('[data-seg-retour]').click()
await page.waitForSelector('[data-seg-preset="pv-residentiel"]')
await page.locator('[data-seg-preset="pv-residentiel"] [data-seg-preset-open]').click()
await page.waitForSelector('[data-seg-count]', { timeout: 20000 })
assert((await page.locator('[data-seg-filtre-off]').count()) >= 1, 'pv-residentiel : filtres grisés (sources absentes)')
assert((await page.locator('text=prochainement').count()) >= 1, 'mention « disponible prochainement »')
await page.screenshot({ path: `${OUT}/segments_partiel.png` })

// 5 — builder : modifier un filtre à la volée change le compteur
await page.locator('[data-seg-retour]').click()
await page.locator('[data-seg-preset="termites-charpente"] [data-seg-preset-open]').click()
await page.waitForFunction(() => document.querySelector('[data-seg-count]')?.textContent !== '—', { timeout: 20000 })
const n1 = await page.locator('[data-seg-count]').textContent()
await page.locator('[data-seg-filtre] input[placeholder="max"]').first().fill('1950')
await page.waitForTimeout(2500)
const n2 = await page.locator('[data-seg-count]').textContent()
assert(n1 !== n2, `filtre à la volée : ${n1} → ${n2}`)

// 6 — ADMIN : dupliquer le preset modifié → nouveau preset en galerie
const slugQa = `qa-copie-${Date.now().toString(36)}`
const reponses = [slugQa, 'Copie QA']                  // prompt slug PUIS prompt nom
page.on('dialog', (d) => d.accept(reponses.shift() ?? ''))
await page.locator('[data-seg-dupliquer]').click()
await page.waitForTimeout(1500)
await page.locator('[data-seg-retour]').click()
await page.waitForSelector(`[data-seg-preset="${slugQa}"]`, { timeout: 15000 })
assert(true, `admin : preset dupliqué « ${slugQa} » visible en galerie`)
// nettoyage : suppression par l'API (le preset QA ne doit pas rester)
const del = await fetch(`${API}/segments/presets/${slugQa}`, { method: 'DELETE' })
assert(del.ok, 'admin : preset QA supprimé (nettoyage)')

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('SEGMENTS — AUTO-QA VERTE')
