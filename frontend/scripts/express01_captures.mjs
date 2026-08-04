/**
 * EXPRESS-01 — captures de revue visuelle (Volet A : IDU complet + copier ; Volet B : bandeau AvisIA).
 *
 * PRÉREQUIS (côté opérateur) :
 *   cd frontend && npm i -D playwright && npx playwright install chromium
 *   # API (autre terminal) :
 *   #   cd ~/Desktop/labuse-express01
 *   #   LABUSE_DEV_MODE=1 PYTHONPATH=src ~/miniforge3/envs/labusedb/bin/python \
 *   #     -m uvicorn labuse.api.app:app --lifespan off
 *   # Front (autre terminal) : cd frontend && npm run dev
 *
 * LANCEMENT (depuis frontend/, pour résoudre node_modules/playwright) :
 *   BASE_URL=http://localhost:5173/socle/ IDU=97415000AT0737 node scripts/express01_captures.mjs
 *   # HEADED=1 pour voir le navigateur ; IDU = une parcelle RÉELLE de ta base.
 *
 * Le script pilote l'app via window.__labuse (exposé par App.tsx) — pas de sélecteurs de nav fragiles.
 * Chaque surface est best-effort : si un élément manque (surface non atteinte, endpoint IA muet),
 * on logue et on prend une capture pleine page en repli, sans abandonner les autres surfaces.
 */
import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.BASE_URL || 'http://localhost:5173/socle/'
const ORIGIN = new URL(BASE).origin
const IDU = process.env.IDU || '97415000AX1059'          // parcelle réelle de revue (défaut EXPRESS-01)
const OUT = process.env.OUT || path.resolve('..', 'reports', 'express-01', 'captures')
const HEADED = process.env.HEADED === '1'
const STEP_TIMEOUT = Number(process.env.STEP_TIMEOUT || 15000)

const log = (...a) => console.log('[capture]', ...a)

async function main() {
  await mkdir(OUT, { recursive: true })
  // macOS 13 : le chromium bundlé de Playwright n'est pas supporté → Chrome système.
  const browser = await chromium.launch({ headless: !HEADED, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const page = await context.newPage()
  page.on('console', (m) => { if (m.type() === 'error') log('page-error:', m.text()) })

  await page.goto(BASE, { waitUntil: 'networkidle' })
  // window.__labuse est branché dans un effet ; on attend qu'il existe.
  await page.waitForFunction(() => !!window.__labuse, null, { timeout: STEP_TIMEOUT }).catch(() => log('⚠ window.__labuse absent — pilotage manuel requis'))

  const drive = (fn, arg) => page.evaluate(fn, arg).catch((e) => log('drive fail:', String(e).slice(0, 120)))
  const setView = (v) => drive((v) => window.__labuse?.setView(v), v)
  const select = (idu) => drive((idu) => { window.__labuse?.setView('cartes'); window.__labuse?.select(idu) }, idu)

  const results = []
  async function capture(name, { prepare, selector, settle = 900 } = {}) {
    log(`→ ${name}`)
    try {
      if (prepare) await prepare()
      await page.waitForTimeout(settle)
      let el = null
      if (selector) {
        el = page.locator(selector).first()
        await el.waitFor({ state: 'visible', timeout: STEP_TIMEOUT })
      }
      const file = path.join(OUT, `${name}.png`)
      if (el) { await el.screenshot({ path: file }) }
      else { await page.screenshot({ path: file, fullPage: true }) }
      results.push({ name, ok: true, mode: el ? 'element' : 'page', file })
      log(`  ✓ ${file}`)
    } catch (e) {
      const file = path.join(OUT, `${name}__fallback.png`)
      await page.screenshot({ path: file, fullPage: true }).catch(() => {})
      results.push({ name, ok: false, err: String(e).slice(0, 160), file })
      log(`  ⚠ échec (${String(e).slice(0, 80)}) — repli pleine page`)
    }
  }
  const click = async (sel) => { const l = page.locator(sel).first(); await l.waitFor({ state: 'visible', timeout: STEP_TIMEOUT }); await l.click() }
  const clickText = async (re) => { const l = page.getByText(re).first(); await l.waitFor({ state: 'visible', timeout: STEP_TIMEOUT }); await l.click() }

  // ─────────────────────────── VOLET A — IDU ───────────────────────────
  await capture('A1_fiche_entete_idu', {
    prepare: () => select(IDU),
    selector: '[data-fiche-idu]',
  })
  // vue rapprochée de l'en-tête complet (IDU + bouton copier + rappel court)
  await capture('A1b_fiche_entete_zone', { selector: 'aside:has([data-fiche-idu])' })
  // état « copié » du bouton
  await capture('A2_bouton_copie', {
    prepare: async () => { await click('[data-fiche-copy-idu]') },
    selector: '[data-fiche-copy-idu]',
    settle: 400,
  })
  // ProjetKanban — s'atteint en OUVRANT un projet depuis la vue Projets.
  // On ouvre un projet AVEC des retenues (les colonnes retenue/écartée ne portent des
  // KanbanCard que là) — 3ᵉ projet de la liste ; repli sur le 1er.
  await capture('A3_kanban_proposee', {
    prepare: async () => {
      await setView('projets')
      await page.getByRole('button', { name: 'Ouvrir' }).nth(2).click()
        .catch(async () => { await clickText(/^Ouvrir$/).catch(() => {}) })
    },
    selector: '[data-proposee-row]',
    settle: 1800,
  })
  await capture('A3b_kanban_carte', { selector: '[data-kanban-card]' })
  // ParcoursTinder (mode « trier ») — ouvrir un projet AVEC parcelles à trier, puis « Trier ».
  await capture('A4_parcours_decision', {
    prepare: async () => {
      await setView('projets')
      await page.getByRole('button', { name: 'Ouvrir' }).nth(2).click().catch(() => {})
      await page.waitForTimeout(1200)
      await page.getByRole('button', { name: 'Trier' }).first().click().catch(() => {})
    },
    selector: '[data-decision-card]',
    settle: 1600,
  })

  // ─────────────────────────── VOLET B — bandeau AvisIA ───────────────────────────
  // Fiche · AskBar
  await capture('B1_askbar', {
    prepare: async () => { await select(IDU); await clickText(/demander/i).catch(() => {}) },
    selector: '[data-avis-ia]',
  })
  // Fiche · explication faisabilité — déplier le tiroir puis cliquer « Expliquer ».
  // (banni dans le bloc de sortie généré → visible seulement si l'endpoint répond)
  await capture('B2_faisa_explain', {
    prepare: async () => { await select(IDU); await clickText(/Faisabilité/i).catch(() => {}); await click('[data-faisa-explain-btn]').catch(() => {}) },
    selector: '[data-faisa-explain] [data-avis-ia]',
    settle: 2500,
  })
  // Fiche · TraducteurBloc — déplier le tiroir Règles puis le bloc traducteur.
  // (bandeau ancré à l'ouverture → visible SANS réponse IA)
  await capture('B3_traducteur', {
    prepare: async () => { await select(IDU); await clickText(/Règles d'urbanisme/i).catch(() => {}); await click('[data-traducteur-toggle]').catch(() => {}) },
    selector: '[data-traducteur] [data-avis-ia]',
    settle: 1400,
  })
  // Recherche IA (IAStub) — bandeau + réponse agrégée
  await capture('B4_ia_search', {
    prepare: async () => {
      await setView('ia')
      const box = page.locator('input, textarea').first()
      await box.waitFor({ state: 'visible', timeout: STEP_TIMEOUT }).catch(() => {})
      await box.fill('combien de parcelles chaudes de plus de 1000 m² à Saint-Paul').catch(() => {})
      await box.press('Enter').catch(() => {})
      await page.waitForTimeout(1800)
      // repli : cliquer un exemple curé si aucun agrégat n'est apparu
      if (!(await page.locator('[data-ia-aggregate]').count())) {
        await page.getByRole('button', { name: /m²|chaudes|combien|Saint-Paul/i }).first().click().catch(() => {})
      }
    },
    selector: '[data-ia-aggregate] [data-avis-ia]',
    settle: 2500,
  })
  // Restitution IA (bandeau App.tsx) — apparaît après une recherche
  await capture('B5_ia_restitution', { selector: '[data-ia-restitution] [data-avis-ia]' })
  // ProjetEntretien (entretien IA)
  await capture('B6_entretien', {
    prepare: async () => { await setView('projets'); await clickText(/décrire un projet|nouveau projet|votre projet/i).catch(() => {}) },
    selector: '[data-entretien] [data-avis-ia]',
    settle: 1200,
  })
  // Copilote
  await capture('B7_copilote', {
    prepare: () => setView('copilote'),
    selector: '[data-copilote] [data-avis-ia]',
  })
  // Export HTML (section « Analyse LABUSE (IA) ») — EXPORT_BASE = API fraîche (mon code),
  // car l'API par défaut peut être antérieure à mes éditions export.py.
  const EXPORT_BASE = process.env.EXPORT_BASE || ORIGIN
  await capture('B8_export_html', {
    prepare: () => page.goto(`${EXPORT_BASE}/parcels/${IDU}/export?format=html`, { waitUntil: 'networkidle' }),
    selector: '.avis-ia',
    settle: 600,
  })

  await browser.close()

  // Récapitulatif pour la revue.
  log('──────── récapitulatif ────────')
  for (const r of results) log(`${r.ok ? '✓' : '⚠'} ${r.name} [${r.mode || 'échec'}] ${r.file}`)
  const ko = results.filter((r) => !r.ok)
  if (ko.length) log(`\n${ko.length} surface(s) non capturée(s) proprement — voir les *__fallback.png et ajuster les sélecteurs/nav.`)
  else log('\nToutes les surfaces capturées.')
}

main().catch((e) => { console.error(e); process.exit(1) })
