/**
 * RETOURS-23 — captures « après » des NEUF sections dépliées, à la largeur réelle du panneau (400 px).
 * AUCUN backend : harness statique (retours23_harness.html) + CSS RÉEL COMPILÉ de l'app
 * (dist/assets/index-*.css → tokens + classes .fiche-v6). Rien ne touche à la base (consigne).
 *   cd frontend && node qa/retours23_shots.mjs
 */
import { chromium } from 'playwright'
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const FRONT = path.resolve(HERE, '..')
const OUT = path.resolve(FRONT, '..', 'docs', 'audit-2026-09', 'RETOURS-23', 'captures')
const NAMES = ['01-reglement', '02-constructibilite', '03-risques', '04-marche', '05-reseaux',
  '06-autour', '07-dispositifs', '08-proprietaire', '09-donnees']

async function main() {
  await mkdir(OUT, { recursive: true })
  const cssFile = (await readdir(path.join(FRONT, 'dist', 'assets'))).find((f) => /^index-.*\.css$/.test(f))
  if (!cssFile) throw new Error('CSS compilé introuvable — `npx vite build` d’abord.')
  const cssAbs = path.join(FRONT, 'dist', 'assets', cssFile)
  const html = (await readFile(path.join(HERE, 'retours23_harness.html'), 'utf8')).replace('__CSS__', pathToFileURL(cssAbs).href)
  const tmp = path.join(HERE, '.retours23_harness.built.html')
  await writeFile(tmp, html)

  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const page = await (await browser.newContext({ viewport: { width: 440, height: 1400 }, deviceScaleFactor: 2 })).newPage()
  page.on('console', (m) => { if (m.type() === 'error') console.log('[page-error]', m.text()) })
  await page.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)

  const sections = await page.locator('.panel > section').all()
  if (sections.length !== NAMES.length) console.log(`⚠ ${sections.length} sections vues, ${NAMES.length} attendues`)
  for (let i = 0; i < sections.length; i++) {
    const file = path.join(OUT, `${NAMES[i]}.png`)
    await sections[i].screenshot({ path: file })
    console.log('✓', file)
  }
  // panneau complet (les 9 empilées)
  await page.locator('.panel').screenshot({ path: path.join(OUT, '00-panneau-complet.png') })
  console.log('✓ 00-panneau-complet.png')
  await browser.close()
}
main().catch((e) => { console.error(e); process.exit(1) })
