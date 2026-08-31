import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getParcoursEtat, getProjet, patchProjet, projetPdfUrl, setStatutParcelle,
  type Cadrage, type ParcoursEtat, type ParcoursItem,
  type StatutParcelle,
} from '../../lib/api'
import { AlgoExplainer, ScoringExplainer } from '../panel/LeftPanel'
import { FiltreFacettes } from '../panel/FiltreFacettes'
import { FiltreProvider } from '../panel/filtreContext'
import { fmtDate, fmtEurCompact, fmtInt, fmtM2, iduCourt } from '../../lib/format'
import { etatBienMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Loading } from '../Loading'
import { Tip } from '../Tip'

/** PROJETS-FIX F2 (maquette §03) — le PÉRIMÈTRE, en étiquette de titre (une seule fois). */
function perimetreLabel(c: Cadrage): string {
  const cs = c.communes ?? []
  return !cs.length ? "toute l'île" : cs.length === 1 ? cs[0] : `${cs.length} communes`
}

/** Les 3 colonnes du projet unifié — UNE seule source de vérité : les statuts `projet_parcelles`.
 *  Accents = tokens de statut (à trier reste NEUTRE : la couleur est pour les décisions). */
const COLS: { key: StatutParcelle; label: string; accent: string }[] = [
  { key: 'proposee', label: 'À trier', accent: TOKENS.stNone },
  { key: 'retenue', label: 'Retenues', accent: TOKENS.stChaude },
  { key: 'ecartee', label: 'Écartées', accent: TOKENS.stEcartee },
]
const APERCU = 3   // cartes visibles par colonne avant « + N autres »

/** retire l'item de son groupe et le pousse dans le groupe cible — maj optimiste (identique au Tinder). */
function moveItem(etat: ParcoursEtat, idu: string, statut: StatutParcelle): ParcoursEtat {
  // colonne d'origine (avant déplacement) — calculée AVANT le strip pour rester bien typée
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
  // M140 Lot A — counts par DELTA : `proposee` est le TOTAL serveur (liste complète VIVE), jamais
  // recompté depuis une fenêtre paginée (.length ≠ N). On décale seulement source → cible.
  const counts = { ...etat.counts }
  if (moved && from && from !== statut) {
    counts[from] = Math.max(0, (counts[from] ?? 0) - 1)
    counts[statut] = (counts[statut] ?? 0) + 1
  }
  return { ...etat, proposees, retenues, ecartees, a_analyser, counts }
}

/** VUE PROJET UNIFIÉE (PJ3) — kanban 3 colonnes (À trier / Retenues / Écartées) branché sur les
 *  statuts `projet_parcelles`. « Ouvrir » un projet mène ICI. Drag & drop natif (pattern CRM) ET
 *  boutons de repli (accessibilité/mobile) appellent la MÊME mutation de statut que le Tinder. */
export function ProjetKanban({ pid, nom }: { pid: number; nom: string }) {
  const qc = useQueryClient()
  const { setOpenProjet, select, algoModale, setAlgoModale } = useApp()
  const [drag, setDrag] = useState<{ idu: string; from: StatutParcelle } | null>(null)
  const [overCol, setOverCol] = useState<StatutParcelle | null>(null)
  const [expandCol, setExpandCol] = useState<StatutParcelle | null>(null)
  const [editing, setEditing] = useState(false)
  const [nomInput, setNomInput] = useState(nom)
  const [filtreAnalyse, setFiltreAnalyse] = useState(false)   // M2 : filtre rapide « à analyser » (colonne proposées)
  const [propLimit, setPropLimit] = useState(60)   // M140 Lot A : fenêtre des proposées (feuilleter la liste complète)
  const [navTier, setNavTier] = useState<string | null>(null)   // OUTILS-5 (P1) : filtre de navigation « classement »

  const projetQ = useQuery({ queryKey: ['projet', pid], queryFn: () => getProjet(pid), enabled: pid > 0 })
  // M140 Lot A — la fenêtre des proposées grandit à la demande (« Charger plus ») : on ne charge
  // JAMAIS tout. `placeholderData` garde la fenêtre précédente affichée pendant l'agrandissement.
  const parcoursKey = ['parcours', pid, propLimit, navTier]
  const etatQ = useQuery({ queryKey: parcoursKey, queryFn: () => getParcoursEtat(pid, 0, propLimit, navTier),
    enabled: pid > 0, placeholderData: (prev) => prev })

  // OUTILS-5 (P1) — le projet est un INSTANTANÉ daté : plus de run à l'ouverture, plus de « Rejouer ».
  // On lit l'état (vivier vif paginé + décidées), on ne relance rien.

  // LE geste de statut — UNE seule logique (drag, boutons, Tinder l'appellent tous). Optimiste +
  // resync CRM (retenue↔pipeline) + compteurs des fiches.
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
      qc.invalidateQueries({ queryKey: ['pipeline'] })   // auto-CRM (Phase 2)
      qc.invalidateQueries({ queryKey: ['projets'] })     // mini-compteurs des fiches
    },
  })
  const patch = useMutation({
    mutationFn: (body: { nom?: string; statut?: string }) => patchProjet(pid, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['projet', pid] }); qc.invalidateQueries({ queryKey: ['projets'] }) },
  })

  const etat = etatQ.data
  const projet = projetQ.data
  // PROJETS-FIX F4 — les DEUX états vides à distinguer : un projet « de zéro » (aucun cadrage, on ajoute
  // depuis les fiches) vs un projet vivier dont le cadrage ne rend RIEN (cas légitime, ex. zone absente).
  const [editCadrage, setEditCadrage] = useState(false)
  const deZero = Boolean((projet?.cadrage as Record<string, unknown> | undefined)?.__de_zero__)
  const vivierVide = etat != null && (etat.total_retenues ?? 0) === 0 && !deZero
  // PROJETS-V4 (V5) — « + Ajouter des parcelles » OUVRE SIMPLEMENT LA CARTE, sans verrouiller aucun état
  // (le mode collant `projetCible` est supprimé). On y ajoute depuis le bouton « Projet » d'une fiche, qui
  // liste TOUS les projets à chaque fois.
  const ouvrirCarte = () => { const s = useApp.getState(); s.setOpenProjet(null); s.setView('cartes') }
  const items = (k: StatutParcelle): ParcoursItem[] =>
    k === 'proposee' ? etat?.proposees ?? [] : k === 'retenue' ? etat?.retenues ?? [] : etat?.ecartees ?? []
  const count = (k: StatutParcelle) => etat?.counts?.[k] ?? 0

  const onDrop = (target: StatutParcelle) => {
    if (drag && drag.from !== target) decide.mutate({ idu: drag.idu, statut: target })
    setDrag(null); setOverCol(null)
  }

  return (
    <div data-projet-kanban className="flex min-w-0 flex-1 flex-col overflow-hidden bg-bg">
      {/* HEADER : nom + critères + rejoué + actions */}
      <div className="shrink-0 border-b border-line-2 px-4 pt-5 pb-3 sm:px-6">
        <button onClick={() => setOpenProjet(null)}
          className="min-h-7 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi"
          title="Revenir à la liste des projets">← Mes projets</button>
        <div className="mt-1.5 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {editing ? (
              <input data-kanban-nom-input autoFocus value={nomInput}
                onChange={(e) => setNomInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && nomInput.trim()) { patch.mutate({ nom: nomInput.trim() }); setEditing(false) }
                  if (e.key === 'Escape') { setNomInput(nom); setEditing(false) }
                }}
                onBlur={() => { if (nomInput.trim() && nomInput !== nom) patch.mutate({ nom: nomInput.trim() }); setEditing(false) }}
                className="rounded-md border border-mint/40 bg-surface-3 px-2 py-1 font-display text-lg font-bold text-txt-hi outline-none focus:border-mint" />
            ) : (
              <div className="flex items-baseline gap-2.5">
                <h1 data-kanban-nom className="truncate font-display text-lg font-bold text-txt-hi" title={projet?.nom ?? nom}>{projet?.nom ?? nom}</h1>
                {/* PROJETS-FIX F2 (maquette §03) — le périmètre, en étiquette, UNE fois. */}
                {projet && <span data-kanban-perimetre className="shrink-0 font-mono text-[11px] uppercase tracking-wider text-txt-dim">{perimetreLabel(projet.cadrage)}</span>}
              </div>
            )}
            {/* PROJETS-FIX F2 — la ligne vivier · valeurs · budget (une seule ligne, comme la maquette).
                « pourquoi ? » ouvre LE composant d'explication de l'analyse LABUSE (jamais une prose parallèle). */}
            <div data-kanban-meta className="mt-1.5 text-[11.5px] leading-relaxed text-txt-mut">
              {/* un projet « de zéro » n'a pas de vivier : on n'affiche pas un « Vivier : 0 » qui n'a pas de sens. */}
              {!deZero && etatQ.data?.total_retenues != null && (
                <span data-kanban-vivier><b className="text-txt-2">Vivier : {etatQ.data.total_retenues.toLocaleString('fr-FR')} parcelles, classées par probabilité de mutation</b>
                  {' '}<button data-kanban-pourquoi onClick={() => useApp.getState().setAlgoModale('scoring')} className="text-mint hover:underline">pourquoi ?</button></span>
              )}
              {etatQ.data?.valeurs_run?.date && (
                <span data-kanban-valeurs-date title="Les valeurs (SDP, zone) sont lues sur le run résiduel servi ; elles peuvent évoluer si le run bascule."> · valeurs au {fmtDate(etatQ.data.valeurs_run.date)} (run {etatQ.data.valeurs_run.label})</span>
              )}
              {projet?.identite?.budget_eur ? <span data-kanban-budget> · budget {fmtEurCompact(projet.identite.budget_eur)} <span className="text-txt-dim">indic.</span></span> : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {/* OUTILS-5 (P4) — RETIRÉS : « Rejouer » (le projet est un instantané daté, assumé — qui veut
                du frais crée un projet) et « CSV complet » (même politique que Densifier/Scan :
                consultation illimitée, extraction non ; le PDF reste). */}
            <a data-kanban-pdf href={projetPdfUrl(pid)} target="_blank" rel="noreferrer"
              className="min-h-7 rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt transition-colors duration-quick hover:border-mint hover:text-txt-hi"
              title="Dossier PDF — extrait figé de présentation">PDF</a>
            <button data-kanban-renommer onClick={() => { setNomInput(projet?.nom ?? nom); setEditing(true) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Renommer</button>
            <button data-kanban-archiver onClick={() => { patch.mutate({ statut: 'archive' }); setOpenProjet(null) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Archiver</button>
            {/* PROJETS-V4 (V3/V5) — « + Ajouter des parcelles » vit dans l'en-tête (à côté de PDF), plus
                seulement dans l'état vide. Il ouvre la carte, sans verrouiller (fin du mode collant). */}
            <button data-kanban-ajouter-header onClick={ouvrirCarte}
              className="min-h-7 rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/25">+ Ajouter des parcelles</button>
          </div>
        </div>
        {/* PROJETS-V4 (V3) — la phrase « Une parcelle en tête ailleurs ? … » est RETIRÉE : le bouton
            « + Ajouter des parcelles » de l'en-tête la remplace. L'en-tête tient sur deux lignes. */}
      </div>

      {/* 3 COLONNES — PROJETS-V4 (V2) : grille pleine largeur À trier 2,2 / Retenues 1 / Écartées 1.
          À trier a besoin de place (lignes compactes) ; Retenues/Écartées servent des mini-lignes. */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-hidden p-4 md:grid-cols-[2.2fr_1fr_1fr] sm:p-6">
        {etatQ.isLoading && <Loading label="Chargement du projet…" className="col-span-full mx-auto self-center" />}
        {COLS.map((col) => {
          const aAnalyser = etat?.a_analyser ?? []
          // M2 — HYBRIDE : « proposées » = file de travail (liste dense triée par rang) où « à analyser »
          // remonte EN TÊTE (badge) ; « retenues/écartées » = cartes visuelles (décisions du client).
          const isProp = col.key === 'proposee'
          const base = isProp ? [...aAnalyser, ...(etat?.proposees ?? [])] : items(col.key)
          const list = isProp && filtreAnalyse ? aAnalyser : base
          const apercu = isProp || expandCol === col.key ? list : list.slice(0, APERCU)
          const reste = list.length - apercu.length
          return (
            <div key={col.key} data-kanban-col={col.key}
              onDragOver={(e) => { e.preventDefault(); setOverCol(col.key) }}
              onDragLeave={() => setOverCol((o) => (o === col.key ? null : o))}
              onDrop={(e) => { e.preventDefault(); onDrop(col.key) }}
              className={`flex min-h-0 min-w-0 flex-col rounded-xl border bg-surface-1 shadow-elev-1 transition-colors duration-quick ${overCol === col.key && drag && drag.from !== col.key ? 'border-mint ring-1 ring-mint/40' : 'border-transparent'}`}>
              {/* tête de colonne : compteur + action de tête */}
              <div className="flex shrink-0 items-center gap-2 border-b border-line-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: col.accent }} />
                <span className="text-[12px] font-medium text-txt-hi">{col.label}</span>
                <span data-kanban-count={col.key} className="font-mono text-[11px] text-txt-dim">{count(col.key)}</span>
                {/* OUTILS-5 (P1) — « À trier » sert le vivier ENTIER, par pages, les mieux classées d'abord :
                    le compteur le dit en toutes lettres. Le bouton « Trier » (parcours carte) est retiré :
                    le flux est déjà ordonné. */}
                {isProp && <span data-kanban-mieux className="text-[10px] text-txt-dim">· les mieux classées d'abord</span>}
                {isProp && aAnalyser.length > 0 && (
                  <button data-kanban-filtre-analyse onClick={() => setFiltreAnalyse((v) => !v)}
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold transition-colors duration-quick ${filtreAnalyse ? 'bg-st-creuser text-mint-ink' : 'border border-st-creuser/60 text-st-creuser'}`}
                    title="Filtrer sur les parcelles marquées « à analyser »">◑ à analyser {aAnalyser.length}</button>
                )}
                {col.key === 'retenue' && (
                  <Tip tip="Chaque retenue crée une piste CRM (contact à préparer)" className="ml-auto">
                    <span className="text-[10px] text-txt-dim">→ CRM</span>
                  </Tip>
                )}
                {col.key === 'ecartee' && (
                  <Tip tip="Écarter n'est jamais définitif : « Récupérer » repasse la parcelle à trier." className="ml-auto">
                    <span className="text-[10px] text-txt-dim">réversible</span>
                  </Tip>
                )}
              </div>
              {/* OUTILS-5 (P1) — FILTRES DE NAVIGATION du vivier « à trier » : classement (même facette
                  `tiers` que la carte, jamais un tri parallèle). On NAVIGUE le vivier, on ne le plafonne pas. */}
              {isProp && (
                <div data-kanban-nav className="flex shrink-0 flex-wrap gap-1.5 border-b border-line-2 px-3 py-2">
                  {([['', 'Tous'], ['brulante', 'Priorité'], ['chaude', 'À suivre']] as const).map(([v, l]) => (
                    <button key={v || 'tous'} data-kanban-nav-tier={v || 'tous'} onClick={() => setNavTier(v || null)}
                      className={`rounded-full border px-2.5 py-0.5 text-[10.5px] transition-colors duration-quick ${(navTier ?? '') === v ? 'border-mint bg-mint/15 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>{l}</button>
                  ))}
                </div>
              )}
              {/* PROJETS-V4 (V1) — l'EN-TÊTE de colonnes en mono, au-dessus de la liste « À trier ». */}
              {isProp && !filtreAnalyse && (etat?.proposees?.length ?? 0) > 0 && (
                <div data-kanban-lhead className="grid shrink-0 grid-cols-[16px_1fr_96px_74px_150px_68px] gap-3 border-b border-line-2 px-3 py-1.5 font-mono text-[9.5px] uppercase tracking-[0.14em] text-txt-dim">
                  <span></span><span>Parcelle</span><span>Signal</span><span className="text-right">Surface</span><span className="text-right">Marché commune</span><span className="text-right">Trier</span>
                </div>
              )}
              <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
                {/* PROJETS-FIX F4 — jamais un « 0 » nu : projet de zéro → ajouter ; cadrage sans résultat → modifier. */}
                {list.length === 0 && isProp && !filtreAnalyse && editCadrage && (
                  <div className="m-2.5"><CadrageEditor pid={pid} cadrage={projet?.cadrage ?? {}} onDone={() => setEditCadrage(false)} /></div>
                )}
                {list.length === 0 && isProp && !filtreAnalyse && !editCadrage && deZero && (
                  <div data-empty-de-zero className="m-2.5 rounded-lg border border-mint/25 bg-mint/[.06] p-4 text-center">
                    <p className="text-[12px] text-txt-2">Projet de zéro — aucune parcelle pour l’instant.</p>
                    <p className="mt-1 text-[11px] text-txt-mut">Choisissez vos cibles depuis la carte : le bouton « Projet » d’une fiche liste tous vos projets et les ajoute à celui que vous choisissez.</p>
                    <button data-empty-ajouter onClick={ouvrirCarte}
                      className="mt-3 rounded-md border border-mint/60 px-3 py-1.5 text-[11.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15">Ajouter des parcelles → carte</button>
                  </div>
                )}
                {list.length === 0 && isProp && !filtreAnalyse && !editCadrage && vivierVide && (
                  <div data-empty-cadrage-vide className="m-2.5 rounded-lg border border-line-2 bg-surface-2/60 p-4 text-center">
                    <p className="text-[12px] text-txt-2">Aucune parcelle ne correspond à ce cadrage.</p>
                    <p className="mt-1 text-[11px] text-txt-mut">Le cadrage est peut-être trop resserré (ou porte une zone absente du périmètre).</p>
                    <button data-empty-modifier onClick={() => setEditCadrage(true)}
                      className="mt-2 text-[11.5px] text-mint transition-colors duration-quick hover:underline">Modifier le cadrage</button>
                  </div>
                )}
                {list.length === 0 && !(isProp && !filtreAnalyse && !editCadrage && (deZero || vivierVide)) && !(isProp && editCadrage) && (
                  <div className="m-2.5 rounded-lg bg-surface-2/60 py-6 text-center text-[11px] text-txt-dim">
                    {isProp ? (filtreAnalyse ? 'Rien à analyser' : 'Rien à trier pour l’instant') : col.key === 'retenue' ? 'Aucune retenue' : 'Aucune écartée'}
                  </div>
                )}
                {/* PROJETS-V4 (V1/V2) — « À trier » = LIGNES compactes (gestes ✓/✕) ; Retenues/Écartées = MINI-LIGNES. */}
                {apercu.map((it) => (isProp ? (
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
                {/* pieds : charger plus / + N autres / réduire / actions Retenues (poussés en bas) */}
                <div className="mt-auto p-2.5 pt-1.5">
                  {isProp && !filtreAnalyse && etat?.page?.has_more && (
                    <button data-kanban-charger-plus disabled={etatQ.isFetching} onClick={() => setPropLimit((l) => l + 60)}
                      className="w-full rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi disabled:opacity-50"
                      title="La colonne « À trier » compte le TOTAL vif ; ici on n'en affiche que les premières (60 par palier) — cliquez pour en charger plus.">
                      {etatQ.isFetching ? 'Chargement…'
                        : `Charger plus  ·  les ${etat?.proposees?.length ?? 0} premières sur ${etat?.total_retenues ?? '…'}`}
                    </button>
                  )}
                  {!isProp && reste > 0 && (
                    <button data-kanban-plus={col.key} onClick={() => setExpandCol(col.key)}
                      className="w-full rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">
                      + {reste} autre{reste > 1 ? 's' : ''}
                    </button>
                  )}
                  {!isProp && expandCol === col.key && list.length > APERCU && (
                    <button onClick={() => setExpandCol(null)}
                      className="mt-1 min-h-7 text-[10.5px] text-txt-dim transition-colors duration-quick hover:text-txt-mut">réduire</button>
                  )}
                  {col.key === 'retenue' && count('retenue') > 0 && (
                    <div data-kanban-retenues-actions className="mt-1 flex gap-2 border-t border-line-2 pt-2">
                      <button data-kanban-crm onClick={() => { const s = useApp.getState(); s.setOpenProjet(null); s.setView('crm') }}
                        className="flex-1 rounded-md border border-mint/40 py-1.5 text-center text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">→ CRM</button>
                      <button data-kanban-courrier onClick={() => {
                        const idus = (etat?.retenues ?? []).map((r) => r.idu)
                        const s = useApp.getState(); s.setCourrierPrefillIdus(idus); s.setOpenProjet(null); s.setView('cartes'); s.setModule('courriers')
                      }}
                        className="flex-1 rounded-md border border-mint/40 py-1.5 text-center text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">✉ Courrier ({count('retenue')})</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      {/* OUTILS-5 (P2) — « pourquoi ? » ouvre LE MÊME composant d'explication que la carte/fiche
          (AlgoExplainer/ScoringExplainer, pilotés par le store `algoModale`) — une seule explication,
          servie partout ; jamais une prose parallèle pour Projets. */}
      {algoModale === 'classement' && <AlgoExplainer onClose={() => setAlgoModale(null)} />}
      {algoModale === 'scoring' && <ScoringExplainer onClose={() => setAlgoModale(null)} />}
    </div>
  )
}

/** PROJETS-FIX F4 — éditeur de cadrage inline (état vide « aucune parcelle ne correspond »). Réutilise
 *  EXACTEMENT les facettes du wizard (FiltreFacettes) branchées sur le cadrage courant du projet ; le
 *  périmètre (communes) est conservé et passé au compteur (`compteurScope`). Enregistrer patche le
 *  cadrage (le back marque la shortlist périmée) et rafraîchit la vue — jamais un moteur parallèle. */
function CadrageEditor({ pid, cadrage, onDone }: { pid: number; cadrage: Cadrage; onDone: () => void }) {
  const qc = useQueryClient()
  const communes = cadrage.communes ?? []
  const [facettes, setFacettes] = useState<Filters>(() => ({ ...EMPTY_FILTERS, ...cadrage }))
  const binding = { filters: facettes, setFilter: <K extends keyof Filters>(k: K, v: Filters[K]) => setFacettes((c) => ({ ...c, [k]: v })) }
  const cadrageOut = (): Cadrage => {
    const out: Cadrage = {}
    for (const [k, v] of Object.entries(facettes) as [keyof Filters, unknown][]) {
      const empty = v === null || v === false || (Array.isArray(v) && v.length === 0)
      if (!empty && k !== 'analyseLabuse') (out as Record<string, unknown>)[k] = v
    }
    if (communes.length) out.communes = communes
    return out
  }
  const save = useMutation({
    mutationFn: () => patchProjet(pid, { cadrage: cadrageOut() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projet', pid] })
      qc.invalidateQueries({ queryKey: ['parcours', pid] })
      qc.invalidateQueries({ queryKey: ['projets'] })
      onDone()
    },
  })
  return (
    <div data-cadrage-editor className="rounded-lg border border-line-2 bg-surface-2/50 p-3">
      <p className="mb-2 text-[11px] text-txt-mut">Périmètre : <b className="text-txt-2">{communes.length ? communes.join(', ') : "toute l'île"}</b></p>
      <FiltreProvider value={binding}><FiltreFacettes compteurScope={{ communes }} /></FiltreProvider>
      <div className="mt-3 flex items-center gap-2">
        <button data-cadrage-save disabled={save.isPending} onClick={() => save.mutate()}
          className="rounded-md border border-mint/60 px-3 py-1.5 text-[11.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15 disabled:opacity-50">{save.isPending ? 'Enregistrement…' : 'Enregistrer le cadrage'}</button>
        <button data-cadrage-annuler onClick={onDone} className="text-[11px] text-txt-dim hover:text-txt-mut">Annuler</button>
      </div>
    </div>
  )
}

/** PROJETS-V4 (V1) — la pastille de tier : Priorité (rouge) · À suivre (orange) · autres (gris). */
const TIER_DOT: Record<string, string> = { brulante: TOKENS.stEcartee, chaude: TOKENS.stCreuser }
function tierDot(tier: string | null): string { return (tier && TIER_DOT[tier]) || '#555' }

/** PROJETS-V4 (V1) — LA LIGNE remplace la carte dans « À trier » : ~42 px, grille alignée (pastille ·
 *  adresse [IDU + nu/bâti en sous-ligne mono] · signal · surface → · marché commune → · deux gestes ✓/✕
 *  de 26 px). Survol = fond éclairci. Clic = fiche ; glisser = décider (même mutation que les gestes). */
function LigneParcelle({ it, onDragStart, onRetenir, onEcarter, onFiche }: {
  it: ParcoursItem; onDragStart: () => void; onRetenir: () => void; onEcarter: () => void; onFiche: () => void
}) {
  const titre = it.adresse || it.commune
  const eb = etatBienMeta(it.etat_bien)
  const nb = eb?.short ?? (it.etat_bien === 'nu' ? 'Nu' : '')
  return (
    <div draggable onDragStart={onDragStart} data-tri-ligne={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className="grid cursor-pointer grid-cols-[16px_1fr_96px_74px_150px_68px] items-center gap-3 border-b border-line/50 px-3 py-2 transition-colors duration-quick hover:bg-surface-2"
      title="Ouvrir la fiche · glisser pour décider">
      <span className="h-[7px] w-[7px] rounded-full" style={{ background: tierDot(it.tier) }} />
      <div className="min-w-0">
        <b className="block truncate text-[13px] font-medium text-txt-hi">{titre}</b>
        <span className="block truncate font-mono text-[10.5px] text-txt-dim">{iduCourt(it.idu)}{nb ? ` · ${nb}` : ''}</span>
      </div>
      <span className="truncate text-[11px] text-txt-mut" title={it.raison ?? undefined}>{it.raison ?? ''}</span>
      <span className="text-right font-mono text-[11.5px] text-txt-mut">{it.surface_m2 != null ? fmtM2(it.surface_m2) : '—'}</span>
      <span className="text-right text-[11.5px] text-txt-dim">{it.marche_eur_m2 != null ? `~${fmtInt(it.marche_eur_m2)} €/m²` : '—'}</span>
      <div className="flex justify-end gap-1.5">
        <button data-tri-retenir onClick={onRetenir} title="Retenir"
          className="flex h-6 w-[26px] items-center justify-center rounded-md border border-mint/40 text-[12px] text-mint transition-colors duration-quick hover:bg-mint/15">✓</button>
        <button data-tri-ecarter onClick={onEcarter} title="Écarter"
          className="flex h-6 w-[26px] items-center justify-center rounded-md border border-st-ecartee/40 text-[12px] text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10">✕</button>
      </div>
    </div>
  )
}

/** PROJETS-V4 (V2) — la MINI-LIGNE des colonnes étroites (Retenues / Écartées) : pastille, adresse
 *  tronquée, bouton retour (↩ → à trier). Pas une carte. Écartées en retrait (opacité). */
function MiniLigne({ it, col, onDragStart, onRetour, onFiche }: {
  it: ParcoursItem; col: StatutParcelle; onDragStart: () => void; onRetour: () => void; onFiche: () => void
}) {
  const titre = it.adresse || it.commune
  const ecartee = col === 'ecartee'
  return (
    <div draggable onDragStart={onDragStart} data-mini-ligne={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className={`flex cursor-pointer items-center gap-2 border-b border-line/50 px-3 py-2 transition-colors duration-quick hover:bg-surface-2 ${ecartee ? 'opacity-60' : ''}`}
      title="Ouvrir la fiche">
      <span className="h-[7px] w-[7px] shrink-0 rounded-full" style={{ background: tierDot(it.tier) }} />
      <b className="min-w-0 flex-1 truncate text-[12.5px] font-medium text-txt">{titre}</b>
      <button data-mini-retour onClick={onRetour}
        title={ecartee ? 'Récupérer (→ à trier)' : 'Remettre à trier'}
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-[12px] transition-colors duration-quick ${ecartee ? 'border-mint/40 text-mint hover:bg-mint/15' : 'border-line-2 text-txt-mut hover:border-mint hover:text-mint'}`}>↩</button>
    </div>
  )
}
