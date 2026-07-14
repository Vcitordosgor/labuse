// E2E — MANDAT M9 (fiche enrichie : ICD + règlement PLU + signalement + transformation).
//   Serveur : labuse api (BASE app = .../socle/). Base servie q_v5_m6b.
//   Usage : BASE=http://127.0.0.1:8020/socle/ node qa/e2e_m9_fiche.mjs
import { execFileSync } from 'node:child_process'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const APP = (process.env.BASE || 'http://127.0.0.1:8020/socle/').replace(/\/$/, '') + '/'
const API = new URL(APP).origin
const DB = process.env.QA_DB || 'postgresql://openclaw@localhost:5432/labuse'
const SRC = 'q_v5_m6b'
// parcelle témoin Saint-Paul : ICD partiel (65), potentiel « fort », zone PLU outillée
const IDU = process.env.IDU || '97415000BE0027'

let fails = 0
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? '✓' : '✗'} ${name}${extra ? ` — ${extra}` : ''}`)
  if (!cond) fails += 1
}
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const rq = ctx.request

// ── 1. ICD dans la fiche API (bloc icd) + cloisonnement du score P ──
const fiche = await (await rq.get(`${API}/parcels/${IDU}?source=${SRC}`)).json()
const icd = fiche.icd
ok('1a.icd-present', !!icd && typeof icd.score === 'number' && icd.score >= 0 && icd.score <= 100,
  icd ? `score=${icd.score} bande=${icd.bande}` : 'absent')
ok('1b.icd-manquants', Array.isArray(icd?.manquants), `${icd?.manquants?.length ?? 0} groupe(s) manquant(s)`)
ok('1c.icd-cloisonne', /score d.opportunit/i.test(icd?.cloisonnement || ''), 'mention de cloisonnement')

// invariance : l'ICD ne pilote NI le tier NI le rang (colonne annexe). Contrôle SQL.
const distinctPairs = sql(
  `SELECT count(DISTINCT tier) FROM parcel_p_score_v2 WHERE run_id=(SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1) AND icd BETWEEN 84 AND 86`)
ok('1d.icd-independant-du-tier', parseInt(distinctPairs) >= 2,
  `un même ICD couvre ${distinctPairs} tiers distincts (ICD ≠ tier)`)

// ── 2. ICD dans les exports (CSV liste + PDF fiche) ──
const csv = await (await rq.get(`${API}/parcels/export.csv?source=${SRC}&communes=Saint-Paul&limit=50`)).text()
const header = csv.split('\n')[0]
ok('2a.csv-colonne-icd', /(^|;)icd(;|$)/.test(header) && /confiance_donnees/.test(header), 'colonnes icd + confiance_donnees')
const pdfResp = await rq.get(`${API}/parcels/${IDU}/export.pdf?source=${SRC}`)
ok('2b.pdf-genere', pdfResp.status() === 200 && (pdfResp.headers()['content-type'] || '').includes('pdf'),
  `http=${pdfResp.status()}`)

// ── 3. Lien règlement PLU par zone ──
const rp = fiche.reglement_plu
const z0 = rp?.zones?.[0]
ok('3a.reglement-present', !!z0, z0 ? `${rp.zones.length} zone(s)` : 'absent')
ok('3b.reglement-lien', !!z0?.url && /^https?:\/\//.test(z0.url), z0?.url || '(aucun)')
// une zone calibrée doit porter des références article/page cliquables
const uidu = sql(
  `SELECT p.idu FROM parcels p JOIN spatial_layers sl ON sl.kind='plu_gpu_zone' AND ST_Intersects(sl.geom_2975,p.geom_2975) WHERE p.commune='Saint-Paul' AND sl.attrs->>'libelle' LIKE 'U1%' LIMIT 1`)
if (uidu) {
  const fu = await (await rq.get(`${API}/parcels/${uidu}?source=${SRC}`)).json()
  const zc = (fu.reglement_plu?.zones || []).find((z) => z.calibree)
  ok('3c.reglement-article-page', !!zc && zc.articles.length > 0 && /#page=\d+/.test(zc.articles[0].url || ''),
    zc ? `${zc.zone}: ${zc.articles.length} art., deep-link ${(zc.articles[0].url || '').split('#')[1]}` : 'aucune zone calibrée')
} else ok('3c.reglement-article-page', false, 'aucune parcelle U1 trouvée')

// ── 4. Signalement : POST API → persistance en base ──
const post = await rq.post(`${API}/signalements`, {
  data: { idu: IDU, type_erreur: 'faux_positif', champ: 'piscine', commentaire: 'E2E M9 — contrôle persistance' },
})
const pj = await post.json()
ok('4a.signalement-post-ok', post.status() === 200 && pj.ok === true && typeof pj.id === 'number', `id=${pj.id}`)
const inDb = sql(`SELECT count(*) FROM signalements WHERE id=${pj.id} AND parcelle_id='${IDU}' AND type_erreur='faux_positif' AND statut='nouveau'`)
ok('4b.signalement-en-base', parseInt(inDb) === 1, `${inDb} ligne(s) horodatée(s) en base`)
const csvSig = await rq.get(`${API}/signalements/export.csv`)
ok('4c.signalement-export-csv', csvSig.status() === 200 && (await csvSig.text()).includes(String(pj.id)), 'export CSV des signalements')

// ── 5. Potentiel de transformation (fond de l'ancien outil Mutabilité) ──
const pt = fiche.potentiel_transformation
ok('5a.transformation-present', !!pt && !!pt.niveau, pt ? `niveau=${pt.niveau} SDP consommée=${pt.pct_consomme}%` : 'absent')
ok('5b.transformation-sdp-ratio', pt && pt.pct_consomme != null, 'alimenté par le ratio SDP consommée/autorisée (bloc D)')

// ── 6. UI : blocs affichés dans la fiche + outil Mutabilité RETIRÉ ──
const errs = []
const page = await ctx.newPage()
page.on('pageerror', (e) => errs.push(String(e).slice(0, 160)))
await page.goto(APP + '#v=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
await page.waitForTimeout(2500)
// 6.0 — le toggle carte « Mutabilité » n'existe plus dans la nav
const mutabiliteBtn = await page.locator('button', { hasText: 'Mutabilité' }).count()
ok('6.0.mutabilite-retiree-nav', mutabiliteBtn === 0, `boutons « Mutabilité » = ${mutabiliteBtn}`)

await page.fill('[data-omnibox]', IDU)
await page.keyboard.press('Enter')
await page.waitForSelector('[data-icd]', { timeout: 15000 }).catch(() => {})
ok('6.1.ui-icd-bloc', await page.locator('[data-icd]').count() > 0, 'bloc Confiance données visible')
ok('6.2.ui-plu-lien', await page.locator('[data-plu-link]').count() > 0, 'lien règlement PLU visible')
ok('6.3.ui-transformation', await page.locator('[data-transformation]').count() > 0, 'bloc Potentiel de transformation visible')
// 6.4 — signaler une erreur : bouton → formulaire → soumission → confirmation
const btn = page.locator('[data-signaler-erreur]')
ok('6.4.ui-bouton-signaler', await btn.count() > 0, 'bouton « Signaler une erreur » visible')
if (await btn.count() > 0) {
  await btn.click()
  await page.waitForSelector('[data-signalement-form]', { timeout: 5000 })
  await page.selectOption('[data-signalement-type]', 'zonage').catch(() => {})
  await page.fill('[data-signalement-commentaire]', 'E2E M9 — signalement via UI')
  await page.click('[data-signalement-submit]')
  const okShown = await page.waitForSelector('[data-signalement-ok]', { timeout: 8000 }).then(() => true).catch(() => false)
  ok('6.5.ui-signalement-enregistre', okShown, 'confirmation affichée')
}
ok('6.6.no-console-errors', errs.length === 0, errs.join(' | '))

await browser.close()
console.log(fails ? `\n✗ ${fails} échec(s)` : '\n✓ E2E M9 : tout est vert')
process.exit(fails ? 1 : 0)
