/* ═══════════════════════════════════════════════════════════════════════════
 * M6 §1.15 — SUITE ANTI-INCOHÉRENCES (rejouable)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Scénarios utilisateur de bout en bout qui traquent toute proposition
 * IMPOSSIBLE de la plateforme (habitat en zone économique, piscine en zone N,
 * parcelle PPR rouge servie par un outil, etc.).
 *
 * USAGE
 *   cd frontend
 *   BASE=http://127.0.0.1:8010/socle/ node qa/m6_scenarios.mjs
 *   Variables : BASE (front), QA_DB (postgres, SELECT uniquement),
 *               OUT (captures), M6_STRICT=1 → les FAIL ATTENDUS font aussi
 *               échouer la suite (mode « tout doit être corrigé »).
 *
 * SORTIE
 *   PASS   : le scénario ne détecte aucune incohérence.
 *   XFAIL  : incohérence CONNUE, consignée — ticket M6-INC-xx dans
 *            reports/m6-audit/sections/1-15-scenarios.md. N'échoue pas la
 *            suite (sauf M6_STRICT=1) : c'est la dette documentée.
 *   XPASS  : un XFAIL qui passe → le bug a été corrigé, retirer le ticket.
 *   FAIL   : régression NON attendue → exit code 1.
 *
 * PRINCIPES
 *   - lecture seule : aucune écriture en base, aucun POST créateur d'objet
 *     (les POST utilisés — /modules/programme, /segments/query,
 *     /modules/faisabilite/{idu}/charge — sont des calculs sans persistance) ;
 *   - aucun IDU codé en dur : les parcelles de test sont retrouvées par SQL
 *     à chaque exécution (la suite survit aux recomputes) ;
 *   - la « vérité terrain » (zone PLU dominante, étage 0, canopée) est lue en
 *     SQL et confrontée à ce que les endpoints/l'UI proposent.
 * ═══════════════════════════════════════════════════════════════════════════ */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const API = new URL('..', BASE).href.replace(/\/$/, '')       // http://127.0.0.1:8010
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
const OUT = process.env.OUT || '../reports/m6-audit/sections/captures-1-15'
const STRICT = process.env.M6_STRICT === '1'
mkdirSync(OUT, { recursive: true })

const sql = (q) => execFileSync('psql', [DB, '-tA', '-F', '|', '-c', q], { encoding: 'utf8' }).trim()
const api = async (path, body, essai = 0) => {
  try {
    const r = await fetch(API + path, body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
    if (!r.ok) throw new Error(`${path} → HTTP ${r.status}`)
    return await r.json()
  } catch (e) {                                  // socket keep-alive recyclé → un retry suffit
    if (essai < 2) { await new Promise((s) => setTimeout(s, 1500)); return api(path, body, essai + 1) }
    throw e
  }
}
const vals = (idus) => idus.map((i) => `('${i}')`).join(',')

/** Zone PLU dominante (par surface d'intersection) pour une liste d'IDUs. */
const domZones = (idus) => sql(`
  WITH t(idu) AS (VALUES ${vals(idus)})
  SELECT t.idu, COALESCE(z.subtype,''), COALESCE(z.lib,''), COALESCE(z.name,'')
  FROM t JOIN parcels p ON p.idu = t.idu
  CROSS JOIN LATERAL (
    SELECT sl.subtype, sl.attrs->>'libelle' AS lib, sl.name
    FROM spatial_layers sl
    WHERE sl.kind = 'plu_gpu_zone' AND ST_Intersects(sl.geom_2975, p.geom_2975)
    ORDER BY ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975)) DESC LIMIT 1) z`)
  .split('\n').filter(Boolean).map((l) => {
    const [idu, subtype, lib, name] = l.split('|')
    return { idu, subtype, lib, name }
  })

/** Zone à VOCATION ÉCONOMIQUE (habitat interdit/marginal) — détection prudente :
 *  libellé long explicite (« activités », « industriel »…) ou code sans ambiguïté
 *  (Ue/UE/Uem/US/AUe — jamais Ui/Ua seuls : selon la commune ils sont résidentiels). */
const isEco = (z) => /activit|industri|commercial|artisan|economiq|économiq/i.test(z.name)
  || /^(1|2)?AUe/.test(z.lib) || ['Ue', 'UE', 'Uem', 'US', 'Uz'].includes(z.lib)

/* ── runner ──────────────────────────────────────────────────────────────── */
const results = []
let browser, page
async function scenario(id, titre, { xfail = null } = {}, fn) {
  process.stdout.write(`\n■ ${id} — ${titre}\n`)
  let verdict, detail = ''
  try {
    const problems = await fn()
    if (problems && problems.length) {
      detail = problems.join(' · ')
      verdict = xfail ? 'XFAIL' : 'FAIL'
      console.log(`  ✗ incohérences : ${detail}`)
      if (xfail) console.log(`  → FAIL ATTENDU, ticket ${xfail} (1-15-scenarios.md)`)
    } else {
      verdict = xfail ? 'XPASS' : 'PASS'
      if (xfail) console.log(`  ✓ passe alors qu'un échec était attendu — ${xfail} corrigé ? Retirer le xfail.`)
      else console.log('  ✓ aucune incohérence détectée')
    }
  } catch (e) {
    verdict = 'ERROR'
    detail = String(e.message || e).slice(0, 300)
    console.log(`  ✗ erreur d'exécution : ${detail}`)
  }
  results.push({ id, titre, verdict, xfail, detail })
}

async function newPage(url) {
  page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2000)
  return page
}

browser = await chromium.launch()

/* ═══ S1 — « logement étudiant » → zones à vocation économique/industrielle ═══
 * Un client décrit une résidence étudiante (40 logements, R+2). Le moteur
 * programme→parcelles (M22, servi aussi par Projets/apercu) ne doit JAMAIS
 * proposer une parcelle dont la zone PLU dominante interdit l'habitat. */
await scenario('S1', 'Logement étudiant → parcelles en zone économique/industrielle',
  { xfail: 'M6-INC-01' }, async () => {
    const d = await api('/modules/programme', {
      type: 'etudiant', batiments: 1, niveaux: 2, logements_par_batiment: 40,
      surface_unite_m2: 60, parking: true, commune: null,
    })
    if (!d.items?.length) throw new Error('aucun candidat M22 — préconditions absentes')
    const zones = domZones(d.items.map((i) => i.idu))
    const eco = zones.filter(isEco)
    console.log(`  · ${d.items.length} candidats servis · ${eco.length} en zone dominante à vocation économique`)
    eco.slice(0, 6).forEach((z) => console.log(`    - ${z.idu} : ${z.lib} (${z.name.slice(0, 70)})`))
    // preuve côté CLIENT : le même moteur dans l'UI (Outils → Faisabilité programme)
    if (eco.length) {
      const p = await newPage(BASE + '#v=1&m=programme')
      await p.selectOption('select', 'etudiant')
      await p.locator('label:has-text("UNITÉS/BÂT") input').fill('40')
      await p.click('text=Trouver les parcelles')
      await p.waitForSelector('text=parcelles candidates', { timeout: 30000 })
      const panel = (await p.textContent('body')) || ''
      const first = eco.find((z) => panel.includes(`${z.idu.slice(8, 10)} ${z.idu.slice(10)}`))
      if (first) console.log(`    - VISIBLE côté client dans le panneau M22 : ${first.idu} (${first.lib})`)
      await p.screenshot({ path: `${OUT}/s1-m22-etudiant.png` })
      await p.close()
    }
    return eco.map((z) => `${z.idu}=${z.lib}`)
  })

/* ═══ S2 — « division parcellaire » sur une parcelle en zone A/N ═══
 * (a) le module Division ne doit lister AUCUNE parcelle à dominante A/N ;
 * (b) sur une parcelle 100 % zone A, la calculette de charge foncière doit
 *     répondre honnêtement (« non calculable »), jamais un chiffre. */
await scenario('S2', 'Division / faisabilité sur parcelle zone A ou N → réponses honnêtes', {}, async () => {
  const problems = []
  const d = await api('/modules/division?limit=300')
  const zones = domZones(d.items.map((i) => i.idu))
  const an = zones.filter((z) => z.subtype === 'A' || z.subtype === 'N')
  console.log(`  · division : ${d.items.length} candidats · ${an.length} à dominante A/N`)
  an.slice(0, 5).forEach((z) => problems.push(`division propose ${z.idu} en zone ${z.lib}`))
  // parcelle entièrement en zone A, retrouvée dynamiquement
  const [iduA] = sql(`SELECT p.idu FROM spatial_layers sl
    JOIN parcels p ON p.geom_2975 && sl.geom_2975 AND ST_Within(p.geom_2975, sl.geom_2975)
    WHERE sl.kind='plu_gpu_zone' AND sl.subtype='A' AND p.surface_m2 BETWEEN 1000 AND 5000
    LIMIT 1`).split('|')
  const charge = await api(`/modules/faisabilite/${iduA}/charge`, {})
  console.log(`  · calculette sur ${iduA} (100 % zone A) : calculable=${charge.calculable} (${charge.raison || '—'})`)
  if (charge.calculable !== false) problems.push(`calculette chiffre une charge foncière en zone A (${iduA})`)
  return problems
})

/* ═══ S3 — « collectif » R+4 en zone à hauteur limitée ═══
 * Le moteur programme→parcelles ne doit jamais proposer une parcelle dont la
 * hauteur PLU VÉRIFIÉE est inférieure à la hauteur requise par le gabarit. */
await scenario('S3', 'Collectif R+4 → aucune parcelle à hauteur PLU vérifiée insuffisante', {}, async () => {
  const d = await api('/modules/programme', {
    type: 'logements', batiments: 1, niveaux: 4, logements_par_batiment: 24,
    surface_unite_m2: 60, parking: true, commune: null,
  })
  const hmin = d.criteres.hauteur_min_m
  const bad = (d.items || []).filter((i) => i.hauteur_verifiee && i.hauteur_plu_m < hmin)
  const inconnu = (d.items || []).filter((i) => !i.hauteur_verifiee).length
  console.log(`  · ${d.n} candidats R+4 (h min ${hmin} m) · violations hauteur vérifiée : ${bad.length}`
    + ` · « à instruire » (hauteur inconnue) : ${inconnu}/${(d.items || []).length}`)
  return bad.map((i) => `${i.idu} h=${i.hauteur_plu_m}<${hmin}`)
})

/* ═══ S4 — « piscine » en zone N / secteur protégé ═══
 * La vue Piscinistes — construction vend des prospects « projet piscine » :
 * une parcelle à dominante A/N, dans le cœur du Parc national ou sans le
 * moindre bâti n'est pas un prospect piscine plausible. */
await scenario('S4', 'Vue Piscinistes → parcelles en zone A/N, cœur de Parc, sans bâti',
  { xfail: 'M6-INC-02' }, async () => {
    const d = await api('/segments/query', { slug: 'piscinistes-construction', limit: 200 })
    const items = d.items || []
    const idus = items.map((i) => i.idu)
    const zones = domZones(idus)
    const an = zones.filter((z) => z.subtype === 'A' || z.subtype === 'N')
    const coeur = sql(`WITH t(idu) AS (VALUES ${vals(idus)})
      SELECT count(DISTINCT t.idu) FROM t JOIN parcels p ON p.idu=t.idu
      JOIN spatial_layers sl ON sl.kind='parc_national' AND sl.subtype='coeur'
        AND ST_Intersects(p.geom_2975, sl.geom_2975)`)
    const nu = items.filter((i) => Number(i.jardin_m2) === Number(i.surface_m2))
    console.log(`  · top ${items.length} (tri défaut jardin) : ${an.length} en zone A/N dominante · `
      + `${coeur} dans le cœur du Parc national · ${nu.length} sans aucun bâti`)
    const problems = []
    if (an.length) problems.push(`${an.length}/${items.length} en zone A/N (ex. ${an[0].idu}=${an[0].lib})`)
    if (Number(coeur) > 0) problems.push(`${coeur} parcelle(s) au cœur du Parc national`)
    if (nu.length) problems.push(`${nu.length} parcelles sans bâti (prospect « piscine » sans maison)`)
    return problems
  })

/* ═══ S5 — parcelle écartée à l'étage 0 (PPR rouge…) proposée par un outil ═══
 * L'étage 0 est le verdict d'exclusion DURE de la plateforme. Le module
 * Division sert sa liste sans jamais le consulter : une parcelle « PPR zone
 * rouge (inconstructible) » peut sortir à score 99 sans le moindre badge. */
await scenario('S5', 'Outil Division → parcelles exclues à l\'étage 0 (PPR rouge) sans avertissement',
  { xfail: 'M6-INC-03' }, async () => {
    const d = await api('/modules/division?limit=300')
    const idus = d.items.map((i) => i.idu)
    const rows = sql(`WITH t(idu) AS (VALUES ${vals(idus)})
      SELECT t.idu, d.status, (SELECT string_agg(DISTINCT cr.layer_name, ',')
          FROM dryrun_cascade_results cr
          WHERE cr.parcel_id = p.id AND cr.run_label = d.run_label AND cr.result = 'HARD_EXCLUDE')
      FROM t JOIN parcels p ON p.idu = t.idu
      JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = 'q_v3_datagap'
      WHERE d.status IN ('exclue','faux_positif_probable')`)
      .split('\n').filter(Boolean).map((l) => l.split('|'))
    console.log(`  · ${rows.length}/${idus.length} candidats servis sont exclus à l'étage 0`)
    rows.slice(0, 5).forEach(([idu, st, motifs]) => console.log(`    - ${idu} : ${st} (${motifs})`))
    // preuve côté CLIENT : l'UI du module n'affiche aucun badge d'exclusion
    if (rows.length) {
      const p = await newPage(BASE + '#v=1&m=division')
      await p.waitForSelector('text=candidats (SQL)', { timeout: 30000 })
      const body = (await p.textContent('body')) || ''
      const visible = rows.find(([idu]) => body.includes(`${idu.slice(8, 10)} ${idu.slice(10)}`))
      if (visible)
        console.log(`    - VISIBLE côté client dans le panneau Division : ${visible[0]} (${visible[2]})`
          + ' — la ligne ne porte aucun badge d\'exclusion (l\'API du module ne renvoie pas l\'étage 0)')
      await p.screenshot({ path: `${OUT}/s5-division-etage0.png` })
      await p.close()
    }
    const probs = rows.map(([idu, st]) => `${idu}=${st}`)
    return probs.length > 10 ? [...probs.slice(0, 10), `… +${probs.length - 10} autres`] : probs
  })

/* ═══ S6 — véranda/pergola sur parcelle SANS bâti (scénario libre) ═══
 * La vue Pergolas & terrasses promet « les maisons avec du jardin nu à
 * équiper » : une parcelle sans aucune emprise bâtie n'a pas de maison. */
await scenario('S6', 'Vue Pergolas → parcelles sans bâti / en zone A-N', { xfail: 'M6-INC-04' }, async () => {
  const d = await api('/segments/query', { slug: 'pergolas-terrasses', limit: 200 })
  const items = d.items || []
  const nu = items.filter((i) => Number(i.jardin_m2) === Number(i.surface_m2))
  const zones = domZones(items.map((i) => i.idu))
  const an = zones.filter((z) => z.subtype === 'A' || z.subtype === 'N')
  console.log(`  · top ${items.length} (tri défaut) : ${nu.length} sans aucun bâti · ${an.length} en zone A/N dominante`)
  const problems = []
  if (nu.length) problems.push(`${nu.length}/${items.length} parcelles sans bâti (ex. ${nu[0].idu})`)
  if (an.length) problems.push(`${an.length} en zone A/N (ex. ${an[0].idu}=${an[0].lib})`)
  return problems
})

/* ═══ S7 — PV résidentiel sur parcelle boisée dense (scénario libre) ═══
 * Le preset pv-residentiel exclut par défaut l'ombrage végétal (filtre
 * optionnel pré-coché). Vérité LiDAR : aucune parcelle servie ne doit avoir
 * une canopée dominante (≥ 60 %). */
await scenario('S7', 'Vue PV résidentiel → aucune parcelle boisée dense (canopée ≥ 60 %)', {}, async () => {
  const d = await api('/segments/query', { slug: 'pv-residentiel', limit: 300 })
  const idus = (d.items || []).map((i) => i.idu)
  if (!idus.length) throw new Error('preset pv-residentiel vide')
  const n = sql(`WITH t(idu) AS (VALUES ${vals(idus)})
    SELECT count(*) FROM t JOIN parcel_vegetation v ON v.idu = t.idu WHERE v.canopee_pct >= 60`)
  console.log(`  · ${idus.length} parcelles servies · canopée ≥ 60 % : ${n}`)
  return Number(n) > 0 ? [`${n} parcelles boisées denses servies`] : []
})

/* ═══ S8 — honnêteté de l'étage 0 dans le parcours principal ═══
 * (a) la liste par défaut n'inclut pas les écartées (chips SQL-exactes) ;
 * (b) la fiche d'une parcelle exclue AFFICHE le bandeau « écartée ». */
await scenario('S8', 'Parcours principal → écartées hors liste par défaut, fiche honnête', {}, async () => {
  const problems = []
  const V2RUN = sql('SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1')
  const [nonEcartees, ecartees] = sql(`
    WITH eff AS (SELECT CASE WHEN d.status IN ('exclue','faux_positif_probable') THEN 'ecartee'
                 ELSE COALESCE(s.tier,'ecartee') END AS t
      FROM parcel_p_score_v2 s JOIN parcels p ON p.idu = s.parcelle_id
      LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = 'q_v3_datagap'
      WHERE s.run_id = '${V2RUN}')
    SELECT count(*) FILTER (WHERE t <> 'ecartee'), count(*) FILTER (WHERE t = 'ecartee') FROM eff`).split('|').map(Number)
  const p = await newPage(BASE + '#f=1&v=1')
  // la chip « Tout » du panneau (≠ « Toute l'île » du header) : « Tout79 043 »
  const chipTout = (await p.locator('button', { hasText: /^Tout[\d\s  ]+$/ }).first().textContent()) || ''
  const numTout = Number(chipTout.replace(/[^\d]/g, ''))
  console.log(`  · chip « Tout » = ${numTout} · SQL non-écartées = ${nonEcartees} (écartées : ${ecartees})`)
  if (numTout !== nonEcartees) problems.push(`chip Tout=${numTout} ≠ SQL non-écartées=${nonEcartees} (écartées incluses ?)`)
  // fiche d'une parcelle exclue étage 0 (retrouvée dynamiquement)
  const [iduX] = sql(`SELECT p.idu FROM parcels p JOIN dryrun_parcel_evaluations d
    ON d.parcel_id = p.id AND d.run_label = 'q_v3_datagap'
    WHERE d.status = 'exclue' LIMIT 1`).split('|')
  await p.evaluate((idu) => window.__labuse.select(idu), iduX)
  await p.waitForSelector('[data-badge-verdict]', { timeout: 20000 })
  await p.waitForTimeout(1200)
  const bandeau = await p.locator('[data-bandeau-ecartee]').count()
  const verdict = (await p.locator('[data-badge-verdict]').first().textContent()) || ''
  console.log(`  · fiche ${iduX} (exclue) : bandeau écartée=${bandeau > 0} · badge="${verdict.trim().slice(0, 40)}"`)
  if (!bandeau && !/Écartée/i.test(verdict)) problems.push(`fiche ${iduX} sans bandeau ni badge « écartée »`)
  await p.screenshot({ path: `${OUT}/s8-fiche-ecartee.png` })
  await p.close()
  return problems
})

/* ═══ S9 — « hauteur PLU (vérifiée) » sans PLU calibré (scénario libre) ═══
 * M22 étiquette « vérifiée » toute hauteur non nulle, même issue de
 * l'ESTIMATION GÉNÉRIQUE (commune sans config/plu_<slug>.yaml). Un client
 * lit « Hauteur PLU 9 m (vérifiée) » au Port alors que rien n'est calibré. */
await scenario('S9', 'M22 → « hauteur vérifiée » affichée pour une commune non calibrée',
  { xfail: 'M6-INC-05' }, async () => {
    if (existsSync('../config/plu_le_port.yaml'))
      return [] // la commune a été calibrée depuis : le scénario n'a plus d'objet
    const d = await api('/modules/programme', {
      type: 'etudiant', batiments: 1, niveaux: 2, logements_par_batiment: 40,
      surface_unite_m2: 60, parking: true, commune: 'Le Port',
    })
    const verifiees = (d.items || []).filter((i) => i.hauteur_verifiee)
    console.log(`  · Le Port (PLU non calibré) : ${verifiees.length}/${(d.items || []).length} candidats « hauteur vérifiée »`)
    return verifiees.slice(0, 3).map((i) => `${i.idu} affiché « h ${i.hauteur_plu_m} m ✓ » sans calibrage`)
  })

/* ═══ S10 — libellé du verdict capacité en zone A (scénario libre) ═══
 * En zone A, le verdict de pré-faisabilité recycle le texte des secteurs de
 * transition « AU*st » — un client lit un motif faux (quoique la conclusion
 * « non constructible » soit juste). */
await scenario('S10', 'Faisabilité zone A → motif du verdict erroné (texte AU*st)',
  { xfail: 'M6-INC-06' }, async () => {
    const [iduA] = sql(`SELECT p.idu FROM spatial_layers sl
      JOIN parcels p ON p.geom_2975 && sl.geom_2975 AND ST_Within(p.geom_2975, sl.geom_2975)
      WHERE sl.kind='plu_gpu_zone' AND sl.subtype='A' AND p.surface_m2 BETWEEN 1000 AND 5000
      LIMIT 1`).split('|')
    const d = await api(`/modules/faisabilite/${iduA}`)
    const verdict = d.capacite?.verdict || ''
    console.log(`  · ${iduA} (zone A) : verdict = « ${verdict.slice(0, 90)} »`)
    return /AU\*?st|transition/i.test(verdict)
      ? [`zone A servie avec un motif « secteur de transition (AU*st) » (${iduA})`] : []
  })

/* ── bilan ───────────────────────────────────────────────────────────────── */
await browser.close()
console.log('\n═════════════ BILAN SUITE M6 §1.15 ═════════════')
const counts = { PASS: 0, FAIL: 0, XFAIL: 0, XPASS: 0, ERROR: 0 }
for (const r of results) {
  counts[r.verdict]++
  const tag = { PASS: '✓ PASS ', FAIL: '✗ FAIL ', XFAIL: '✗ XFAIL', XPASS: '! XPASS', ERROR: '! ERROR' }[r.verdict]
  console.log(`${tag}  ${r.id} ${r.titre}${r.xfail ? ` [${r.xfail}]` : ''}`)
}
console.log(`\n${results.length} scénarios : ${counts.PASS} PASS · ${counts.XFAIL} XFAIL (tickets ouverts) · `
  + `${counts.XPASS} XPASS · ${counts.FAIL} FAIL · ${counts.ERROR} ERROR`)
const hardFail = counts.FAIL + counts.ERROR + (STRICT ? counts.XFAIL : 0)
if (hardFail) { console.log('\n→ ÉCHEC (régression non consignée ou mode strict)'); process.exit(1) }
console.log('\n→ OK (les seuls échecs sont les tickets consignés M6-INC-01..06)')
