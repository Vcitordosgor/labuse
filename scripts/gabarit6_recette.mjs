// GABARIT-6 · recette navigateur (headless, profil isolé — ne touche pas au navigateur MCP).
// Capture le panneau outil + carte pour chaque parcelle de recette via le deep-link #m=gabarit&idu=…
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'
import path from 'node:path'

const BASE = 'http://localhost:5336/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-gabarit6/docs/GABARIT/captures/gabarit-6'
const TAG = process.argv[2] || 'apres'
const ONLY = process.argv[3] ? process.argv[3].split(',') : null   // filtre optionnel par nom

const SPECS_ALL = [
  ['citerne-bz1065',       '97411000BZ1065'],   // 3 Chemin de la Citerne, Saint-Denis — LA vraie parcelle
  ['servie-irreguliere-1', '97411000CV0740'],   // contour très irrégulier (52 sommets), servie
  ['servie-irreguliere-2', '97415000CT2639'],   // contour irrégulier, servie
  ['servie-irreguliere-3', '97409000AV0323'],   // contour irrégulier, servie
  ['bloquee-autre-cause',  '97411000EV0332'],   // Saint-Denis : 1 arête rattachée MAIS bloc autre limite (ravine)
]
const SPECS = ONLY ? SPECS_ALL.filter(([n]) => ONLY.includes(n)) : SPECS_ALL

const browser = await chromium.launch({
  headless: true,
  executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
})
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()

for (const [name, idu] of SPECS) {
  // FLUX OUTIL PUR (comme le mandat) : on ouvre l'outil SANS #idu (donc SANS fiche), puis on saisit
  // l'IDU dans le champ de l'outil + Entrée → onPick → l'outil interroge, la fiche ne s'ouvre pas.
  // C'est le seul flux où « écran vide en cas de bloc » se voit (le clic-carte, lui, ouvre la fiche
  // qui trace déjà la parcelle).
  await page.goto(`${BASE}?r=${encodeURIComponent(name)}#m=gabarit`, { waitUntil: 'networkidle' })
  const input = await page.waitForSelector('[data-gabarit-parcelle]', { timeout: 20000 })
  await input.click()
  await input.fill(idu)
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-gabarit-chiffres],[data-gabarit-incomplet]', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(2500)   // laisse la carte se caler (fitBounds) + tuiles
  const file = path.join(OUT, `recette-${name}-${TAG}.png`)
  await page.screenshot({ path: file, fullPage: false })
  const st = await page.$('[data-gabarit-incomplet]') ? 'incomplete' : (await page.$('[data-gabarit-chiffres]') ? 'ok' : '??')
  const ref = await page.$eval('[data-gabarit-parcelle-ref]', el => el.textContent).catch(() => null)
  console.log(`${name} (${idu}) → ${st}${ref ? ' | ' + ref.trim() : ''} → ${file}`)
}

await browser.close()
