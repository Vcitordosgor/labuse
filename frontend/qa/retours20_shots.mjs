/**
 * RETOURS-20 — captures « après » des deux sections (Règlement · Réseaux) à la largeur réelle du
 * panneau (400 px). AUCUN backend : le harness statique (retours20_harness.html) rend le DOM des
 * composants refondus avec le CSS RÉEL COMPILÉ de l'app (dist/assets/index-*.css) → tokens + classes
 * .fiche-v6. Rien ne touche à la base (consigne : ne pas lancer d'app de captures qui heale le schéma).
 *
 *   cd frontend && node qa/retours20_shots.mjs
 */
import { chromium } from 'playwright'
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const FRONT = path.resolve(HERE, '..')
const OUT = path.resolve(FRONT, '..', 'docs', 'audit-2026-09', 'RETOURS-20', 'captures')

async function main() {
  await mkdir(OUT, { recursive: true })
  const cssFile = (await readdir(path.join(FRONT, 'dist', 'assets'))).find((f) => /^index-.*\.css$/.test(f))
  if (!cssFile) throw new Error('CSS compilé introuvable — lance `npx vite build` d’abord.')
  const cssAbs = path.join(FRONT, 'dist', 'assets', cssFile)
  const html = (await readFile(path.join(HERE, 'retours20_harness.html'), 'utf8')).replace('__CSS__', pathToFileURL(cssAbs).href)
  const tmp = path.join(HERE, '.retours20_harness.built.html')
  await writeFile(tmp, html)

  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const page = await (await browser.newContext({ viewport: { width: 440, height: 1600 }, deviceScaleFactor: 2 })).newPage()
  page.on('console', (m) => { if (m.type() === 'error') console.log('[page-error]', m.text()) })
  await page.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)

  const sections = await page.locator('.panel > div').all()
  const names = ['reglement-apres', 'reseaux-apres']
  for (let i = 0; i < names.length; i++) {
    const el = sections[i * 2]   // les <div> de section alternent avec un spacer 16px
    const file = path.join(OUT, `${names[i]}.png`)
    await el.screenshot({ path: file })
    console.log('✓', file)
  }
  await browser.close()
}
main().catch((e) => { console.error(e); process.exit(1) })
