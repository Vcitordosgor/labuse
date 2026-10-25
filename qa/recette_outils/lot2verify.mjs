import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const out = {}
await t.go(''); await t.wait(700)
// Radar (11) — overlay via porte
await page.evaluate(() => window.__labuse.setModule('communes')); await t.wait(1200)
const radarPorte = page.getByText("Marché des annonces (Radar)").first()
if (await radarPorte.count()) { await radarPorte.click(); await t.wait(2200) }
out.radar_vend90 = await page.getByText('Vend.90j').count()
out.radar_echec = await page.getByText("Échec", { exact: true }).count()
out.radar_lesTroisBassins = await page.getByText('Les Trois-Bassins').count()
out.radar_troisBassins = await page.getByText("Trois-Bassins", { exact: true }).count()
out.radar_capture = await page.locator('[data-radar-capture]').count()
await t.shot('P11-radar-apres')
// Etude (26) — section Activité retirée
await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(1500)
out.etude_parcourirFamille = await page.getByText('parcourir par famille').count()
out.etude_activiteEtudiee = await page.getByText('Activité étudiée').count()
await t.shotSel('aside', 'P26-27-etude-apres')
// Scan operations (14) — accordions
await page.evaluate(() => window.__labuse.setModule('patrimoine')); await t.wait(1000)
const porteOps = page.locator('[data-scan-porte="operations"]').first()
if (await porteOps.count()) { await porteOps.click(); await t.wait(2500) }
out.scan_promoteurs = await page.locator('[data-vp-promoteur]').count()
out.scan_opsVisibles = await page.locator('[data-vp-operation]').count()  // doit être 0 (repliés)
await t.shotSel('aside', 'P14-scan-ops-apres')
console.log(JSON.stringify(out))
await browser.close()
