// M52-B — captures écran réel du SÉLECTEUR DE PROFIL « Vous cherchez ? » et des 3 états de liste.
// Le sélecteur vit dans le panneau gauche (mode verdict). On allume l'analyse, on clique chaque
// profil (nu / bâti / les deux) et on capture : (1) le sélecteur seul, (2) le panneau résultats
// entier (compteur « Retenues par l'analyse » + liste) pour prouver que la liste réagit.
// Usage : node capture_profil.mjs   (API dev déjà lancée, sert /socle/ sur :8010)
import { chromium } from 'playwright'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const BASE = process.env.BASE || 'http://127.0.0.1:8010'
const OUT = dirname(fileURLToPath(import.meta.url))
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const EXE = process.env.PW_EXE
  || '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell'

const browser = await chromium.launch({ executablePath: EXE })
const ctx = await browser.newContext({ viewport: { width: 1480, height: 1400 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()

await page.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' })
// allumer l'analyse LABUSE (le sélecteur n'apparaît qu'en mode verdict)
const on = page.locator('[data-verdict-on]')
await on.waitFor({ state: 'visible', timeout: 20000 })
await on.click()
const sel = page.locator('[data-profil-selecteur]')
await sel.waitFor({ state: 'visible', timeout: 20000 })
await sleep(1500) // compteurs /filtre (les 2 voies) + liste

const panel = page.locator('[data-results-panel]').first()

// état PAR DÉFAUT = « Les deux » (puce active à l'arrivée)
await sel.screenshot({ path: join(OUT, 'M52B_selecteur_defaut.png') })

const ETATS = [
  ['deux', 'les_deux'],
  ['nu', 'terrain_nu'],
  ['bati', 'bati'],
]
for (const [k, name] of ETATS) {
  await page.locator(`[data-profil="${k}"]`).click()
  await sleep(1600) // le compteur SQL des 2 voies se recale sur les filtres pré-appliqués
  await sel.screenshot({ path: join(OUT, `M52B_selecteur_${name}.png`) })
  await panel.screenshot({ path: join(OUT, `M52B_liste_${name}.png`) })
  const note = await page.locator('[data-profil-bati-note]').count()
  console.log(`✓ ${name} — étiquette bâti visible: ${k === 'bati' ? note > 0 : 'n/a'}`)
}

await browser.close()
console.log('done')
