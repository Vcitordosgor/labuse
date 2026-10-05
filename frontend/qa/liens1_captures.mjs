// LIENS-1 — captures avant/après de l'EN-TÊTE de fiche (ligne de boutons + IDU/adresse/secteur).
// LABEL=avant|apres. Deux largeurs : fiche LARGE (pane 400) et fiche ÉTROITE (petit écran).
// Capture par CLIP (bbox) — pas d'attente de stabilité d'élément (la carte maplibre repeint en continu).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const LABEL = process.env.LABEL || 'apres'
const BASE = process.env.BASE || 'http://localhost:6025/socle/'
const IDU = process.env.IDU || '97411000BZ1065'
const OUT = `/Users/openclaw/Desktop/labuse-liens/captures/LIENS-1`
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch({ channel: 'chrome' })

async function capture(nom, width, height) {
  const page = await b.newPage({ viewport: { width, height } })
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(1200)
  await page.evaluate((idu) => window.__labuse.select(idu), IDU)
  const tete = page.locator('.fiche-v6 [data-fiche-tete-collee]').first()
  await tete.waitFor({ timeout: 20000 }).catch(() => {})
  // attendre que la fiche (f) soit CHARGÉE : le lien Google Earth n'existe que dans le bloc `f && …`
  // (en AVANT, ce lien n'existe pas → on attend l'adresse rendue à la place).
  await page.locator('.fiche-v6 [data-fiche-tete-collee] [data-earth-link]').first().waitFor({ timeout: 25000 })
    .catch(async () => { await page.locator('.fiche-v6 [data-fiche-adresse]').first().waitFor({ timeout: 25000 }).catch(() => {}) })
  await page.waitForTimeout(1500)
  // fige animations + masque la carte (repeint sans fin) pour un rendu net
  await page.addStyleTag({ content: '*{animation:none!important;transition:none!important} .maplibregl-map,canvas{visibility:hidden!important}' })
  await page.waitForTimeout(300)
  const box = await tete.boundingBox()
  if (!box) { console.log('PAS DE BBOX', nom); await page.close(); return }
  const pad = 6
  await page.screenshot({
    path: `${OUT}/${nom}_${LABEL}.png`,
    clip: { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: box.width + pad * 2, height: box.height + pad * 2 },
  })
  const row = await page.evaluate(() => {
    const r = document.querySelector('.head-actions')
    const btns = document.querySelectorAll('.fiche-v6 [data-fiche-tete-collee] .hbtn')
    return { overflow: r ? r.scrollWidth - r.clientWidth : null, nBtns: btns.length,
             allFull: Array.from(btns).every((x) => Math.round(x.getBoundingClientRect().width) === 26) }
  })
  console.log(`shot ${nom}_${LABEL}  pane=${Math.round(box.width)}  overflow=${row.overflow}  boutons=${row.nBtns}  pleineTaille=${row.allFull}`)
  await page.close()
}

await capture('entete-large', 1440, 1000)
await capture('entete-etroite', 390, 900)

await b.close()
console.log('DONE', LABEL)
