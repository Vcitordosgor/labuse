// FICHE-1 — captures avant/après de la fiche parcelle. LABEL=avant|apres.
// 3 parcelles : bâtie (DPE+PPR), nue, dans le rayon TCSP.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const LABEL = process.env.LABEL || 'apres'
const OUT = `/Users/openclaw/Desktop/labuse-audit/docs/RECETTE/FICHE-1/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5173/socle/'

// tiroir ids (data-drawer) : le_bien, risques, faisabilite (Constructibilité), marche, viab (Réseaux)
const PARCELLES = [
  { idu: '97411000AC0079', tag: 'batie_dpe_ppr', tiroirs: ['faisabilite', 'le_bien', 'risques', 'marche'] },
  { idu: '97401000AI0073', tag: 'nue', tiroirs: ['faisabilite', 'le_bien'] },
  { idu: '97415000AB0790', tag: 'tcsp', tiroirs: ['viabilisation', 'le_bien'] },
]

const b = await chromium.launch({ channel: 'chrome' })
const page = await b.newPage({ viewport: { width: 1440, height: 1300 } })
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1500)

const shot = async (name, loc) => {
  try { await (loc || page).screenshot({ path: `${OUT}/${name}_${LABEL}.png` }); console.log('shot', name) }
  catch (e) { console.log('shot FAIL', name, e.message) }
}

for (const p of PARCELLES) {
  try {
    await page.evaluate((idu) => window.__labuse.select(idu), p.idu)
    const fiche = page.locator('.fiche-v6').first()
    await fiche.waitFor({ timeout: 20000 }).catch(() => {})
    // attendre la FIN du chargement : au moins un tiroir rendu
    await page.waitForSelector('[data-drawer]', { timeout: 40000 }).catch(() => console.log('no drawer appeared', p.idu))
    await page.waitForTimeout(1500)
    await shot(`${p.tag}_00_fiche`, fiche)
    for (const t of p.tiroirs) {
      const drawer = page.locator(`[data-drawer="${t}"]`).first()
      if (!(await drawer.count())) { console.log('no drawer', p.tag, t); continue }
      await drawer.scrollIntoViewIfNeeded().catch(() => {})
      await drawer.locator('button.tiroir').first().click({ timeout: 8000 }).catch(() => {})
      await page.waitForTimeout(1000)
      await shot(`${p.tag}_${t}`, drawer)
    }
  } catch (e) { console.log('parcelle FAIL', p.idu, e.message) }
}

await b.close()
console.log('DONE', LABEL)
