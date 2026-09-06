// OUTILS-FIX-1 — captures des 3 écrans touchés. LABEL=avant|apres ; OUT=dossier de sortie.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const LABEL = process.env.LABEL || 'apres'
const OUT = process.env.OUT || `/Users/openclaw/Desktop/labuse-fix1/docs/audit-2026-09/OUTILS-FIX-1/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5173/socle/'
const IDU = '97404000AP0126'   // parcelle avec fiche soleil + piscine (données réelles)

const b = await chromium.launch({ channel: 'chrome' })
const PANEL = { x: 0, y: 0, width: 540, height: 900 }   // le panneau outil (gauche) — lisible
const shot = async (name, page, clip) => { await page.screenshot({ path: `${OUT}/${name}_${LABEL}.png`, clip }); console.log('shot', name) }

async function open(mod) {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  await p.goto(`${BASE}#m=${mod}`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1500)
  return p
}

try {
  // 1) SOLAIRE — mode Piscines (A2 colonnes + A3 CSV + A5 courrier)
  {
    const p = await open('prospection-solaire')
    await p.click('[data-solaire-mode="piscines"]').catch(() => {})
    await p.waitForSelector('[data-piscines-row]', { timeout: 30000 }).catch(() => {})
    await p.waitForTimeout(1200)
    await shot('01_solaire_piscines', p, PANEL)
    // sélectionner 2 lignes → pont Courrier actif (A5)
    const cbs = await p.$$('[data-piscines-sel]')
    for (const cb of cbs.slice(0, 2)) await cb.click().catch(() => {})
    await p.waitForTimeout(400)
    await shot('02_solaire_piscines_courrier', p, PANEL)
    await p.close()
  }
  // 2) SOLAIRE — mode Ensoleillement, fiche soleil (A1 phrase inclinaison + A6 kWc servi)
  {
    const p = await open('prospection-solaire')
    await p.click('[data-solaire-mode="ensoleillement"]').catch(() => {})
    await p.waitForTimeout(600)
    await p.fill('[data-solaire-idu]', IDU).catch(() => {})
    await p.keyboard.press('Enter')
    await p.waitForSelector('[data-solaire-fiche]', { timeout: 30000 }).catch(() => {})
    await p.waitForTimeout(1500)
    await shot('03_solaire_fiche', p, PANEL)
    await p.close()
  }
  // 3) FAISABILITÉ — par critères (B1 tri serveur + B2 « N sur M, mieux ajustées d'abord »)
  {
    const p = await open('programme')
    await p.getByText('Trouver les parcelles').click({ timeout: 10000 }).catch(() => {})
    await p.waitForSelector('[data-prog-item]', { timeout: 40000 }).catch(() => {})
    await p.waitForTimeout(1500)
    await shot('04_faisabilite_criteres', p, PANEL)
    await p.close()
  }
  // 4) DENSIFIER — tableau complet (C1 colonne Surélévation retirée)
  {
    const p = await open('renouvellement')
    await p.getByText(/Ouvrir le tableau complet/).click({ timeout: 15000 }).catch(() => {})
    await p.waitForSelector('[data-densifier-row]', { timeout: 40000 }).catch(() => {})
    await p.waitForTimeout(1500)
    await shot('05_densifier_tableau', p)
    await p.close()
  }
} finally {
  await b.close()
}
