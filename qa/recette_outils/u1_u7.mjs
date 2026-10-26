// RECETTE-OUTILS-4 — U1 + U7 : l'export PDF de l'OUTIL Étude de zone transmet l'activité choisie, à
// l'identique de l'export depuis Docs. On intercepte LIVE l'URL /etude-zone.pdf émise par chaque
// chemin (outil / Docs) × chaque activité (toutes / Restauration), et on capture l'écran de l'outil
// avec « Restauration » choisie. Les 4 URLs sont imprimées pour être rejouées au PDF (diff texte).
import { launch, mk } from './lib.mjs'

const IDU = '97411000BZ1281'
const seen = []
const { browser, page } = await launch()
const t = mk(page)
page.on('request', (r) => { const u = r.url(); if (u.includes('etude-zone.pdf')) seen.push(u) })

async function lireEtExporter() {
  // (re)lire la zone puis cliquer l'export de l'outil ; attend la nouvelle requête .pdf
  const avant = seen.length
  await page.locator('text=Lire la zone').first().click({ timeout: 8000 }).catch(() => {})
  await page.waitForSelector('[data-zone-section]', { timeout: 20000 }).catch(() => {})
  await t.wait(600)
  await page.locator('[data-etude-export]').first().click({ timeout: 8000 })
  await page.waitForFunction((n) => true, {}, 0).catch(() => {})
  for (let i = 0; i < 40 && seen.length === avant; i++) await t.wait(250)
  return seen[seen.length - 1]
}

try {
  // ───────── OUTIL ─────────
  await t.go('')
  await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(1000)
  const inp = page.locator('[data-zone-point] input, input[placeholder*="Adresse"]').first()
  await inp.fill(IDU); await t.wait(1200); await page.keyboard.press('Enter'); await t.wait(1000)
  await page.locator('[data-zone-rayon="1"]').first().click().catch(() => {})
  await t.wait(400)
  // activité = toutes (défaut '')
  await page.selectOption('[data-destination-select="etude-zone"]', '').catch(() => {})
  await t.wait(300)
  const outilToutes = await lireEtExporter()
  // activité = Restauration (re-arme « Lire la zone »)
  await page.selectOption('[data-destination-select="etude-zone"]', 'restauration').catch(() => {})
  await t.wait(500)
  await t.shotSel('aside', 'U1-outil-restauration')   // LIVE : outil avec « Restauration »
  const outilResto = await lireEtExporter()

  // ───────── DOCS ─────────
  async function docsExport(dest) {
    const avant = seen.length
    await page.evaluate(() => window.__labuse.setView('documents')); await t.wait(1000)
    await page.locator('button:has-text("Étude de zone")').first().click({ timeout: 8000 })
    await t.wait(700)
    const di = page.locator('input[placeholder]').last()
    await di.fill(IDU); await t.wait(1200); await page.keyboard.press('Enter'); await t.wait(1200)
    await page.locator('[role="dialog"], .fixed').locator('text=/^1 km$/').first().click({ timeout: 5000 }).catch(() => {})
    await t.wait(300)
    await page.selectOption('[data-destination-select="doc-etude-zone"]', dest).catch(() => {})
    await t.wait(400)
    if (dest === 'restauration') await t.shot('U1-docs-restauration')
    await page.locator('button:has-text("Générer l’étude de zone"), button:has-text("Générer l\'étude de zone")').first().click({ timeout: 8000 })
    for (let i = 0; i < 60 && seen.length === avant; i++) await t.wait(250)
    return seen[seen.length - 1]
  }
  const docsToutes = await docsExport('')
  const docsResto = await docsExport('restauration')

  console.log('URLS=' + JSON.stringify({ outilToutes, outilResto, docsToutes, docsResto }, null, 0))
} catch (e) {
  console.log('ERREUR', String(e))
  console.log('SEEN=' + JSON.stringify(seen))
} finally {
  await browser.close()
}
