// RADAR-VEILLE-1 — captures de recette. Build servi sous /socle/ (uvicorn :8000, flag dépôt agence ON).
// Une PAGE FRAÎCHE par section (les tiles carte d'une section ne doivent pas gêner la suivante).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/RADAR-VEILLE-1/captures'
fs.mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
const report = { errors: [] }
const newPage = async () => { const p = await ctx.newPage(); p.on('pageerror', (e) => report.errors.push(String(e).slice(0, 120))); return p }
const shot = async (p, n) => { await p.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log('  shot', n) }

// ── R1 — la fiche d'une annonce (fond opaque, comparaison marché reformulée) ──
{
  const p = await newPage()
  await p.goto(BASE + '#radar=1', { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('[data-radar-bien]', { timeout: 20000 })
  report.n_biens = await p.locator('[data-radar-bien]').count()
  const maison = p.locator('[data-radar-bien]', { hasText: 'Maison' })
  await ((await maison.count()) ? maison.first() : p.locator('[data-radar-bien]').first()).click()
  await p.waitForSelector('[data-radar-fiche]', { timeout: 10000 })
  await p.waitForTimeout(900)
  await shot(p, '01-radar-fiche')
  report.fiche_marche = await p.locator('[data-radar-sous-marche]').innerText().catch(() => null)
  await p.close()
}

// ── V1/V2/V3 — veille : entrée (sans titre) + annonces (Créer une veille + critères, sans événements) ──
{
  const p = await newPage()
  await p.goto(BASE + '#surveillance=parcelles', { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('[data-veille-retour]', { timeout: 15000 })
  await p.click('[data-veille-retour]'); await p.waitForSelector('[data-veille-porte]', { timeout: 8000 }); await p.waitForTimeout(400)
  await shot(p, '02-veille-entree')
  report.veille_titre_accueil = await p.locator('[data-surveillance-panel] h3').allInnerTexts()
  await p.click('[data-veille-porte="externe"]')
  await p.waitForSelector('[data-veille-ext-creer-ouvrir]', { timeout: 8000 }); await p.waitForTimeout(400)
  await shot(p, '03-veille-annonces')
  report.a_bouton_creer = await p.locator('[data-veille-ext-creer-ouvrir]').count()
  report.a_events_restants = await p.locator('[data-veille-ext-event]').count()   // 0 attendu (V3)
  await p.click('[data-veille-ext-creer-ouvrir]'); await p.waitForTimeout(400)
  await shot(p, '04-veille-annonces-formulaire')
  await p.close()
}

// ── R3 — le wizard admin « Déposer une annonce » (4 étapes ; flag ON) ──
{
  const p = await newPage()
  await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('aside button', { timeout: 15000 }); await p.waitForTimeout(800)
  await p.locator('aside button', { hasText: 'Radar' }).first().click()
  await p.waitForSelector('[data-depot-agence]', { timeout: 10000 })
  const wiz = p.locator('[data-depot-agence]')
  report.wizard_present = await wiz.count()
  await wiz.scrollIntoViewIfNeeded(); await shot(p, '05-depot-etape1')
  const html = fs.readFileSync('../qa/radar-html/ECH-1.html', 'utf-8')
  await p.fill('[data-depot-html]', html)
  await p.click('[data-depot-analyser]')
  await p.waitForSelector('[data-depot-etape="2"]', { timeout: 20000 }); await p.waitForTimeout(400)
  await wiz.scrollIntoViewIfNeeded(); await shot(p, '06-depot-etape2')
  await p.click('[data-depot-continuer-adresse]')
  await p.waitForSelector('[data-depot-etape="3"]', { timeout: 8000 })
  await p.fill('[data-depot-adresse]', '27 chemin Vidot, La Bretagne, 97490 Saint-Denis')
  await p.fill('[data-depot-agence-nom]', 'Agence Immo Transac')
  const idu = await ctx.request.get('http://127.0.0.1:8000/radar/biens?limit=80').then(r => r.json()).then(r => (r.biens || []).find(b => b.rattachement?.idu)?.rattachement?.idu).catch(() => null)
  report.idu_test = idu
  if (idu) { await p.fill('[data-depot-parcelle] input', idu); await p.waitForTimeout(800); await p.locator('[data-depot-parcelle] button').first().click().catch(() => {}) }
  await p.waitForTimeout(400); await wiz.scrollIntoViewIfNeeded(); await shot(p, '07-depot-etape3')
  if (await p.locator('[data-depot-publier]').isEnabled().catch(() => false)) {
    await p.click('[data-depot-publier]')
    await p.waitForSelector('[data-depot-etape="4"]', { timeout: 8000 }).catch(() => {})
    await p.waitForTimeout(400); await wiz.scrollIntoViewIfNeeded(); await shot(p, '08-depot-etape4')
    report.publie = await p.locator('[data-depot-etape="4"]').innerText().catch(() => null)
  }
  await p.close()
}

report.errors = report.errors.slice(0, 8)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
