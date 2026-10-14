/**
 * MAPLIBRE-1 — diff pixel avant/après (sans dépendance : décodage PNG via le canvas de Chromium).
 * Pour chaque scène : % de pixels dont l'écart max de canal dépasse un seuil (16/255) — ce seuil
 * écarte l'anti-crénelage. Affiche aussi l'écart moyen. LANCEMENT (depuis frontend/) :
 *   node scripts/maplibre1_diff.mjs [dossierAvant] [dossierApres]
 */
import { chromium } from 'playwright'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const EXE = process.env.PW_CHROME ||
  '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const AVANT = path.resolve(process.argv[2] || '../reports/maplibre1/avant_dev')
const APRES = path.resolve(process.argv[3] || '../reports/maplibre1/apres_dev')
const SEUIL = 16   // écart de canal (0-255) au-delà duquel un pixel « diffère » (hors anti-crénelage)

async function toDataUrl(p) { return 'data:image/png;base64,' + (await readFile(p)).toString('base64') }

async function main() {
  const scenes = (await readdir(AVANT)).filter((f) => f.endsWith('.png')).sort()
  const browser = await chromium.launch({ headless: true, executablePath: EXE })
  const page = await (await browser.newContext()).newPage()
  const rows = []
  for (const s of scenes) {
    try {
      const [a, b] = await Promise.all([toDataUrl(path.join(AVANT, s)), toDataUrl(path.join(APRES, s))])
      const r = await page.evaluate(async ({ a, b, seuil }) => {
        const load = (src) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src })
        const [ia, ib] = await Promise.all([load(a), load(b)])
        const w = Math.min(ia.width, ib.width), h = Math.min(ia.height, ib.height)
        const mk = (img) => { const c = new OffscreenCanvas(w, h); const x = c.getContext('2d'); x.drawImage(img, 0, 0); return x.getImageData(0, 0, w, h).data }
        const da = mk(ia), db = mk(ib)
        let diff = 0, somme = 0, n = w * h
        for (let i = 0; i < da.length; i += 4) {
          const dr = Math.abs(da[i] - db[i]), dg = Math.abs(da[i + 1] - db[i + 1]), dbl = Math.abs(da[i + 2] - db[i + 2])
          const m = Math.max(dr, dg, dbl); somme += (dr + dg + dbl) / 3
          if (m > seuil) diff++
        }
        return { w, h, dimA: [ia.width, ia.height], dimB: [ib.width, ib.height], pctDiff: diff / n * 100, moyen: somme / n }
      }, { a, b, seuil: SEUIL })
      rows.push({ scene: s, ...r })
      console.log(`${s.padEnd(26)} diff=${r.pctDiff.toFixed(3)}%  moyen=${r.moyen.toFixed(2)}/255  ${r.dimA.join('x')} vs ${r.dimB.join('x')}`)
    } catch (e) { console.log(`${s.padEnd(26)} ERREUR ${String(e).slice(0, 80)}`); rows.push({ scene: s, erreur: String(e).slice(0, 120) }) }
  }
  await browser.close()
  await writeFile(path.join(APRES, '_diff.json'), JSON.stringify(rows, null, 2))
  const max = rows.filter((r) => r.pctDiff != null).reduce((m, r) => Math.max(m, r.pctDiff), 0)
  console.log(`\nMax %diff = ${max.toFixed(3)}%  (seuil anti-crénelage ${SEUIL}/255)`)
}
main().catch((e) => { console.error(e); process.exit(1) })
