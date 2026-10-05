// RECETTE-2 T1/T2 — doublon « ou cliquez une parcelle » + invite encore visible après clic carte.
// LABEL=avant|apres. Prouve : une seule invite dans l'entrée ; après un clic carte (window.__labuse.select)
// l'invite/chemin non utilisé grise, aucune invite grisée-mais-visible en double.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const LABEL = process.env.LABEL || 'apres'
const OUT = `/Users/openclaw/Desktop/labuse-recette2/docs/audit-2026-10/RECETTE-2/captures/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5905/socle/'
const IDU = '97415000AM0097'   // témoin Saint-Paul
const PANEL = { x: 0, y: 0, width: 560, height: 960 }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await chromium.launch({ channel: 'chrome', headless: true })
const shot = async (name, page, clip) => { await page.screenshot({ path: `${OUT}/${name}.png`, clip }); console.log('shot', name, '→', LABEL) }
async function open(mod) {
  const p = await b.newPage({ viewport: { width: 1440, height: 980 } })
  await p.goto(`${BASE}#m=${mod}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 30000 }).catch(() => {})
  await sleep(1800)
  return p
}

async function entreeThenClic(mod, tag) {
  const p = await open(mod)
  // 1) entrée vierge : combien d'invites « cliquez une parcelle » visibles ?
  const nInvite0 = await p.getByText(/cliquez une parcelle/i).count().catch(() => 0)
  console.log(`${tag} entrée — invites « cliquez une parcelle » visibles :`, nInvite0)
  await shot(`${tag}_01_entree`, p, PANEL)
  // 2) clic carte simulé → la parcelle est résolue par la carte (source=carte)
  await p.evaluate((i) => window.__labuse.select(i), IDU).catch((e) => console.log('select fail', e.message))
  await sleep(1800)
  const nInvite1 = await p.getByText(/cliquez une parcelle/i).count().catch(() => 0)
  console.log(`${tag} après clic carte — invites « cliquez une parcelle » (DOM) :`, nInvite1)
  await shot(`${tag}_02_apres_clic`, p, PANEL)
  await p.close()
}

try {
  await entreeThenClic('taxe-amenagement', 'T12_taxe')
  await entreeThenClic('prospection-solaire', 'T12_solaire')
  await entreeThenClic('temps', 'T12_temps')
  await entreeThenClic('gabarit', 'T12_gabarit')
} finally {
  await b.close()
}
