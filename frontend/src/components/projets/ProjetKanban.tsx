import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  getCadrageCompteur, getParcoursEtat, getProjet, patchProjet, projetPdfUrl, setStatutParcelle,
  type Cadrage, type ParcoursEtat, type ParcoursItem, type StatutParcelle,
} from '../../lib/api'
import { AlgoExplainer, ScoringExplainer } from '../panel/LeftPanel'
import { FiltreFacettes } from '../panel/FiltreFacettes'
import { FiltreProvider } from '../panel/filtreContext'
import { fmtDate, fmtEurCompact, fmtInt, fmtM2, iduCourt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Loading } from '../Loading'

const PAGE = 50   // PROJETS-V5 (E4) — pagination « 50 par page · page X/Y »

/** PROJETS-FIX F2 — le PÉRIMÈTRE, en étiquette de titre (une seule fois). */
function perimetreLabel(c: Cadrage): string {
  const cs = c.communes ?? []
  return !cs.length ? "toute l'île" : cs.length === 1 ? cs[0] : `${cs.length} communes`
}

/** PROJETS-V5 (E4/E7) — l'état du bien + sa constructibilité, dits en clair sur la sous-ligne mono. */
function etatLabel(etat_bien?: string | null): string {
  return etat_bien === 'nu' ? 'Nu'
    : etat_bien === 'bati_encore' ? 'Bâti · encore constructible'
      : etat_bien === 'bati_max' ? 'Bâti · au max'
        : etat_bien === 'bati' ? 'Bâti' : ''
}

/** PROJETS-V4 (V1) — la pastille de tier : Priorité (rouge) · À suivre (orange) · autres (gris). */
const TIER_DOT: Record<string, string> = { brulante: TOKENS.stEcartee, chaude: TOKENS.stCreuser }
function tierDot(tier: string | null): string { return (tier && TIER_DOT[tier]) || '#4a4a4a' }

/** retire l'item de son groupe et le pousse dans le groupe cible — maj optimiste. */
function moveItem(etat: ParcoursEtat, idu: string, statut: StatutParcelle): ParcoursEtat {
  const from: StatutParcelle | null =
    etat.proposees.some((x) => x.idu === idu) ? 'proposee'
      : etat.retenues.some((x) => x.idu === idu) ? 'retenue'
        : etat.ecartees.some((x) => x.idu === idu) ? 'ecartee'
          : etat.a_analyser.some((x) => x.idu === idu) ? 'a_analyser' : null
  let moved: ParcoursItem | null = null
  const strip = (arr: ParcoursItem[]) => arr.filter((x) => {
    if (x.idu === idu) { moved = { ...x, statut }; return false }
    return true
  })
  const proposees = strip(etat.proposees), retenues = strip(etat.retenues)
  const ecartees = strip(etat.ecartees), a_analyser = strip(etat.a_analyser)
  if (moved) {
    if (statut === 'retenue') retenues.push(moved)
    else if (statut === 'ecartee') ecartees.push(moved)
    else if (statut === 'a_analyser') a_analyser.push(moved)
    else proposees.push(moved)
  }
  const counts = { ...etat.counts }
  if (moved && from && from !== statut) {
    counts[from] = Math.max(0, (counts[from] ?? 0) - 1)
    counts[statut] = (counts[statut] ?? 0) + 1
  }
  return { ...etat, proposees, retenues, ecartees, a_analyser, counts }
}

/** PROJETS-V5 (E7) — l'adresse ou « sans adresse — Commune » (italique gris) + l'IDU en clair. */
function AdresseLigne({ it, mono }: { it: ParcoursItem; mono?: string }) {
  return (
    <div className="min-w-0">
      {it.adresse
        ? <b className="block truncate text-[13px] font-medium text-txt-hi">{it.adresse}</b>
        : <b className="block truncate text-[13px] font-normal italic text-txt-dim">sans adresse — {it.commune}</b>}
      <span className="block truncate font-mono text-[10.5px] text-txt-mut">{iduCourt(it.idu)}{mono ? ` · ${mono}` : ''}</span>
    </div>
  )
}

/** PROJETS-V5 (E4) — jusqu'à deux signaux en chips (le fort en rouge) ; « aucun signal » en gris. */
function SignauxLigne({ signaux }: { signaux?: { label: string; fort: boolean }[] }) {
  const sg = signaux ?? []
  if (!sg.length) return <span className="text-[10.5px] text-txt-dim">aucun signal</span>
  return (
    <div className="flex flex-wrap gap-1">
      {sg.map((s, i) => (
        <span key={i} className={`rounded-[5px] border px-1.5 py-px text-[10.5px] ${s.fort ? 'border-st-ecartee/40 text-st-ecartee' : 'border-line-2 text-txt-mut'}`}>{s.label}</span>
      ))}
    </div>
  )
}

/** PROJETS-V5 (E4) — LA LIGNE « À trier » : pastille · adresse (IDU + état/constructibilité mono) ·
 *  jusqu'à 2 signaux · surface (droite) · gestes ✓/✕. Plus de colonne « marché commune ». */
function LigneParcelle({ it, onDragStart, onRetenir, onEcarter, onFiche }: {
  it: ParcoursItem; onDragStart: () => void; onRetenir: () => void; onEcarter: () => void; onFiche: () => void
}) {
  return (
    <div draggable onDragStart={onDragStart} data-tri-ligne={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className="grid cursor-pointer grid-cols-[14px_1fr_170px_76px_66px] items-center gap-3 border-b border-line/50 px-3.5 py-2 transition-colors duration-quick hover:bg-surface-2"
      title="Ouvrir la fiche · glisser pour décider">
      <span className="h-[7px] w-[7px] rounded-full" style={{ background: tierDot(it.tier) }} />
      <AdresseLigne it={it} mono={etatLabel(it.etat_bien)} />
      <SignauxLigne signaux={it.signaux} />
      <span className="text-right font-mono text-[11.5px] text-txt-mut">{it.surface_m2 != null ? fmtM2(it.surface_m2) : '—'}</span>
      <div className="flex justify-end gap-1.5">
        <button data-tri-retenir onClick={onRetenir} title="Retenir"
          className="flex h-6 w-[26px] items-center justify-center rounded-md border border-mint/40 text-[12px] text-mint transition-colors duration-quick hover:bg-mint/15">✓</button>
        <button data-tri-ecarter onClick={onEcarter} title="Écarter"
          className="flex h-6 w-[26px] items-center justify-center rounded-md border border-st-ecartee/40 text-[12px] text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10">✕</button>
      </div>
    </div>
  )
}

/** PROJETS-V5 (E6/E7) — la MINI-LIGNE (Retenues / Écartées) : pastille, adresse (ou « sans adresse »),
 *  IDU, bouton retour. Liste COMPLÈTE qui défile (plus de « + N autres »). */
function MiniLigne({ it, col, onDragStart, onRetour, onFiche }: {
  it: ParcoursItem; col: StatutParcelle; onDragStart: () => void; onRetour: () => void; onFiche: () => void
}) {
  const ecartee = col === 'ecartee'
  return (
    <div draggable onDragStart={onDragStart} data-mini-ligne={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className="grid cursor-pointer grid-cols-[14px_1fr_26px] items-center gap-2 border-b border-line/50 px-3.5 py-2 transition-colors duration-quick hover:bg-surface-2"
      title="Ouvrir la fiche">
      <span className="h-[7px] w-[7px] shrink-0 rounded-full" style={{ background: tierDot(it.tier) }} />
      <div className="min-w-0">
        {it.adresse
          ? <b className="block truncate text-[12.5px] font-medium text-txt">{it.adresse}</b>
          : <b className="block truncate text-[12.5px] font-normal italic text-txt-dim">sans adresse — {it.commune}</b>}
        <span className="block truncate font-mono text-[10px] text-txt-dim">{iduCourt(it.idu)}</span>
      </div>
      <button data-mini-retour onClick={onRetour} title={ecartee ? 'Récupérer (→ à trier)' : 'Remettre à trier'}
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-[12px] transition-colors duration-quick ${ecartee ? 'border-mint/40 text-mint hover:bg-mint/15' : 'border-line-2 text-txt-mut hover:border-mint hover:text-mint'}`}>↩</button>
    </div>
  )
}

/** PROJETS-V5 (E5) — le TIROIR « Filtrer » : les critères du wizard (FiltreFacettes), servis par la
 *  MÊME requête. Le bouton de validation ANNONCE le résultat (« Voir N parcelles ») calculé en direct.
 *  « Tout effacer » remet le cadrage du projet (sf = null). */
function FiltreDrawer({ cadrageProjet, initial, onApply, onClear, onClose }: {
  cadrageProjet: Cadrage; initial: Cadrage | null
  onApply: (sf: Cadrage) => void; onClear: () => void; onClose: () => void
}) {
  const communes = cadrageProjet.communes ?? []
  const [facettes, setFacettes] = useState<Filters>(() => ({ ...EMPTY_FILTERS, ...(initial ?? cadrageProjet) }))
  const binding = useMemo(() => ({
    filters: facettes,
    setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => setFacettes((c) => ({ ...c, [k]: v })),
  }), [facettes])
  const sfOut = useMemo((): Cadrage => {
    const out: Cadrage = {}
    for (const [k, v] of Object.entries(facettes) as [keyof Filters, unknown][]) {
      const empty = v === null || v === false || (Array.isArray(v) && v.length === 0)
      if (!empty && k !== 'analyseLabuse') (out as Record<string, unknown>)[k] = v
    }
    if (communes.length) out.communes = communes; else delete out.communes
    return out
  }, [facettes, communes])
  const cnt = useQuery({ queryKey: ['drawer-compteur', JSON.stringify(sfOut)], queryFn: () => getCadrageCompteur(sfOut) })

  return (
    <div data-filtre-drawer className="w-[300px] shrink-0 overflow-y-auto rounded-xl border border-line-2 bg-surface-1 p-3.5 shadow-elev-2">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-[13px] font-semibold text-txt-hi">Filtrer les parcelles à trier</h4>
        <button data-drawer-close onClick={onClose} className="text-txt-dim hover:text-txt-hi" aria-label="Fermer">✕</button>
      </div>
      <FiltreProvider value={binding}><FiltreFacettes compteurScope={{ communes }} /></FiltreProvider>
      <div className="mt-3 flex gap-2">
        <button data-drawer-clear onClick={() => { setFacettes({ ...EMPTY_FILTERS, ...cadrageProjet }); onClear() }}
          className="flex-1 rounded-md border border-line-2 py-1.5 text-center text-[11.5px] text-txt-mut transition-colors duration-quick hover:text-txt">Tout effacer</button>
        <button data-drawer-apply onClick={() => onApply(sfOut)}
          className="flex-1 rounded-md border border-mint bg-mint py-1.5 text-center text-[11.5px] font-semibold text-mint-ink transition-[filter] duration-quick hover:brightness-110">
          Voir {cnt.data ? cnt.data.vivier.toLocaleString('fr-FR') : '…'} parcelles</button>
      </div>
    </div>
  )
}

// ── libellés des facettes actives (E4) — pour les puces retirables sous la barre ──
function facetteLabels(c: Cadrage): { key: keyof Filters; label: string }[] {
  const out: { key: keyof Filters; label: string }[] = []
  if (c.etatSol?.length) out.push({ key: 'etatSol', label: c.etatSol.map((e) => (e === 'nu' ? 'terrain nu' : 'bâti')).join(' / ') })
  if (c.surfaceMin != null) out.push({ key: 'surfaceMin', label: `surface ≥ ${c.surfaceMin} m²` })
  if (c.surfaceMax != null) out.push({ key: 'surfaceMax', label: `surface ≤ ${c.surfaceMax} m²` })
  if (c.zonePlu?.length) out.push({ key: 'zonePlu', label: `zone ${c.zonePlu.join('/')}` })
  if (c.zonagePlu?.length) out.push({ key: 'zonagePlu', label: `zonage ${c.zonagePlu.join('/')}` })
  if (c.signaux?.length) out.push({ key: 'signaux', label: `${c.signaux.length} signal${c.signaux.length > 1 ? 'aux' : ''}` })
  return out
}

/** VUE PROJET V5 — quatre étages (identité · analyse · progression · tri), lisibles d'un coup d'œil. */
export function ProjetKanban({ pid, nom }: { pid: number; nom: string }) {
  const qc = useQueryClient()
  const { setOpenProjet, select, algoModale, setAlgoModale } = useApp()
  const [drag, setDrag] = useState<{ idu: string; from: StatutParcelle } | null>(null)
  const [overCol, setOverCol] = useState<StatutParcelle | null>(null)
  const [editing, setEditing] = useState(false)
  const [nomInput, setNomInput] = useState(nom)
  const [navTier, setNavTier] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [sousFiltre, setSousFiltre] = useState<Cadrage | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [totalProp, setTotalProp] = useState(0)

  const sfKey = JSON.stringify(sousFiltre ?? {})
  const projetQ = useQuery({ queryKey: ['projet', pid], queryFn: () => getProjet(pid), enabled: pid > 0 })
  const parcoursKey = ['parcours', pid, page, navTier, sfKey]
  const etatQ = useQuery({ queryKey: parcoursKey, enabled: pid > 0, placeholderData: (prev) => prev,
    queryFn: () => getParcoursEtat(pid, page * PAGE, PAGE, navTier, sousFiltre) })

  useEffect(() => { setPage(0) }, [navTier, sfKey])   // changer de filtre → page 1

  const decide = useMutation({
    mutationFn: ({ idu, statut }: { idu: string; statut: StatutParcelle }) => setStatutParcelle(pid, idu, statut),
    onMutate: async ({ idu, statut }) => {
      await qc.cancelQueries({ queryKey: ['parcours', pid] })
      const prev = qc.getQueryData<ParcoursEtat>(parcoursKey)
      if (prev) qc.setQueryData<ParcoursEtat>(parcoursKey, moveItem(prev, idu, statut))
      return { prev }
    },
    onError: (_e, _v, ctx) => { if (ctx?.prev) qc.setQueryData(parcoursKey, ctx.prev) },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['parcours', pid] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
      qc.invalidateQueries({ queryKey: ['projets'] })
    },
  })
  const patch = useMutation({
    mutationFn: (body: { nom?: string; statut?: string }) => patchProjet(pid, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['projet', pid] }); qc.invalidateQueries({ queryKey: ['projets'] }) },
  })

  const etat = etatQ.data
  const projet = projetQ.data
  // `analyse` (bandeau + chips) n'est servi qu'à la page 0 : on le mémorise pour qu'il reste en paginant.
  const [analyse, setAnalyse] = useState<ParcoursEtat['analyse'] | null>(null)
  useEffect(() => { if (etat?.analyse) setAnalyse(etat.analyse) }, [etat?.analyse])
  // RETOURS-3 R8 — le RESTANT à trier par tier (chips) est servi à la page 0 : on le mémorise comme `analyse`.
  const [restant, setRestant] = useState<ParcoursEtat['restant'] | null>(null)
  useEffect(() => { if (etat?.restant) setRestant(etat.restant) }, [etat?.restant])
  // RETOURS-3 R10 — le bandeau d'analyse est REPLIÉ par défaut (une ligne) ; « Voir pourquoi » déplie
  // le contenu complet (phrase gravée entière, signaux, valeurs, run). Fond vert et formulation inchangés.
  const [analyseOuvert, setAnalyseOuvert] = useState(false)
  useEffect(() => { if (etat?.total_retenues != null) setTotalProp(etat.counts.proposee) }, [etat?.total_retenues, etat?.counts?.proposee])
  const deZero = Boolean((projet?.cadrage as Record<string, unknown> | undefined)?.__de_zero__)
  const ouvrirCarte = () => { const s = useApp.getState(); s.setOpenProjet(null); s.setView('cartes') }

  const c = etat?.counts ?? { proposee: 0, retenue: 0, ecartee: 0, a_analyser: 0 }
  const vivier = analyse?.total ?? (c.proposee + c.retenue + c.ecartee + (c.a_analyser ?? 0))
  const pages = Math.max(1, Math.ceil(totalProp / PAGE))
  // recherche client sur la page chargée (adresse / IDU) — la pagination porte le vivier complet.
  const proposeesVues = etat?.proposees ?? []
  const cadrageEffectif = sousFiltre ?? (projet?.cadrage ?? {})
  const puces = facetteLabels(cadrageEffectif)
  const retirerFacette = (k: keyof Filters) => {
    const next = { ...cadrageEffectif } as Record<string, unknown>
    if (k === 'surfaceMin' || k === 'surfaceMax') delete next[k]; else delete next[k]
    setSousFiltre(next as Cadrage)
  }

  const onDrop = (target: StatutParcelle) => {
    if (drag && drag.from !== target) decide.mutate({ idu: drag.idu, statut: target })
    setDrag(null); setOverCol(null)
  }

  const carte = 'rounded-xl border border-line-2 bg-surface-1'
  const btn = 'min-h-7 rounded-md border border-line-2 px-2.5 py-1 text-[11.5px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi'

  return (
    <div data-projet-kanban className="flex min-w-0 flex-1 flex-col gap-3.5 overflow-hidden bg-bg p-4 sm:p-5">
      {/* ÉTAGE 1 — IDENTITÉ */}
      <div className={`shrink-0 ${carte} px-4 py-3`}>
        <button onClick={() => setOpenProjet(null)} className="min-h-6 text-[11px] text-txt-dim transition-colors duration-quick hover:text-txt-hi"
          title="Revenir à la liste des projets">← Mes projets</button>
        <div className="mt-1 flex flex-wrap items-center gap-2.5">
          {editing ? (
            <input data-kanban-nom-input autoFocus value={nomInput} onChange={(e) => setNomInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && nomInput.trim()) { patch.mutate({ nom: nomInput.trim() }); setEditing(false) }
                if (e.key === 'Escape') { setNomInput(nom); setEditing(false) }
              }}
              onBlur={() => { if (nomInput.trim() && nomInput !== nom) patch.mutate({ nom: nomInput.trim() }); setEditing(false) }}
              className="rounded-md border border-mint/40 bg-surface-3 px-2 py-1 font-display text-lg font-bold text-txt-hi outline-none focus:border-mint" />
          ) : (
            <h1 data-kanban-nom className="font-display text-xl font-bold text-txt-hi" title={projet?.nom ?? nom}>{projet?.nom ?? nom}</h1>
          )}
          {projet && <span data-kanban-perimetre className="rounded border border-line-2 px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-wider text-txt-mut">{perimetreLabel(projet.cadrage)}</span>}
          {projet?.identite?.budget_eur ? <span data-kanban-budget className="rounded border border-line-2 px-2 py-0.5 font-mono text-[9.5px] uppercase tracking-wider text-txt-dim">{fmtEurCompact(projet.identite.budget_eur)} indic.</span> : null}
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            <a data-kanban-pdf href={projetPdfUrl(pid)} target="_blank" rel="noreferrer" className={btn} title="Dossier PDF — extrait figé">PDF</a>
            <button data-kanban-renommer onClick={() => { setNomInput(projet?.nom ?? nom); setEditing(true) }} className={btn}>Renommer</button>
            <button data-kanban-archiver onClick={() => { patch.mutate({ statut: 'archive' }); setOpenProjet(null) }} className={btn}>Archiver</button>
            <button data-kanban-ajouter-header onClick={ouvrirCarte}
              className="min-h-7 rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/25">+ Ajouter des parcelles</button>
          </div>
        </div>
      </div>

      {/* ÉTAGE 2 — ANALYSE (le classement est le moteur STATISTIQUE de LABUSE → vert, jamais mauve/IA).
          RETOURS-3 R10 — REPLIÉ par défaut sur une ligne ; « Voir pourquoi » déplie le contenu complet. */}
      {!deZero && analyse && analyse.total > 0 && (
        <div data-kanban-analyse className="shrink-0 rounded-xl border border-mint/25 bg-mint/[0.06] px-4 py-3">
          <div className="grid grid-cols-[38px_1fr_auto] items-center gap-3.5">
            <span className="flex h-[38px] w-[38px] items-center justify-center rounded-lg bg-mint/15 text-[18px] text-mint" aria-hidden>✦</span>
            {/* la LIGNE repliée : le résumé (formulation gravée, chiffres du cadrage) */}
            <p className="text-[13px] leading-snug text-txt-2">
              LABUSE a analysé <b className="text-txt-hi">{analyse.total.toLocaleString('fr-FR')} parcelles</b> :
              {' '}<b className="text-mint">{analyse.signalees.toLocaleString('fr-FR')}</b> ressortent
              {' '}— {analyse.priorite.toLocaleString('fr-FR')} Priorité, {analyse.a_suivre.toLocaleString('fr-FR')} À suivre.
            </p>
            <button data-kanban-pourquoi aria-expanded={analyseOuvert} onClick={() => setAnalyseOuvert((o) => !o)}
              className="shrink-0 rounded-md border border-mint/40 px-3 py-1.5 text-[12px] text-mint transition-colors duration-quick hover:bg-mint/15">
              {analyseOuvert ? 'Voir moins ▴' : 'Voir pourquoi ▾'}</button>
          </div>
          {/* le CONTENU complet déplié : phrase gravée entière + signaux + valeurs/run */}
          {analyseOuvert && (
            <div data-kanban-analyse-detail className="mt-2.5 border-t border-mint/15 pl-[50px] pt-2.5">
              <p className="text-[13.5px] leading-relaxed text-txt-2">
                LABUSE a analysé les <b className="text-txt-hi">{analyse.total.toLocaleString('fr-FR')} parcelles</b> de votre cadrage :
                {' '}<b className="text-mint">{analyse.signalees.toLocaleString('fr-FR')}</b> ont plus de chances que les autres d'être vendues
                {' '}— {analyse.priorite.toLocaleString('fr-FR')} en Priorité, {analyse.a_suivre.toLocaleString('fr-FR')} À suivre.
                {' '}Elles arrivent en tête de votre tri ; les {(analyse.total - analyse.signalees).toLocaleString('fr-FR')} autres suivent, sans jugement.
              </p>
              <p data-kanban-analyse-sub className="mt-1 text-[11px] text-txt-dim">
                {(() => {
                  const distinct = Array.from(new Set((etat?.proposees ?? []).flatMap((it) => (it.signaux ?? []).map((s) => s.label)))).slice(0, 4)
                  return distinct.length ? `Signaux détectés : ${distinct.join(', ')} · ` : ''
                })()}
                {/* RETOURS-7 Z12.2 — libellé lisible = la DATE ; l'identifiant technique du run
                    (valeurs_run.label) reste au survol et au dashboard, plus servi au client. */}
                {etat?.valeurs_run?.date ? <span title={`run ${etat.valeurs_run.label}`}>{`valeurs au ${fmtDate(etat.valeurs_run.date)}`}</span> : ''}
                {(() => { const m = (etat?.proposees ?? []).find((it) => it.marche_eur_m2 != null)?.marche_eur_m2; return m != null && projet && (projet.cadrage.communes?.length === 1) ? ` · marché ancien ${projet.cadrage.communes[0]} ~${fmtInt(m)} €/m²` : '' })()}
              </p>
              <button data-kanban-scoring onClick={() => setAlgoModale('scoring')}
                className="mt-1.5 text-[11px] text-mint transition-colors duration-quick hover:underline">Comprendre le classement →</button>
            </div>
          )}
        </div>
      )}

      {/* ÉTAGE 3 — PROGRESSION (une ligne : 3 compteurs + barre à deux segments). */}
      <div data-kanban-progression className={`shrink-0 grid grid-cols-[auto_1fr] items-center gap-4 ${carte} px-4 py-2.5`}>
        <div className="flex gap-5 font-mono text-[12px] text-txt-mut">
          <span><b className="mr-1 text-[15px] text-mint">{c.retenue}</b>retenues</span>
          <span><b className="mr-1 text-[15px] text-st-ecartee">{c.ecartee}</b>écartées</span>
          <span><b className="mr-1 text-[15px] text-txt">{(analyse ? Math.max(0, analyse.total - c.retenue - c.ecartee) : c.proposee).toLocaleString('fr-FR')}</b>à trier</span>
        </div>
        <div className="flex h-1.5 overflow-hidden rounded-full bg-surface-3">
          {vivier > 0 && <span style={{ width: `${(c.retenue / vivier) * 100}%`, background: TOKENS.mint }} />}
          {vivier > 0 && <span style={{ width: `${(c.ecartee / vivier) * 100}%`, background: TOKENS.stEcartee }} />}
        </div>
      </div>

      {/* ÉTAGE 4 — TRI : 3 colonnes (2,3 / 1 / 1) + tiroir « Filtrer » à droite. */}
      <div className="flex min-h-0 flex-1 gap-3.5">
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3.5 md:grid-cols-[2.3fr_1fr_1fr]">
          {etatQ.isLoading && <Loading label="Chargement du projet…" className="col-span-full mx-auto self-center" />}
          {COLS.map((col) => {
            const isProp = col.key === 'proposee'
            const list = isProp ? proposeesVues : (col.key === 'retenue' ? etat?.retenues ?? [] : etat?.ecartees ?? [])
            const count = col.key === 'proposee' ? totalProp : (etat?.counts?.[col.key] ?? 0)
            return (
              <div key={col.key} data-kanban-col={col.key}
                onDragOver={(e) => { e.preventDefault(); setOverCol(col.key) }}
                onDragLeave={() => setOverCol((o) => (o === col.key ? null : o))}
                onDrop={(e) => { e.preventDefault(); onDrop(col.key) }}
                className={`flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border bg-surface-1 transition-colors duration-quick ${overCol === col.key && drag && drag.from !== col.key ? 'border-mint ring-1 ring-mint/40' : 'border-line-2'}`}>
                {/* tête de colonne */}
                <div className="flex shrink-0 items-center gap-2 border-b border-line-2 bg-surface-2 px-3.5 py-2.5">
                  <span className="h-[7px] w-[7px] rounded-full" style={{ background: col.accent }} />
                  <span className="font-mono text-[9.5px] uppercase tracking-wider text-txt-mut">{col.label}</span>
                  <span data-kanban-count={col.key} className="font-mono text-[12.5px] text-mint">{count.toLocaleString('fr-FR')}</span>
                  {/* RETOURS-3 R8 — même logique que les chips : les signalées RESTANT à trier (restant), pas le total. */}
                  {isProp && restant && restant.signalees > 0 && <span className="text-[10.5px] text-txt-dim">· les {restant.signalees.toLocaleString('fr-FR')} signalées d'abord</span>}
                  {col.key === 'ecartee' && <span className="ml-auto text-[10px] text-txt-dim">réversible</span>}
                </div>

                {isProp && (
                  <>
                    {/* barre : chips classement · recherche · Filtrer */}
                    <div className="flex shrink-0 items-center gap-1.5 border-b border-line-2 px-3.5 py-2">
                      {([['', 'Tous', null], ['brulante', 'Priorité', TOKENS.stEcartee], ['chaude', 'À suivre', TOKENS.stCreuser]] as const).map(([v, l, dot]) => {
                        const on = (navTier ?? '') === v
                        // RETOURS-3 R8 — les chips comptent ce qui reste À TRIER (retenues/écartées en sortent),
                        // cohérent avec le compteur « à trier » du haut. Tous = total à trier ; Priorité/À suivre
                        // = restant par tier (servi `restant`). Le bandeau, lui, garde le total du cadrage.
                        const n = v === 'brulante' ? restant?.priorite : v === 'chaude' ? restant?.a_suivre : totalProp
                        return (
                          <button key={v || 'tous'} data-kanban-nav-tier={v || 'tous'} onClick={() => setNavTier(v || null)}
                            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick ${on ? 'border-mint/45 bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
                            {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: dot }} />}{l}{n != null ? ` ${n.toLocaleString('fr-FR')}` : ''}
                          </button>
                        )
                      })}
                      {/* RETOURS-3 R9 (Vic 31/08) — barre de recherche « adresse, IDU… » RETIRÉE de la
                          colonne À trier (le tri se fait par chips + tiroir Filtrer, pas par recherche libre). */}
                      <span className="flex-1" />
                      <button data-kanban-filtrer onClick={() => setDrawerOpen((o) => !o)}
                        className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11.5px] transition-colors duration-quick ${drawerOpen ? 'border-mint text-mint' : 'border-line-2 text-txt hover:border-mint'}`}>
                        ⚙ Filtrer{puces.length > 0 && <span className="rounded-full bg-mint px-1.5 text-[9.5px] font-bold text-mint-ink">{puces.length}</span>}</button>
                    </div>
                    {/* filtres actifs (puces retirables) */}
                    {puces.length > 0 && (
                      <div data-kanban-filtres-actifs className="flex shrink-0 flex-wrap items-center gap-1.5 border-b border-line-2 px-3.5 py-1.5 text-[11px] text-txt-dim">
                        filtres actifs :
                        {puces.map((p) => (
                          <button key={String(p.key)} onClick={() => retirerFacette(p.key)}
                            className="rounded border border-mint/35 px-2 py-px text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">{p.label} ×</button>
                        ))}
                        <button onClick={() => setSousFiltre(null)} className="rounded border border-line-2 px-2 py-px text-[11px] text-txt-dim hover:text-txt">tout effacer</button>
                      </div>
                    )}
                    {/* en-tête de colonnes */}
                    {list.length > 0 && (
                      <div data-kanban-lhead className="grid shrink-0 grid-cols-[14px_1fr_170px_76px_66px] gap-3 border-b border-line-2 px-3.5 py-1.5 font-mono text-[9.5px] uppercase tracking-wider text-txt-dim">
                        <span></span><span>Parcelle</span><span>Signaux</span><span className="text-right">Surface</span><span className="text-right">Trier</span>
                      </div>
                    )}
                  </>
                )}

                {/* liste (défile) */}
                <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
                  {list.length === 0 && (
                    <div className="m-3 rounded-lg bg-surface-2/60 py-6 text-center text-[11px] text-txt-dim">
                      {isProp ? (deZero ? 'Projet de zéro — ajoutez des parcelles depuis leurs fiches.' : (puces.length ? 'Aucune parcelle ne correspond à ce filtre.' : 'Rien à trier pour l’instant.'))
                        : col.key === 'retenue' ? 'Aucune retenue' : 'Aucune écartée'}
                    </div>
                  )}
                  {list.map((it) => (isProp ? (
                    <LigneParcelle key={it.idu} it={it}
                      onDragStart={() => setDrag({ idu: it.idu, from: 'proposee' })}
                      onRetenir={() => decide.mutate({ idu: it.idu, statut: 'retenue' })}
                      onEcarter={() => decide.mutate({ idu: it.idu, statut: 'ecartee' })}
                      onFiche={() => select(it.idu)} />
                  ) : (
                    <MiniLigne key={it.idu} it={it} col={col.key}
                      onDragStart={() => setDrag({ idu: it.idu, from: col.key })}
                      onRetour={() => decide.mutate({ idu: it.idu, statut: 'proposee' })}
                      onFiche={() => select(it.idu)} />
                  )))}
                </div>

                {/* pied : pagination (À trier) ou actions Retenues */}
                {isProp && totalProp > PAGE && (
                  <div data-kanban-pagination className="flex shrink-0 items-center justify-center gap-3 border-t border-line-2 px-3.5 py-2 text-[11.5px] text-txt-dim">
                    <button disabled={page === 0 || etatQ.isFetching} onClick={() => setPage((p) => Math.max(0, p - 1))}
                      className="text-txt-mut transition-colors duration-quick hover:text-txt disabled:opacity-30">← précéd.</button>
                    <span>{PAGE} par page · page {page + 1} / {pages.toLocaleString('fr-FR')}</span>
                    <button data-kanban-suivante disabled={page + 1 >= pages || etatQ.isFetching} onClick={() => setPage((p) => p + 1)}
                      className="text-mint transition-colors duration-quick hover:text-txt-hi disabled:opacity-30">suivante →</button>
                  </div>
                )}
                {col.key === 'retenue' && (etat?.counts?.retenue ?? 0) > 0 && (
                  <div data-kanban-retenues-actions className="flex shrink-0 gap-2 border-t border-line-2 bg-surface-2 px-3.5 py-2.5">
                    <button data-kanban-crm onClick={() => { const s = useApp.getState(); s.setOpenProjet(null); s.setView('crm') }}
                      className="flex-1 rounded-md border border-mint/40 py-1.5 text-center text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">→ CRM</button>
                    <button data-kanban-courrier onClick={() => {
                      const idus = (etat?.retenues ?? []).map((r) => r.idu)
                      const s = useApp.getState(); s.setCourrierPrefillIdus(idus); s.setOpenProjet(null); s.setView('cartes'); s.setModule('courriers')
                    }}
                      className="flex-1 rounded-md border border-mint/40 py-1.5 text-center text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">✉ Courrier ({etat?.counts?.retenue ?? 0})</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {drawerOpen && projet && (
          <FiltreDrawer cadrageProjet={projet.cadrage} initial={sousFiltre}
            onApply={(sf) => { setSousFiltre(Object.keys(sf).length ? sf : null); setDrawerOpen(false) }}
            onClear={() => { setSousFiltre(null); setDrawerOpen(false) }}
            onClose={() => setDrawerOpen(false)} />
        )}
      </div>

      {algoModale === 'classement' && <AlgoExplainer onClose={() => setAlgoModale(null)} />}
      {algoModale === 'scoring' && <ScoringExplainer onClose={() => setAlgoModale(null)} />}
    </div>
  )
}

/** Les 3 colonnes — source de vérité : les statuts `projet_parcelles`. */
const COLS: { key: StatutParcelle; label: string; accent: string }[] = [
  { key: 'proposee', label: 'À trier', accent: TOKENS.stNone },
  { key: 'retenue', label: 'Retenues', accent: TOKENS.mint },
  { key: 'ecartee', label: 'Écartées', accent: '#4a4a4a' },
]
