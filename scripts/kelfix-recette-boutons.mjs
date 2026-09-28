// FICHE-FIX-4 (Lot M) — recette des boutons de la fiche : pour chaque bouton d'outil (data-porte),
// ouvrir sa section, cliquer, lire l'état du store, remettre à zéro. Sortie = tableau texte.
import pkg from '/Users/openclaw/Desktop/labuse-kelfix/frontend/node_modules/playwright-core/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5745/socle/'
const IDU = process.argv[2] || '97415000AB0134'

// (section tiroir, data-porte, attendu lisible) — FICHE-FIX-5 : boutons mis à jour.
const BTNS = [
  ['identite', 'patrimoine', 'module=patrimoine'],
  ['identite', 'spf-letter', 'module=courriers'],
  ['urbanisme', 'annuaire', 'module=plu'],
  ['urbanisme', 'verif-procedure', 'module=plu'],
  ['urbanisme', 'simuler-ouverture', 'module=plu'],
  ['risques', 'risques', 'module=risques'],
  ['fiscalite', 'taxe-amenagement-outil', 'module=taxe-amenagement'],
  ['marche', 'communes', 'module=communes'],
  ['quartier', 'etude-chalandise', 'module=etude-zone'],
  ['quartier', 'etude-particulier', 'module=etude-zone'],
  ['quartier', 'permis', 'module=permis'],
  ['quartier', 'fiche-commune', 'contexteCommune set'],
  ['potentiel', 'densifier-filtre', 'filtres ouverts'],
  ['potentiel', 'gabarit', 'module=programme'],
  ['simulation', 'faisabilite-outil', 'module=programme'],
  ['simulation', 'calculette', 'module=calculette-fonciere'],
  ['simulation', 'assemblage-outil', 'module=assemblage'],
]

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' })
const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } })
await page.goto(`${BASE}#f=1&idu=${IDU}`, { waitUntil: 'domcontentloaded' })
await page.evaluate(async (idu) => { const m = await import('/socle/src/store/useApp.ts'); const s = m.useApp.getState(); s.setView('cartes'); s.select(idu) }, IDU)
await page.waitForSelector('.fiche-v6 [data-drawer]', { timeout: 15000 })
await page.waitForTimeout(1500)

console.log(`IDU ${IDU}`)
console.log('section         | data-porte            | attendu                       | constaté')
for (const [tiroir, porte, attendu] of BTNS) {
  const r = await page.evaluate(async ({ tiroir, porte, idu }) => {
    const m = await import('/socle/src/store/useApp.ts')
    const st = m.useApp
    // reset : reséléctionne la parcelle, ferme module/compare/contexte, ouvre le tiroir voulu
    const s0 = st.getState(); s0.setView('cartes'); s0.select(idu); s0.setModule(null); if (s0.compareOpen) s0.openCompare(); s0.setContexteCommune(null); s0.setFicheTiroir(idu, tiroir)
    await new Promise((res) => setTimeout(res, 250))
    const btn = document.querySelector(`.fiche-v6 [data-drawer="${tiroir}"] [data-porte="${porte}"]`)
    if (!btn) return { found: false }
    btn.click()
    await new Promise((res) => setTimeout(res, 150))
    const s = st.getState()
    return { found: true, module: s.module, compareOpen: s.compareOpen, contexteCommune: s.contexteCommune, view: s.view }
  }, { tiroir, porte, idu: IDU })
  const got = !r.found ? 'ABSENT du DOM'
    : `module=${r.module ?? '∅'}${r.compareOpen ? ' compareOpen' : ''}${r.contexteCommune ? ` contexte=${r.contexteCommune}` : ''}`
  console.log(`${tiroir.padEnd(15)} | ${porte.padEnd(21)} | ${attendu.padEnd(29)} | ${got}`)
}
await browser.close()
