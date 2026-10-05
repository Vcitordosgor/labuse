// RECETTE-2 Lot T — captures des surfaces visibles. LABEL=avant|apres.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const LABEL = process.env.LABEL || 'apres'
const OUT = `/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5905/socle/'
const IDU = '97415000AM0097'
const PANEL = { x: 0, y: 0, width: 560, height: 980 }
const sleep = (ms) => new Promise(r => setTimeout(r, ms))
const b = await chromium.launch({ channel: 'chrome', headless: true })
const shot = async (n, p, clip) => { await p.screenshot({ path: `${OUT}/${n}.png`, clip }); console.log('shot', n, LABEL) }
async function open(mod) {
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } })
  await p.goto(`${BASE}#m=${mod}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 30000 }).catch(() => {})
  await sleep(1600)
  return p
}
const tryClick = async (p, sel) => { try { await p.click(sel, { timeout: 6000 }) } catch {} }
try {
  // T3 — Assemblage : Réinitialiser seul sur sa ligne après sélection d'une parcelle
  { const p = await open('assemblage'); await p.evaluate(i => window.__labuse.select(i), IDU); await sleep(1600)
    await shot('T3_assemblage', p, PANEL); await p.close() }
  // T3 — Pièges et risques : idem
  { const p = await open('risques'); await p.evaluate(i => window.__labuse.select(i), IDU); await sleep(2000)
    await shot('T3_pieges', p, PANEL); await p.close() }
  // T9 — Scan patrimoine : 2 portes sans bord gauche vert (entrée)
  { const p = await open('patrimoine'); await sleep(800); await shot('T9_scan_portes', p, PANEL); await p.close() }
  // T10 — Piscines : écran Périmètre, ligne « Toute l'île »
  { const p = await open('prospection-solaire'); await tryClick(p, '[data-solaire-mode="piscines"]'); await sleep(2200)
    await shot('T10_piscines_perimetre', p, PANEL); await p.close() }
  // T8 — Fiche parcelle : chevrons des tuiles (fiche ouverte par select)
  { const p = await open(''); await p.evaluate(i => window.__labuse.select(i), IDU); await sleep(3000)
    await shot('T8_fiche_chevrons', p, PANEL); await p.close() }
} finally { await b.close() }
