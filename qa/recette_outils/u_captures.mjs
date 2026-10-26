// RECETTE-OUTILS-4 — captures LIVE : U2 (% espacés), U3 (chevron 16 px, 3 menus), U4 (bâti déduit
// 40 m² à l'écran), U5 (sphère d'orientation 3D, 3 orientations), U6 (Copilote sans « Ce qu'il sait faire »).
import { launch, mk } from './lib.mjs'

const { browser, page } = await launch()
const t = mk(page)
const BZ = '97411000BZ1281', CM = '97415000CM1658'

async function fillOutilParcelle(idu) {
  const inp = page.locator('aside input[placeholder], [data-zone-point] input').first()
  await inp.fill(idu); await t.wait(1100); await page.keyboard.press('Enter'); await t.wait(1200)
}

try {
  // ───────── U6 — Copilote ─────────
  await t.go('')
  await page.evaluate(() => window.__labuse.setView('copilote')); await t.wait(1400)
  await t.shot('U6-copilote-accueil')
  const saitFaire = await page.locator('text=CE QU\'IL SAIT FAIRE').count()
  const exemples = await page.locator('[data-accueil-exemple]').count()
  console.log('U6 saitFaire=' + saitFaire + ' exemples=' + exemples)

  // ───────── U2 + U3(étude) — Étude de zone ─────────
  await page.evaluate(() => window.__labuse.setView('cartes')); await t.wait(500)
  await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(1000)
  await fillOutilParcelle(BZ)
  await page.locator('[data-zone-rayon="1"]').first().click().catch(() => {})
  await t.wait(300)
  await t.shotSel('[data-destination-select="etude-zone"]', 'U3-menu-activite')        // U3 menu 1
  await page.locator('text=Lire la zone').first().click().catch(() => {})
  await page.waitForSelector('[data-zone-section="contraintes"]', { timeout: 20000 }).catch(() => {})
  await page.locator('[data-zone-section-toggle="contraintes"]').first().click().catch(() => {})
  await t.wait(800)
  await t.shotSel('[data-zone-section="contraintes"]', 'U2-contraintes-pourcentages')   // U2

  // ───────── U3 — Périmètre (Blocs fonciers) ─────────
  await page.evaluate(() => window.__labuse.setModule('blocs-fonciers')); await t.wait(1200)
  await t.shotSel('[data-commune-scope]', 'U3-menu-perimetre-blocs')                     // U3 menu 2

  // ───────── U3 — Périmètre (Successions) ─────────
  await page.evaluate(() => window.__labuse.setModule('successions')); await t.wait(1200)
  await t.shotSel('[data-commune-scope]', 'U3-menu-perimetre-successions')               // U3 menu 3

  // ───────── U4 — Gabarit : bâti existant déduit : 40 m² ─────────
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await t.wait(1000)
  await fillOutilParcelle(CM)
  await page.waitForSelector('[data-gabarit-chiffres]', { timeout: 20000 }).catch(() => {})
  await t.wait(700)
  await t.shotSel('[data-gabarit-panel]', 'U4-gabarit-bati-deduit')
  const sub = await page.locator('[data-gabarit-chiffres]').first().innerText().catch(() => '')
  console.log('U4 chiffres=' + JSON.stringify(sub))

  // ───────── U5 — Sphère d'orientation 3D ─────────
  await page.locator('[data-gabarit-3d]').first().click(); await t.wait(2800)   // « Voir en 3D »
  const sphere = page.locator('[data-controle-3d]')
  if (await sphere.count()) {
    await page.screenshot({ path: 'reports/RECETTE-OUTILS-1/captures/U5-sphere-depart.png' })
    await t.shotSel('[data-controle-3d]', 'U5-sphere-closeup')
    // orientation 1 : clic E
    await page.locator('[data-c3d-e]').click(); await t.wait(1200)
    await page.screenshot({ path: 'reports/RECETTE-OUTILS-1/captures/U5-sphere-est.png' })
    // orientation 2 : clic S
    await page.locator('[data-c3d-s]').click(); await t.wait(1200)
    await page.screenshot({ path: 'reports/RECETTE-OUTILS-1/captures/U5-sphere-sud.png' })
    // orientation 3 : GLISSER dans la sphère (rotation + inclinaison)
    const box = await sphere.locator('[data-c3d-sphere]').boundingBox()
    if (box) {
      const cx = box.x + box.width / 2, cy = box.y + box.height / 2
      await page.mouse.move(cx, cy); await page.mouse.down()
      await page.mouse.move(cx + 45, cy - 18, { steps: 12 }); await page.mouse.up()
    }
    await t.wait(1000)
    await page.screenshot({ path: 'reports/RECETTE-OUTILS-1/captures/U5-sphere-glisser.png' })
    const orient = await page.evaluate(() => ({ b: Math.round(window.__labuse_map.getBearing()), p: Math.round(window.__labuse_map.getPitch()) }))
    console.log('U5 après glisser bearing/pitch=' + JSON.stringify(orient))
  } else {
    console.log('U5 ERREUR : sphère [data-controle-3d] absente')
  }
} catch (e) {
  console.log('ERREUR', String(e))
} finally {
  await browser.close()
}
