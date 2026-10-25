import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'apres'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
await page.evaluate(() => window.__labuse.setModule('communes')); await t.wait(1200)
const porte = page.getByText('Comparaison communes').first(); if (await porte.count()) { await porte.click(); await t.wait(2500) }
await t.shot(`R5-table-${SUF}`)
const fiche = page.getByText('Fiche →').first()
if (await fiche.count()) { await fiche.click(); await t.wait(2800) }
const tablePanel = await page.locator('[data-communes-table-panel]').count()
const tableVisible = tablePanel ? await page.locator('[data-communes-table-panel]').first().isVisible() : false
const fichePanel = await page.locator('[data-contexte-panel]').count()
const ficheVisible = fichePanel ? await page.locator('[data-contexte-panel]').first().isVisible() : false
await t.shot(`R5-fiche-over-${SUF}`)
// fermer la fiche (croix) → tableau intact
const croix = page.locator('[data-contexte-panel] button[aria-label="Fermer"], [data-contexte-panel] [aria-label*="ermer"]').first()
if (await croix.count()) { await croix.click(); await t.wait(1500) }
const tableApresFermeture = await page.locator('[data-communes-table-panel]').first().isVisible().catch(()=>false)
const ficheApresFermeture = await page.locator('[data-contexte-panel]').count()
await t.shot(`R5-table-retour-${SUF}`)
console.log(JSON.stringify({ tableVisible, ficheVisible, tableApresFermeture, ficheApresFermeture }))
await browser.close()
