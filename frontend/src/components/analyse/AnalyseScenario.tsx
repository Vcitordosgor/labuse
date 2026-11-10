// ECRANS-NOV-2 — l'écran « Analyse LABUSE par scénario », DANS le panneau de gauche (à côté de la
// carte). LIT GET /analyse/scenarios (ALGO-FIX-1) : il n'invente aucun chiffre. DEUX étapes :
// « Choisir » (objectif/scénario + cases à cocher bandes/statuts avec effectifs) → « La liste » (plein
// panneau ; « Modifier la recherche » rouvre Choisir). Recette 2 (maquette 7c) : cartes de résultat
// avec le chiffre principal EN GROS + « capacité − existant » en petit, une raison + une flèche ; TOUTE
// la carte ouvre la fiche parcelle (bordure verte au survol). Plus de détail à déplier. Le Signal est
// renommé « Vente » partout. La carte peint EXACTEMENT la liste choisie (scenarioPaint).
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { getAnalyseScenarios, type ScnParcelle, type ScnReponse } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { BANDE_META, type Bande } from '../../lib/status'
import {
  BANDES_CHIP, STATUTS_CHIP, NIVEAUX_CHIP, NIVEAU_META, STATUT_SCN_META,
  bandeLabel, couleurParcelle, venteLabel, equipementLabel,
  FONCIER_PUBLIC_COLOR, FONCIER_PUBLIC_LABEL,
  type NiveauChip, type Objectif, type ScnScenario,
} from '../../lib/scenario'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'

const PAGE = 40
const PAINT_CAP = 20_000
const NET_NEG = '#C4653C'   // orange (terracotta) : une perte (gain net négatif).

// ── la barre de répartition : un segment par cohorte, largeur proportionnelle au compte. ──────────
function BarreRepartition({ segments }: { segments: { color: string; n: number; label: string }[] }) {
  const total = segments.reduce((s, x) => s + x.n, 0) || 1
  return (
    <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-2" role="img"
      aria-label={`Répartition : ${segments.filter((s) => s.n).map((s) => `${s.label} ${s.n}`).join(', ')}`}>
      {segments.filter((s) => s.n > 0).map((s, i) => (
        <span key={i} style={{ width: `${(s.n / total) * 100}%`, background: s.color }} title={`${s.label} · ${fmtInt(s.n)}`} />
      ))}
    </div>
  )
}

// ── une bascule segmentée (Objectif, Scénario) : deux options, l'active en vert opaque. ───────────
function Segment<T extends string>({ value, options, onChange }:
  { value: T; options: { v: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="flex gap-1.5">
      {options.map((o) => (
        <button key={o.v} onClick={() => onChange(o.v)}
          className={`flex-1 rounded-md border px-3 py-1.5 text-[12.5px] transition-colors duration-quick ${
            value === o.v ? 'border-transparent bg-mint font-medium text-mint-on' : 'border-line-2 text-txt hover:border-txt-dim'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

// ── une petite étiquette (puce de carte) : bande, ou « Vente : … ». ───────────────────────────────
function Pastille({ label, color, principal }: { label: string; color: string; principal?: boolean }) {
  return (
    <span className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
      style={principal ? { background: color, color: '#071009' } : { border: `1px solid ${color}66`, color }}>
      {label}
    </span>
  )
}

// ── une LIGNE À COCHER : pastille de couleur + libellé + effectif + coche (✓). ────────────────────
function CheckRow({ label, n, color, on, onToggle }:
  { label: string; n: number | undefined; color: string; on: boolean; onToggle: () => void }) {
  return (
    <button data-check={on ? 'on' : 'off'} role="checkbox" aria-checked={on} onClick={onToggle}
      className="flex w-full items-center gap-2.5 rounded-md px-1.5 py-1.5 text-left text-[12.5px] transition-colors duration-quick hover:bg-surface-2">
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: on ? color : 'transparent', border: `1.5px solid ${color}` }} />
      <span className={`min-w-0 flex-1 truncate ${on ? 'text-txt-hi' : 'text-txt-mut'}`}>{label}</span>
      {n != null && <span className={`tnum ${on ? 'text-txt' : 'text-txt-dim'}`}>{fmtInt(n)}</span>}
      <span className="w-3 shrink-0 text-center text-[12px] font-bold text-mint">{on ? '✓' : ''}</span>
    </button>
  )
}

function fmtSigned(n: number): string {
  return `${n >= 0 ? '+ ' : '− '}${fmtInt(Math.abs(n))}`
}

// La raison COURTE d'une carte (dérivée des quantités servies — aucun calcul inventé).
function raisonCarte(p: ScnParcelle, objectif: Objectif, scenario: ScnScenario, aCheval: boolean): string | null {
  if (objectif === 'sale') return null
  const q = p.quantites
  if (scenario === 'rebuild') {
    const net = q.net_signed
    if (net != null && net < 0) {
      return (q.existing != null && q.project_total != null && q.existing > q.project_total * 1.3)
        ? "l'existant dépasse les règles" : 'bâtie au maximum'
    }
    if (q.existing && q.existing > 0) return `démolition ${fmtInt(q.existing)} m² à prévoir`
    if (q.existing === 0) return 'terrain nu — aucune démolition'
    return null
  }
  if (aCheval && p.zone_productive?.zone) return `sur la portion ${p.zone_productive.zone} (${fmtInt(p.zone_productive.area_m2)} m²)`
  return null
}

// ── une carte de résultat : le chiffre principal en gros + « capacité − existant » en petit, une
// raison + une flèche ; TOUTE la carte ouvre la fiche parcelle (bordure verte au survol). ──────────
function CarteResultat({ p, objectif, scenario }:
  { p: ScnParcelle; objectif: Objectif; scenario: ScnScenario }) {
  const focusParcelle = useApp((s) => s.focusParcelle)
  const q = p.quantites
  const bande = bandeLabel(p.bande)
  const bandeColor = (p.bande && BANDE_META[p.bande as Bande]?.color) || '#5C7268'
  const vente = venteLabel(p.signal?.niveau)
  const venteColor = p.signal?.niveau ? NIVEAU_META[p.signal.niveau].color : '#5C7268'
  const estime = p.statut === 'ESTIMATED'
  const surf = p.surface_m2 ?? 0
  const zoneA = p.zone_productive?.area_m2 ?? null
  const aCheval = !!p.zone_productive?.zone && zoneA != null && surf > 0 && zoneA < surf * 0.98
  const typeBati = q.existing != null ? (q.existing > 0 ? 'bâti' : 'terrain nu') : null
  const faits = [surf ? `${fmtInt(surf)} m²` : null, typeBati,
    p.zone_productive?.zone ? `zone ${p.zone_productive.zone}` : null].filter(Boolean).join(' · ')
  const capExist = (q.project_total != null && q.existing != null)
    ? `${fmtInt(q.project_total)} − ${fmtInt(q.existing)} m²` : null

  // Le chiffre principal EN GROS (vert si gain, orange si perte ; « net » en reconstruction).
  let gros = ''
  let grosColor: string | undefined
  if (objectif === 'sale') {
    gros = p.signal?.p != null ? `Vente ${NIVEAU_META[p.signal.niveau as NiveauChip]?.label ?? ''} — ${p.signal.p.toFixed(2).replace('.', ',')}` : 'Vente non évaluée'
  } else if (!estime) {
    gros = STATUT_SCN_META[p.statut]?.label ?? bande ?? '—'
  } else if (scenario === 'rebuild') {
    // estimé en reconstruction → gain net signé servi ; absent (jamais, en principe) → bande.
    gros = q.net_signed != null ? `${fmtSigned(q.net_signed)} m² net` : (bande ?? '—')
    grosColor = q.net_signed != null && q.net_signed < 0 ? NET_NEG : '#4ADE80'
  } else {
    gros = q.additional != null ? `+ ${fmtInt(q.additional)} m² de plancher` : (bande ?? '—')
    grosColor = '#4ADE80'
  }
  const raison = raisonCarte(p, objectif, scenario, aCheval)

  return (
    <button data-carte-resultat={p.idu} onClick={() => focusParcelle(p.idu, { fiche: true })}
      className="shrink-0 rounded-[10px] border border-line-2 bg-surface-3 px-4 py-3 text-left transition-colors duration-quick hover:border-mint">
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span className="shrink-0 font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{p.idu}</span>
        {objectif === 'sale' ? (
          <>
            {vente && <Pastille label={vente} color={venteColor} principal />}
            {bande && <Pastille label={bande} color={bandeColor} />}
          </>
        ) : (
          <>
            {estime && bande ? <Pastille label={bande} color={bandeColor} principal />
              : <Pastille label={STATUT_SCN_META[p.statut]?.label ?? '—'} color={couleurParcelle(p.statut, p.bande)} principal />}
            {vente && <Pastille label={vente} color={venteColor} />}
          </>
        )}
        {/* FONCIER-PUBLIC-1 — « Équipement public : <type> » (occupé → Hors projet) ou « Foncier
            public » (terrain public, bande gardée). L'équipement prime (il explique le Hors projet). */}
        {p.equipement_public
          ? <Pastille label={equipementLabel(p.equipement_public)!} color={FONCIER_PUBLIC_COLOR} />
          : p.foncier_public && <Pastille label={FONCIER_PUBLIC_LABEL} color={FONCIER_PUBLIC_COLOR} />}
      </div>
      <div className={`mt-1 truncate text-[11px] ${p.adresse ? 'text-txt-dim' : 'text-txt-ghost'}`}>
        {p.adresse ?? 'Adresse non disponible'}
      </div>
      {faits && <div className="mt-0.5 truncate text-[11px] text-txt-mut tnum">{faits}</div>}
      {/* le chiffre principal EN GROS (gauche) + « capacité − existant » en petit (droite) */}
      <div className="mt-1.5 flex items-baseline justify-between gap-2">
        <span className="text-[14px] font-semibold tnum" style={{ color: grosColor }}>{gros}</span>
        {capExist && <span className="shrink-0 text-[11px] text-txt-dim tnum">{capExist}</span>}
      </div>
      {/* une ligne de raison (gauche) + une flèche (droite) — toute la carte ouvre la fiche */}
      <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-txt-mut">
        <span className="min-w-0 truncate">{raison ? `▾ ${raison}` : ''}</span>
        <span aria-hidden className="shrink-0 text-txt-dim">→</span>
      </div>
    </button>
  )
}

// ── le panneau « Comprendre l'analyse ». ──────────────────────────────────────────────────────────
function ComprendreModale({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc)
  }, [onClose])
  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6" onClick={onClose}>
      <div className="max-w-[480px] rounded-xl border border-line-2 bg-bg-1 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-txt-hi">Comprendre l'analyse</h2>
          <button onClick={onClose} className="text-txt-dim hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        <div className="mt-3 space-y-2.5 text-[12px] leading-relaxed text-txt-mut">
          <p><span className="text-txt">Potentiel foncier</span> classe par <span className="text-txt">bande</span> : en <span className="text-txt">bâti conservé</span>, la surface de plancher supplémentaire ; en <span className="text-txt">reconstruction</span>, la capacité du nouveau projet, avec un gain net signé (négatif s'il perd). Chaque carte montre le chiffre en gros et, en petit, « capacité − existant ».</p>
          <p><span className="text-txt">Prospection</span> classe par <span className="text-txt">Vente</span> (Signal de mutation à 12 mois) : qui est susceptible de bouger.</p>
          <p>Vous cochez les bandes et statuts à voir ; les effectifs portent sur toute la sélection, ils font le total. Une bande est servie telle quelle par le moteur ; « À vérifier », « À différer », « Aucun ajout », « Hors projet » isolent ce que le moteur refuse de donner pour sûr.</p>
          <p>Aucun chiffre n'est inventé : tout vient du run servi. Toute la carte ouvre la fiche parcelle.</p>
        </div>
      </div>
    </div>
  )
}

// Cases cochées par défaut : Excellente + Bonne en potentiel (maquette) ; Vente forte + moyenne en vente.
type Coches = { bands: string[]; statuts: string[]; niveaux: NiveauChip[] }
const COCHES_DEFAUT = (o: Objectif): Coches =>
  o === 'sale' ? { bands: [], statuts: [], niveaux: ['fort', 'moyen'] }
    : { bands: ['A', 'B'], statuts: [], niveaux: [] }

export function AnalyseScenario() {
  const filters = useApp((s) => s.filters)
  const retourFiltres = useApp((s) => s.retourFiltres)
  const setScenarioPaint = useApp((s) => s.setScenarioPaint)
  const [etape, setEtape] = useState<'choisir' | 'liste'>('choisir')
  const [objectif, setObjectif] = useState<Objectif>('potential')
  const [scenario, setScenario] = useState<ScnScenario>('keep')
  const [coches, setCoches] = useState<Coches>(COCHES_DEFAUT('potential'))
  const [autresOpen, setAutresOpen] = useState(false)
  // FONCIER-PUBLIC-1 — « Inclure le foncier public » : DÉCOCHÉE par défaut (décision Vic). Décochée,
  // le terrain public sans équipement sort de la sélection (effectifs, liste, carte).
  const [inclureFoncier, setInclureFoncier] = useState(false)
  const [limit, setLimit] = useState(PAGE)
  const [comprendre, setComprendre] = useState(false)

  useEffect(() => { setCoches(COCHES_DEFAUT(objectif)); setAutresOpen(false) }, [objectif])
  useEffect(() => { setLimit(PAGE) }, [filters, objectif, scenario, coches, inclureFoncier, etape])
  // La carte ne peint la liste choisie que tant que l'écran est monté : on l'efface en quittant.
  useEffect(() => () => setScenarioPaint(null), [setScenarioPaint])

  // ── EFFECTIFS (étape « Choisir » + le N de l'étape « Liste ») : requête limit=0, CACHÉE côté serveur.
  // `placeholderData=prev` → changer d'objectif/scénario GARDE l'affichage précédent le temps de la MAJ.
  const effQ = useQuery({
    queryKey: ['scn-eff', filters, objectif, scenario, inclureFoncier],
    queryFn: () => getAnalyseScenarios(filters, { mode: objectif, scenario, limit: 0, inclureFoncierPublic: inclureFoncier }),
    placeholderData: (prev) => prev,
  })
  const data: ScnReponse | undefined = effQ.data
  const eff = data?.effectifs
  const nSelection = data?.n_selection ?? 0
  const nFoncierPublic = data?.n_foncier_public ?? 0

  // ── LISTE + IDU pour la carte : cohortes cochées. carte=1 → la carte peint EXACTEMENT la liste. ──
  const cochesCsv = { bands: coches.bands, statuts: coches.statuts, niveaux: coches.niveaux }
  const listeQ = useQuery({
    queryKey: ['scn-liste', filters, objectif, scenario, coches, inclureFoncier, etape === 'liste' ? limit : 0],
    queryFn: () => getAnalyseScenarios(filters, {
      mode: objectif, scenario, carte: true, inclureFoncierPublic: inclureFoncier,
      limit: etape === 'liste' ? limit : 0, ...cochesCsv,
    }),
    placeholderData: (prev) => prev,
  })
  const nFiltre = listeQ.data?.n_filtre ?? 0
  const tropLarge = nFiltre > PAINT_CAP || !!listeQ.data?.idus_tronque

  // La carte peint exactement la liste choisie (idus des cohortes) ; null si trop large pour peindre.
  useEffect(() => {
    if (!listeQ.data) return
    setScenarioPaint({ idus: listeQ.data.idus ?? null, tronque: !!listeQ.data.idus_tronque,
      foncierPublic: listeQ.data.idus_foncier_public ?? null })
  }, [listeQ.data, setScenarioPaint])

  // lignes à cocher (bandes), lignes « Autres » (statuts), segments de la barre, selon l'objectif.
  const toggle = (famille: 'bands' | 'statuts' | 'niveaux', key: string) => () =>
    setCoches((c) => {
      const arr = c[famille] as string[]
      const next = arr.includes(key) ? arr.filter((x) => x !== key) : [...arr, key]
      return { ...c, [famille]: next }
    })
  const { bandeLignes, autresLignes, nAutres, niveauLignes, segments } = useMemo(() => {
    const vide = { bandeLignes: [], autresLignes: [], nAutres: 0, niveauLignes: [], segments: [] as { color: string; n: number; label: string }[] }
    if (!eff) return vide
    if (objectif === 'sale') {
      const ps = eff.par_signal ?? {}
      const segs = NIVEAUX_CHIP.map((k) => ({ color: NIVEAU_META[k].color, n: ps[k] ?? 0, label: NIVEAU_META[k].label }))
      // en prospection, les lignes à cocher sont les niveaux de Vente (0 masqués).
      const lignes = NIVEAUX_CHIP.filter((k) => (ps[k] ?? 0) > 0).map((k) => ({
        key: k, label: venteLabel(k)!, n: ps[k] ?? 0, color: NIVEAU_META[k].color,
        on: coches.niveaux.includes(k), toggle: toggle('niveaux', k) }))
      return { ...vide, niveauLignes: lignes, segments: segs }
    }
    const pb = eff.par_bande, pst = eff.par_statut
    const segs = [
      ...BANDES_CHIP.map((b) => ({ color: BANDE_META[b].color, n: pb[b] ?? 0, label: BANDE_META[b].label })),
      ...STATUTS_CHIP.map((s) => ({ color: STATUT_SCN_META[s].color, n: pst[s] ?? 0, label: STATUT_SCN_META[s].label })),
    ]
    // les 4 bandes en lignes (0 masqués) ; les statuts regroupés sous « Autres parcelles ».
    const bl = BANDES_CHIP.filter((b) => (pb[b] ?? 0) > 0).map((b) => ({
      key: b, label: BANDE_META[b].label, n: pb[b] ?? 0, color: BANDE_META[b].color,
      on: coches.bands.includes(b), toggle: toggle('bands', b) }))
    const al = STATUTS_CHIP.filter((s) => (pst[s] ?? 0) > 0).map((s) => ({
      key: s, label: STATUT_SCN_META[s].label, n: pst[s] ?? 0, color: STATUT_SCN_META[s].color,
      on: coches.statuts.includes(s), toggle: toggle('statuts', s) }))
    const nA = al.reduce((s, l) => s + l.n, 0)
    return { bandeLignes: bl, autresLignes: al, nAutres: nA, niveauLignes: [], segments: segs }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eff, objectif, coches])

  // N = somme des effectifs cochés (immédiat, dérivé des effectifs).
  const nCoche = useMemo(() => {
    if (!eff) return 0
    if (objectif === 'sale') return coches.niveaux.reduce((s, k) => s + (eff.par_signal?.[k] ?? 0), 0)
    return coches.bands.reduce((s, b) => s + (eff.par_bande[b] ?? 0), 0)
      + coches.statuts.reduce((s, k) => s + (eff.par_statut[k] ?? 0), 0)
  }, [eff, objectif, coches])

  const resumeLigne = `${fmtInt(nCoche)} parcelles · ${objectif === 'sale' ? 'Prospection'
    : `Potentiel · ${scenario === 'rebuild' ? 'Reconstruction' : 'Bâti conservé'}`}`
  const parcelles = listeQ.data?.parcelles ?? []

  // ── EN-TÊTE sur UNE ligne : « Analyse LABUSE » + « i » (Comprendre) + « ← Retour ». ──
  const entete = (
    <header className="flex shrink-0 items-center gap-2 px-5 pt-3 pb-2">
      <div className="flex min-w-0 flex-1 items-center gap-1.5">
        <span className="text-[12.5px] font-semibold tracking-wide text-txt-hi">Analyse LABUSE</span>
        <button data-comprendre onClick={() => setComprendre(true)} aria-label="Comprendre l'analyse"
          className="flex h-[14px] w-[14px] items-center justify-center rounded-full border border-mint/50 text-[9px] font-bold leading-none text-mint hover:bg-mint/10">i</button>
      </div>
      <button data-retour onClick={retourFiltres}
        className="shrink-0 rounded-ctl border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-mut hover:border-txt-dim hover:text-txt">← Retour</button>
    </header>
  )

  return (
    <div data-ecran="analyse-scenario" data-etape={etape} className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      {entete}

      {etape === 'choisir' ? (
        /* ════════ ÉTAPE « CHOISIR » ════════ */
        <div data-etape-choisir className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-4">
          <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-txt-dim">Objectif</div>
          <Segment value={objectif} onChange={setObjectif}
            options={[{ v: 'sale', label: 'Prospection' }, { v: 'potential', label: 'Potentiel' }]} />
          {objectif === 'potential' && (
            <>
              <div className="mb-1.5 mt-3 text-[10px] font-medium uppercase tracking-wide text-txt-dim">Projet · logement</div>
              <Segment value={scenario} onChange={setScenario}
                options={[{ v: 'keep', label: 'Bâti conservé' }, { v: 'rebuild', label: 'Reconstruction' }]} />
            </>
          )}
          <div className="mt-3 flex items-center justify-between">
            <span className="text-[10px] font-medium uppercase tracking-wide text-txt-dim">{fmtInt(nSelection)} parcelles analysées</span>
            {effQ.isFetching && <span className="text-[10px] text-txt-ghost">mise à jour…</span>}
          </div>
          <div className="mt-2"><BarreRepartition segments={segments} /></div>
          <div className="mt-2.5 flex flex-col">
            {objectif === 'sale'
              ? niveauLignes.map((l) => <CheckRow key={l.key} label={l.label} n={l.n} color={l.color} on={l.on} onToggle={l.toggle} />)
              : (
                <>
                  {bandeLignes.map((l) => <CheckRow key={l.key} label={l.label} n={l.n} color={l.color} on={l.on} onToggle={l.toggle} />)}
                  {/* les statuts repliés sous « Autres parcelles · N ▸ » */}
                  {autresLignes.length > 0 && (
                    <>
                      <button data-autres onClick={() => setAutresOpen((o) => !o)}
                        className="mt-1 flex w-full items-center gap-1.5 rounded-md px-1.5 py-1.5 text-left text-[12.5px] text-txt-mut transition-colors duration-quick hover:bg-surface-2">
                        <span className="text-txt-dim">{autresOpen ? '▾' : '▸'}</span>
                        <span className="flex-1">Autres parcelles</span>
                        <span className="tnum text-txt-dim">{fmtInt(nAutres)}</span>
                      </button>
                      {autresOpen && (
                        <div className="pl-3">
                          {autresLignes.map((l) => <CheckRow key={l.key} label={l.label} n={l.n} color={l.color} on={l.on} onToggle={l.toggle} />)}
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
          </div>
          {/* FONCIER-PUBLIC-1 — la case « Inclure le foncier public » (décochée par défaut) : elle
              fait ENTRER le terrain public SANS équipement (État/commune/EP) dans la sélection.
              Les équipements publics restent toujours visibles, en « Hors projet ». */}
          <div className="mt-3 border-t border-line-2/60 pt-2.5">
            <button data-foncier-public role="checkbox" aria-checked={inclureFoncier}
              onClick={() => setInclureFoncier((v) => !v)}
              className="flex w-full items-center gap-2.5 rounded-md px-1.5 py-1.5 text-left text-[12.5px] transition-colors duration-quick hover:bg-surface-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: inclureFoncier ? FONCIER_PUBLIC_COLOR : 'transparent', border: `1.5px solid ${FONCIER_PUBLIC_COLOR}` }} />
              <span className={`min-w-0 flex-1 truncate ${inclureFoncier ? 'text-txt-hi' : 'text-txt-mut'}`}>Inclure le foncier public</span>
              <span className={`tnum ${inclureFoncier ? 'text-txt' : 'text-txt-dim'}`}>{fmtInt(nFoncierPublic)}</span>
              <span className="w-3 shrink-0 text-center text-[12px] font-bold" style={{ color: FONCIER_PUBLIC_COLOR }}>{inclureFoncier ? '✓' : ''}</span>
            </button>
            <p className="px-1.5 text-[10.5px] leading-snug text-txt-ghost">Terrains publics (État, Région, Département, commune) sans équipement en place.</p>
          </div>
          <button data-voir-parcelles onClick={() => setEtape('liste')} disabled={nCoche === 0}
            className="mt-4 shrink-0 rounded-lg bg-mint py-2.5 text-center text-[13px] font-semibold text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            Voir les {fmtInt(nCoche)} parcelles →
          </button>
        </div>
      ) : (
        /* ════════ ÉTAPE « LA LISTE » (prend tout le panneau) ════════ */
        <>
          <button data-modifier onClick={() => setEtape('choisir')}
            className="mx-5 shrink-0 rounded-lg border border-line-2 bg-bg-1 py-2 text-center text-[12.5px] font-medium text-mint hover:border-mint/50 hover:bg-mint/5">
            Modifier la recherche
          </button>
          <div className="mx-5 mt-2 shrink-0 text-[11px] text-txt-mut">{resumeLigne}</div>
          {tropLarge && (
            <div data-trop-large className="mx-5 mt-2 shrink-0 rounded-lg border border-amber/40 bg-amber-bg px-3 py-2 text-[11px] leading-snug text-amber">
              Liste trop large pour tout peindre ({fmtInt(nFiltre)}). À droite, la carte ne peint pas cette liste au-delà de {fmtInt(PAINT_CAP)} parcelles.
            </div>
          )}
          <div data-scn-scroll className="mt-2 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-5 pb-6">
            {listeQ.isLoading && !listeQ.data ? (
              <Squelette bloc label="LABUSE dresse la liste…" />
            ) : listeQ.isError ? (
              <ErrorState message="Analyse indisponible." />
            ) : parcelles.length === 0 ? (
              <EmptyState title="Aucune parcelle" hint="Aucune parcelle dans les cohortes cochées." />
            ) : (
              <>
                {parcelles.map((p) => <CarteResultat key={p.idu} p={p} objectif={objectif} scenario={scenario} />)}
                {nCoche > parcelles.length && (
                  <button onClick={() => setLimit((l) => l + PAGE)} disabled={listeQ.isFetching}
                    className="mt-1 shrink-0 rounded-lg border border-line-2 py-2 text-[11.5px] text-txt-mut hover:border-txt-dim hover:text-txt">
                    {listeQ.isFetching ? 'Chargement…' : `Charger plus (${fmtInt(nCoche - parcelles.length)} restantes)`}
                  </button>
                )}
              </>
            )}
          </div>
        </>
      )}

      {comprendre && <ComprendreModale onClose={() => setComprendre(false)} />}
    </div>
  )
}

export default AnalyseScenario
