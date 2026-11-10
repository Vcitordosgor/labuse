// ECRANS-NOV-2 — l'écran « Analyse LABUSE par scénario » (maquette docs/design/maquettes/nov-2026/
// 7-analyse-labuse.png). LIT GET /analyse/scenarios (ALGO-FIX-1) : il n'invente aucun chiffre.
// Objectif (Prospection vente / Potentiel foncier) ; en potentiel, un scénario (Bâti conservé /
// Reconstruction). Une phrase dit TOUJOURS ce qui classe. Bloc de filtres repliable en une ligne de
// résumé. Puces comptées (effectifs de l'API, ils « font le total ») + barre de répartition. Cartes
// de résultat, et un DÉTAIL par parcelle (deux gros chiffres, gain net, « Ce qui explique »,
// « À vérifier avant d'aller plus loin »). Règles de focus/sélection de l'app (vert opaque, aucun
// contour au clic) — vérifiées dans WebKit.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { getAnalyseScenarios, getAnalyseScenarioDetail, type ScnParcelle, type ScnReponse } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { BANDE_META, SIGNAL_META, type Bande } from '../../lib/status'
import {
  BANDES_CHIP, STATUTS_CHIP, NIVEAUX_CHIP, NIVEAU_META, STATUT_SCN_META,
  bandeLabel, couleurParcelle, phraseClassement, resumeFiltres,
  type NiveauChip, type Objectif, type ScnScenario,
} from '../../lib/scenario'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'

const PAGE = 40
const PAINT_CAP = 20_000     // M55-G : au-delà, la carte peint les meilleures bandes (A+B).

// ── une LIGNE À COCHER : pastille de couleur + libellé + effectif + coche (✓). La ligne entière
// bascule ; cochée = encre vive + ✓ menthe. Aucun contour au clic (règle de l'app). ────────────────
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

// ── la barre de répartition : un segment par cohorte (bande/statut, ou niveau de Signal), largeur
// proportionnelle au compte. Les effectifs « font le total ». ──────────────────────────────────────
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

// ── petite étiquette de bande / de signal (puce de carte). ────────────────────────────────────────
function Pastille({ label, color, principal }: { label: string; color: string; principal?: boolean }) {
  return (
    <span className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
      style={principal
        ? { background: color, color: '#071009' }
        : { border: `1px solid ${color}66`, color }}>
      {label}
    </span>
  )
}

function fmtSigned(n: number): string {
  return `${n >= 0 ? '+ ' : '− '}${fmtInt(Math.abs(n))} m²`
}
const NET_NEG = '#C4653C'   // orange (terracotta) : un gain net négatif (mandat §2).

// ── une carte de résultat. ────────────────────────────────────────────────────────────────────────
function CarteResultat({ p, objectif, scenario, onDetail }:
  { p: ScnParcelle; objectif: Objectif; scenario: ScnScenario; onDetail: () => void }) {
  const q = p.quantites
  const bande = bandeLabel(p.bande)
  const bandeColor = (p.bande && BANDE_META[p.bande as Bande]?.color) || '#5C7268'
  const sig = p.signal?.niveau ? SIGNAL_META[p.signal.niveau] : null
  const estime = p.statut === 'ESTIMATED'
  // parcelle à cheval : la portion productive est plus petite que le terrain → on le dit.
  const surf = p.surface_m2 ?? 0
  const zoneA = p.zone_productive?.area_m2 ?? null
  const aCheval = p.zone_productive?.zone && zoneA != null && surf > 0 && zoneA < surf * 0.98
  const typeBati = q.existing != null ? (q.existing > 0 ? 'bâti' : 'terrain nu') : null
  const faits = [surf ? `${fmtInt(surf)} m²` : null, typeBati,
    p.zone_productive?.zone ? `zone ${p.zone_productive.zone}` : null].filter(Boolean).join(' · ')

  // Le chiffre + la raison (jamais une formule sur la carte).
  let chiffre: ReactNode = null
  let raison: string | null = null
  if (objectif === 'sale') {
    chiffre = p.signal?.p != null
      ? <>Signal {p.signal.niveau} — <span className="tnum">{p.signal.p.toFixed(2).replace('.', ',')}</span></>
      : <span className="text-txt-dim">Signal non évalué</span>
  } else if (scenario === 'rebuild') {
    const net = q.net_signed
    chiffre = (q.project_total != null && q.existing != null && net != null) ? (
      <span>Projet <span className="tnum">{fmtInt(q.project_total)} m²</span> · existant <span className="tnum">{fmtInt(q.existing)} m²</span>
        {' · '}<span className="tnum font-semibold" style={{ color: net < 0 ? NET_NEG : undefined }}>{fmtSigned(net)}</span></span>
    ) : <span className="text-txt-mut">{STATUT_SCN_META[p.statut]?.label ?? 'Calcul à compléter'}</span>
    raison = net != null && net < 0 ? "l'existant dépasse les règles actuelles"
      : q.existing && q.existing > 0 ? `démolition ${fmtInt(q.existing)} m² à prévoir`
      : q.existing === 0 ? 'terrain nu — aucune démolition' : null
  } else { // keep
    chiffre = q.additional != null && estime ? (
      <span><span className="tnum font-semibold text-mint">+ {fmtInt(q.additional)} m²</span> de plancher
        {aCheval && <span className="text-txt-mut"> — sur la portion {p.zone_productive!.zone} ({fmtInt(zoneA!)} m²)</span>}</span>
    ) : <span className="text-txt-mut">{STATUT_SCN_META[p.statut]?.label ?? bande ?? '—'}</span>
  }

  const scnLabel = scenario === 'rebuild' ? 'Reconstruction' : 'Bâti conservé'
  // En potentiel, la CARTE ENTIÈRE ouvre le détail (mandat : « clic sur une carte de résultat → détail »).
  // En prospection, pas de détail : la carte est statique (le Signal est l'histoire).
  const cliquable = objectif === 'potential'
  return (
    <div data-carte-resultat={p.idu} role={cliquable ? 'button' : undefined} tabIndex={cliquable ? 0 : undefined}
      onClick={cliquable ? onDetail : undefined}
      onKeyDown={cliquable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onDetail() } } : undefined}
      className={`shrink-0 rounded-[10px] border border-line-2 bg-surface-3 px-4 py-3 ${cliquable ? 'cursor-pointer transition-colors duration-quick hover:border-mint/50' : ''}`}>
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span className="shrink-0 font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{p.idu}</span>
        {/* en potentiel : bande principale + Signal secondaire ; en prospection : Signal principal + bande secondaire. */}
        {objectif === 'sale' ? (
          <>
            {sig && <Pastille label={NIVEAU_META[p.signal!.niveau as NiveauChip]?.label ?? sig.label} color={sig.color} principal />}
            {bande && <Pastille label={bande} color={bandeColor} />}
          </>
        ) : (
          <>
            {estime && bande ? <Pastille label={bande} color={bandeColor} principal />
              : <Pastille label={STATUT_SCN_META[p.statut]?.label ?? '—'} color={couleurParcelle(p.statut, p.bande)} principal />}
            {sig && <span className="text-[10.5px] text-txt-dim">Signal {sig.label.replace('Signal ', '')}</span>}
          </>
        )}
      </div>
      <div className={`mt-1 truncate text-[11px] ${p.adresse ? 'text-txt-dim' : 'text-txt-ghost'}`}>
        {p.adresse ?? 'Adresse non disponible'}
      </div>
      {faits && <div className="mt-0.5 truncate text-[11px] text-txt-mut tnum">{faits}</div>}
      <div className="mt-1.5 text-[12.5px] text-txt">{chiffre}</div>
      {raison && <div className="mt-0.5 text-[11px] text-txt-mut">▾ {raison}</div>}
      {objectif === 'potential' && (
        <div className="mt-2 flex items-center justify-between border-t border-line-2/60 pt-2">
          <span className="text-[10.5px] text-txt-dim">{scnLabel}</span>
          {/* affordance visuelle : la carte ENTIÈRE est cliquable (pas un bouton imbriqué). */}
          <span data-voir-detail className="text-[11px] font-medium text-mint">Voir le détail →</span>
        </div>
      )}
    </div>
  )
}

// ── le DÉTAIL d'une parcelle (overlay) : enrich=1 pour C/E exacts + facteurs. ──────────────────────
function DetailOverlay({ idu, scenario, onClose }:
  { idu: string; scenario: ScnScenario; onClose: () => void }) {
  const d = useQuery({
    queryKey: ['scn-detail', idu, scenario],
    queryFn: () => getAnalyseScenarioDetail(idu, { scenario }),
  })
  const p = d.data?.parcelles[0]
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc)
  }, [onClose])
  const q = p?.quantites
  const net = q?.net_signed
  const det = p?.details
  // « Ce qui explique » : points × facteurs = score → bande (ce que le moteur a fait).
  const facteurs = det ? [
    det.pente_pct != null ? `pente ${Math.round(det.pente_pct)} %` : null,
    det.f_forme != null && det.f_forme < 1 ? 'forme étroite' : 'forme régulière',
    det.f_acces != null && det.f_acces < 1 ? 'accès non identifié' : 'accès identifié',
    p?.zone_productive?.zone ? `zone ${p.zone_productive.zone}` : null,
  ].filter(Boolean).join(' · ') : null

  return (
    <div className="absolute inset-0 z-40 flex justify-end bg-black/40" onClick={onClose}>
      <div className="h-full w-full max-w-[460px] overflow-y-auto border-l border-line-2 bg-bg-1 p-5"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wide text-txt-dim">Détail · <span className="font-mono normal-case tracking-tight text-txt">{idu}</span></span>
          <button onClick={onClose} className="text-txt-dim hover:text-txt" aria-label="Fermer le détail">✕</button>
        </div>
        {d.isLoading && <div className="mt-6"><Squelette bloc label="Calcul du détail…" /></div>}
        {d.isError && <div className="mt-6"><ErrorState message="Détail indisponible." /></div>}
        {p && (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-3">
                <div className="font-display text-[26px] font-bold leading-none text-txt-hi tnum">
                  {q?.project_total != null ? fmtInt(q.project_total) : '—'} <span className="text-[14px] font-normal text-txt-mut">m²</span></div>
                <div className="mt-1 text-[10.5px] uppercase tracking-wide text-txt-dim">
                  {scenario === 'rebuild' ? 'Capacité du nouveau projet' : 'Capacité du projet'}</div>
              </div>
              <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-3">
                <div className="font-display text-[26px] font-bold leading-none text-txt-hi tnum">
                  {q?.existing != null ? fmtInt(q.existing) : '—'} <span className="text-[14px] font-normal text-txt-mut">m²</span></div>
                <div className="mt-1 text-[10.5px] uppercase tracking-wide text-txt-dim">Existant</div>
              </div>
            </div>
            {net != null && (
              <div className="mt-3 flex items-center justify-between rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
                <span className="text-[11.5px] text-txt-mut">Gain net</span>
                <span className="font-display text-[17px] font-bold tnum" style={{ color: net < 0 ? NET_NEG : '#4ADE80' }}>{fmtSigned(net)}</span>
              </div>
            )}
            <div className="mt-5">
              <div className="text-[10.5px] font-medium uppercase tracking-wide text-txt-dim">Ce qui explique</div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-txt">
                {bandeLabel(p.bande ?? p.bande_provisoire) && det?.score_brut != null ? (
                  <>Points de la capacité × facteurs ({facteurs}) = score {det.score_brut} → bande <span className="font-medium">{bandeLabel(p.bande ?? p.bande_provisoire)}</span>.</>
                ) : <>{p.libelle ?? STATUT_SCN_META[p.statut]?.label}{facteurs ? ` — ${facteurs}.` : '.'}</>}
              </p>
            </div>
            {p.vigilance?.length > 0 && (
              <div className="mt-5">
                <div className="text-[10.5px] font-medium uppercase tracking-wide text-txt-dim">À vérifier avant d'aller plus loin</div>
                <ul className="mt-1.5 space-y-1.5">
                  {p.vigilance.map((v, i) => (
                    <li key={i} className="flex gap-1.5 text-[11.5px] leading-snug text-txt-mut"><span className="shrink-0 text-amber">·</span><span>{v}</span></li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
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
          <p><span className="text-txt">Prospection vente</span> classe par <span className="text-txt">Signal de mutation à 12 mois</span> : qui est susceptible de bouger. La bande foncière est indicative, elle ne classe pas.</p>
          <p><span className="text-txt">Potentiel foncier</span> classe par <span className="text-txt">bande</span> puis par la quantité du scénario. En <span className="text-txt">bâti conservé</span>, la surface de plancher supplémentaire ; en <span className="text-txt">reconstruction</span>, la capacité du nouveau projet, avec un gain net signé (négatif s'il perd).</p>
          <p>Les <span className="text-txt">effectifs</span> des puces portent sur toute la sélection : ils font le total. Une bande est servie telle quelle par le moteur ; « À vérifier », « À différer », « Aucun ajout », « Hors projet » et « Calcul à compléter » isolent ce que le moteur refuse de donner pour sûr.</p>
          <p>Aucun chiffre n'est inventé : tout vient du run servi. Le <span className="text-txt">détail</span> montre le calcul (points × facteurs = score → bande) et ce qui reste à vérifier.</p>
        </div>
      </div>
    </div>
  )
}

// Cohortes cochées par défaut : Excellente + Bonne en potentiel (maquette) ; Fort + Moyen en vente.
type Coches = { bands: string[]; statuts: string[]; niveaux: NiveauChip[] }
const COCHES_DEFAUT = (o: Objectif): Coches =>
  o === 'sale' ? { bands: [], statuts: [], niveaux: ['fort', 'moyen'] }
    : { bands: ['A', 'B'], statuts: [], niveaux: [] }

export function AnalyseScenario() {
  // ECRANS-NOV-2 (placement) — le panneau vit DANS la colonne de gauche, à côté de la carte : il lit
  // le JEU DE FILTRES GLOBAL (la sélection de l'analyse), et « ← Retour » revient aux filtres.
  const filters = useApp((s) => s.filters)
  const retourFiltres = useApp((s) => s.retourFiltres)
  const [etape, setEtape] = useState<'choisir' | 'liste'>('choisir')
  const [objectif, setObjectif] = useState<Objectif>('potential')
  const [scenario, setScenario] = useState<ScnScenario>('keep')
  const [coches, setCoches] = useState<Coches>(COCHES_DEFAUT('potential'))
  const [limit, setLimit] = useState(PAGE)
  const [detailIdu, setDetailIdu] = useState<string | null>(null)
  const [comprendre, setComprendre] = useState(false)

  // Changer d'objectif remet les cases cochées sur le défaut de ce nouvel objectif (bandes ≠ niveaux).
  useEffect(() => { setCoches(COCHES_DEFAUT(objectif)) }, [objectif])
  useEffect(() => { setLimit(PAGE) }, [filters, objectif, scenario, coches, etape])

  // ── EFFECTIFS (étape « Choisir » + le N de l'étape « Liste ») : une requête limit=0, CACHÉE côté
  // serveur (30 s). `placeholderData=prev` → changer d'objectif ou de scénario GARDE l'affichage
  // précédent le temps de la mise à jour (jamais « 0 parcelle »). C'est aussi le fix du bug (4) :
  // les effectifs sont RE-TIRÉS pour le scénario choisi (plus les chiffres du bâti conservé). ──────
  const effQ = useQuery({
    queryKey: ['scn-eff', filters, objectif, scenario],
    queryFn: () => getAnalyseScenarios(filters, { mode: objectif, scenario, limit: 0 }),
    placeholderData: (prev) => prev,
  })
  const data: ScnReponse | undefined = effQ.data
  const eff = data?.effectifs
  const nSelection = data?.n_selection ?? 0
  const tropLarge = nSelection > PAINT_CAP

  // ── LISTE (étape « Liste ») : la page des cohortes cochées. Activée à l'étape Liste seulement. ──
  const listeQ = useQuery({
    queryKey: ['scn-liste', filters, objectif, scenario, coches, limit],
    queryFn: () => getAnalyseScenarios(filters, {
      mode: objectif, scenario, limit,
      bands: coches.bands, statuts: coches.statuts, niveaux: coches.niveaux,
    }),
    enabled: etape === 'liste',
    placeholderData: (prev) => prev,
  })

  // La liste des lignes à cocher + les segments de la barre, selon l'objectif. Chaque ligne porte
  // son effectif (servi par l'API) ; une case cochée s'ajoute, jamais ne remplace (plusieurs à voir).
  const { lignes, segments } = useMemo(() => {
    if (!eff) return { lignes: [] as { key: string; label: string; n: number; color: string; on: boolean; toggle: () => void }[], segments: [] }
    const toggle = (famille: 'bands' | 'statuts' | 'niveaux', key: string) => () =>
      setCoches((c) => {
        const arr = c[famille] as string[]
        const next = arr.includes(key) ? arr.filter((x) => x !== key) : [...arr, key]
        return { ...c, [famille]: next }
      })
    if (objectif === 'sale') {
      const ps = eff.par_signal ?? {}
      const segs = NIVEAUX_CHIP.map((k) => ({ color: NIVEAU_META[k].color, n: ps[k] ?? 0, label: NIVEAU_META[k].label }))
      const lg = NIVEAUX_CHIP.map((k) => ({ key: k, label: NIVEAU_META[k].label, n: ps[k] ?? 0,
        color: NIVEAU_META[k].color, on: coches.niveaux.includes(k), toggle: toggle('niveaux', k) }))
      return { lignes: lg, segments: segs }
    }
    const pb = eff.par_bande, pst = eff.par_statut
    const segs = [
      ...BANDES_CHIP.map((b) => ({ color: BANDE_META[b].color, n: pb[b] ?? 0, label: BANDE_META[b].label })),
      ...STATUTS_CHIP.map((s) => ({ color: STATUT_SCN_META[s].color, n: pst[s] ?? 0, label: STATUT_SCN_META[s].label })),
    ]
    const lg = [
      ...BANDES_CHIP.map((b) => ({ key: b, label: BANDE_META[b].label, n: pb[b] ?? 0,
        color: BANDE_META[b].color, on: coches.bands.includes(b), toggle: toggle('bands', b) })),
      ...STATUTS_CHIP.map((s) => ({ key: s, label: STATUT_SCN_META[s].label, n: pst[s] ?? 0,
        color: STATUT_SCN_META[s].color, on: coches.statuts.includes(s), toggle: toggle('statuts', s) })),
    ]
    return { lignes: lg, segments: segs }
  }, [eff, objectif, coches])

  // N = somme des effectifs cochés (immédiat, dérivé des effectifs — pas d'attente de la liste).
  const nCoche = useMemo(() => {
    if (!eff) return 0
    if (objectif === 'sale') return coches.niveaux.reduce((s, k) => s + (eff.par_signal?.[k] ?? 0), 0)
    return coches.bands.reduce((s, b) => s + (eff.par_bande[b] ?? 0), 0)
      + coches.statuts.reduce((s, k) => s + (eff.par_statut[k] ?? 0), 0)
  }, [eff, objectif, coches])

  // Libellés des cohortes cochées (pour la ligne de résumé de l'étape « Liste »).
  const labelsCoches = useMemo(() => {
    if (objectif === 'sale') return coches.niveaux.map((k) => NIVEAU_META[k].label)
    return [...coches.bands.map((b) => BANDE_META[b as Bande]?.label ?? b),
      ...coches.statuts.map((s) => STATUT_SCN_META[s]?.label ?? s)]
  }, [objectif, coches])

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
          <p className="mt-3 text-[11px] leading-snug text-txt-mut">{phraseClassement(objectif, scenario)}</p>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-[10px] font-medium uppercase tracking-wide text-txt-dim">{fmtInt(nSelection)} parcelles analysées</span>
            {effQ.isFetching && <span className="text-[10px] text-txt-ghost">mise à jour…</span>}
          </div>
          <div className="mt-2"><BarreRepartition segments={segments} /></div>
          {/* la liste des bandes et statuts à cocher (plusieurs possibles), chacun son effectif */}
          <div className="mt-2.5 flex flex-col">
            {lignes.map((l) => <CheckRow key={l.key} label={l.label} n={l.n} color={l.color} on={l.on} onToggle={l.toggle} />)}
          </div>
          {/* un seul bouton : « Voir les N parcelles » */}
          <button data-voir-parcelles onClick={() => setEtape('liste')} disabled={nCoche === 0}
            className="mt-4 shrink-0 rounded-lg bg-mint py-2.5 text-center text-[13px] font-semibold text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            Voir les {fmtInt(nCoche)} parcelles →
          </button>
        </div>
      ) : (
        /* ════════ ÉTAPE « LA LISTE » (prend tout le panneau) ════════ */
        <>
          {/* les choix, repliés en une ligne de résumé — « Modifier ▾ » rouvre l'étape « Choisir » */}
          <button data-modifier onClick={() => setEtape('choisir')}
            className="mx-5 flex shrink-0 items-center justify-between rounded-lg border border-line-2 bg-bg-1 px-3 py-2 text-left hover:border-txt-dim">
            <span className="min-w-0 truncate text-[11.5px] text-txt">{resumeFiltres(objectif, scenario, labelsCoches)}
              <span className="text-txt-dim"> · {fmtInt(nCoche)} parcelles</span></span>
            <span className="shrink-0 pl-2 text-[11px] font-medium text-mint">Modifier ▾</span>
          </button>
          {tropLarge && (
            <div data-trop-large className="mx-5 mt-2 shrink-0 rounded-lg border border-amber/40 bg-amber-bg px-3 py-2 text-[11px] leading-snug text-amber">
              Sélection trop large pour tout peindre ({fmtInt(nSelection)}). À droite, la carte peint les meilleures bandes (Excellente + Bonne).
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
                {parcelles.map((p) => (
                  <CarteResultat key={p.idu} p={p} objectif={objectif} scenario={scenario}
                    onDetail={() => setDetailIdu(p.idu)} />
                ))}
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

      {detailIdu && (
        <DetailOverlay idu={detailIdu} scenario={scenario} onClose={() => setDetailIdu(null)} />
      )}
      {comprendre && <ComprendreModale onClose={() => setComprendre(false)} />}
    </div>
  )
}

export default AnalyseScenario
