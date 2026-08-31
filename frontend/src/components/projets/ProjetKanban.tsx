import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getParcoursEtat, getProjet, patchProjet, projetPdfUrl, setStatutParcelle,
  type Cadrage, type ParcoursEtat, type ParcoursItem, type ProprietairePublic,
  type StatutParcelle,
} from '../../lib/api'
import { AlgoExplainer, ScoringExplainer } from '../panel/LeftPanel'
import { FiltreFacettes } from '../panel/FiltreFacettes'
import { FiltreProvider } from '../panel/filtreContext'
import { fmtDate, fmtEurCompact, fmtInt, fmtM2, iduComplet, iduCourt } from '../../lib/format'
import { CLIENT } from '../../lib/strings'
import { etatBienMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Loading } from '../Loading'
import { TierBadge } from '../outils/TierBadge'
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

/** Contact proprio — PRIVACY : personne morale nommée (public) ; particulier JAMAIS nommé. */
function ProprioLine({ p }: { p?: ProprietairePublic | null }) {
  if (!p) return null
  if (p.type === 'personne_morale') return (
    <div className="truncate text-[10px] text-txt-mut" title={`Personne morale (registre public DGFiP) · SIREN ${p.siren ?? '—'}`}>
      <span className="text-txt">{p.denomination}</span>{p.siren ? <span className="text-txt-dim"> · SIREN {p.siren}</span> : null}
    </div>
  )
  return <div className="truncate text-[10px] italic text-txt-dim" title="Propriétaire personne physique — jamais nommé (privacy)">Propriétaire particulier — non communiqué</div>
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
  const ajouterDepuisCarte = () => {
    const s = useApp.getState()
    s.setProjetCible({ id: pid, nom: projet?.nom ?? nom })   // la fiche « Projet » rattachera DIRECTEMENT ici
    s.setView('cartes')
  }
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
          </div>
        </div>
        {/* OUTILS-5 (P1) — bandeau « cadrage modifié / rejeu » RETIRÉ avec le bouton Rejouer : le projet
            est un instantané daté, jamais rejoué en place (« valeurs au JJ/MM » l'assume). */}
        <p data-kanban-ajouter className="mt-1.5 text-[10.5px] text-txt-dim">{CLIENT.projet.ajouterDepuisFiche}</p>
      </div>

      {/* 3 COLONNES — PROJETS-FIX F2 (maquette §03) : GRILLE pleine largeur (À trier 1.35 / Retenues 1 /
          Écartées 0.8) qui remplit tout l'espace alloué — fini les colonnes à largeur fixe qui laissaient
          un grand vide. Sous 980px, on empile (une colonne). */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-hidden p-4 md:grid-cols-[1.35fr_1fr_0.8fr] sm:p-6">
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
              <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2.5">
                {/* PROJETS-FIX F4 — jamais un « 0 » nu : selon le cas, on invite à ajouter (projet de
                    zéro) ou à modifier un cadrage sans résultat (cas légitime). */}
                {list.length === 0 && isProp && !filtreAnalyse && editCadrage && (
                  <CadrageEditor pid={pid} cadrage={projet?.cadrage ?? {}} onDone={() => setEditCadrage(false)} />
                )}
                {list.length === 0 && isProp && !filtreAnalyse && !editCadrage && deZero && (
                  <div data-empty-de-zero className="rounded-lg border border-mint/25 bg-mint/[.06] p-4 text-center">
                    <p className="text-[12px] text-txt-2">Projet de zéro — aucune parcelle pour l’instant.</p>
                    <p className="mt-1 text-[11px] text-txt-mut">Choisissez vos cibles depuis la carte : le bouton « Projet » d’une fiche les rattachera directement ici.</p>
                    <button data-empty-ajouter onClick={ajouterDepuisCarte}
                      className="mt-3 rounded-md border border-mint/60 px-3 py-1.5 text-[11.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15">Ajouter des parcelles → carte</button>
                  </div>
                )}
                {list.length === 0 && isProp && !filtreAnalyse && !editCadrage && vivierVide && (
                  <div data-empty-cadrage-vide className="rounded-lg border border-line-2 bg-surface-2/60 p-4 text-center">
                    <p className="text-[12px] text-txt-2">Aucune parcelle ne correspond à ce cadrage.</p>
                    <p className="mt-1 text-[11px] text-txt-mut">Le cadrage est peut-être trop resserré (ou porte une zone absente du périmètre).</p>
                    <button data-empty-modifier onClick={() => setEditCadrage(true)}
                      className="mt-2 text-[11.5px] text-mint transition-colors duration-quick hover:underline">Modifier le cadrage</button>
                  </div>
                )}
                {list.length === 0 && !(isProp && !filtreAnalyse && !editCadrage && (deZero || vivierVide)) && !(isProp && editCadrage) && (
                  <div className="rounded-lg bg-surface-2/60 py-6 text-center text-[11px] text-txt-dim">
                    {isProp ? (filtreAnalyse ? 'Rien à analyser' : 'Rien à trier pour l’instant') : col.key === 'retenue' ? 'Aucune retenue' : 'Aucune écartée'}
                  </div>
                )}
                {/* M120 · Phase 4 — MÊME anatomie de carte, DEUX densités : « À trier » garde tout
                    (pourquoi + signaux, c'est là qu'on décide) ; Retenues/Écartées s'allègent. */}
                {apercu.map((it) => (
                  <TriCard key={it.idu} it={it} col={col.key} dense={isProp}
                    onDragStart={() => setDrag({ idu: it.idu, from: isProp ? 'proposee' : col.key })}
                    onAction={(statut) => decide.mutate({ idu: it.idu, statut })}
                    onFiche={() => select(it.idu)} />
                ))}
                {/* FIX-PROJETS (P2) — le compteur de colonne (en-tête) = TOTAL VIF ; ce pied est un CAP
                    d'AFFICHAGE explicite (« les N premières sur M »), jamais un compteur. « Charger plus »
                    agrandit la fenêtre serveur (offset/limit) de 60, jamais tout chargé. */}
                {isProp && !filtreAnalyse && etat?.page?.has_more && (
                  <button data-kanban-charger-plus disabled={etatQ.isFetching}
                    onClick={() => setPropLimit((l) => l + 60)}
                    className="rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi disabled:opacity-50"
                    title="La colonne « À trier » compte le TOTAL vif ; ici on n'en affiche que les premières (60 par palier) — cliquez pour en charger plus.">
                    {etatQ.isFetching ? 'Chargement…'
                      : `Charger plus  ·  les ${etat?.proposees?.length ?? 0} premières sur ${etat?.total_retenues ?? '…'}`}
                  </button>
                )}
                {!isProp && reste > 0 && (
                  <button data-kanban-plus={col.key} onClick={() => setExpandCol(col.key)}
                    className="rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt-hi">
                    + {reste} autre{reste > 1 ? 's' : ''}
                  </button>
                )}
                {!isProp && expandCol === col.key && list.length > APERCU && (
                  <button onClick={() => setExpandCol(null)}
                    className="min-h-7 text-[10.5px] text-txt-dim transition-colors duration-quick hover:text-txt-mut">réduire</button>
                )}
                {/* OUTILS-5 (P4) — colonne Retenues : « → CRM » + « ✉ Courrier (N) » (ouvre l'outil
                    Courrier propriétaire pré-rempli des retenues, étape 1 remplie). */}
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

/** M2 — badges parcelle (défisc / PC caduc / hors critères). */
function Badges({ it }: { it: ParcoursItem }) {
  if (!it.hors_criteres && !it.defisc && !it.caduc) return null
  return (
    <span className="inline-flex flex-wrap gap-1 align-middle">
      {it.hors_criteres && (
        <Tip tip="Décidée avant, hors des critères actuels — conservée (jamais évincée)">
          <span data-badge-hors className="rounded-full border border-st-creuser px-1.5 text-[8.5px] font-semibold text-st-creuser">hors critères actuels</span>
        </Tip>
      )}
      {it.defisc && <span className="rounded-full border border-violet px-1.5 text-[8.5px] font-semibold text-violet">défisc</span>}
      {it.caduc && <span className="rounded-full border border-st-creuser px-1.5 text-[8.5px] font-semibold text-st-creuser">PC caduc</span>}
    </span>
  )
}

/** M120 · Phase 4 — LA CARTE DE TRI, une SEULE anatomie, DEUX densités (patron liste M114) :
 *  · dense (« À trier ») garde TOUT — adresse, tier, le POURQUOI (forces sourcées), le signal
 *    marché/événement, et les DEUX gestes (✓ Retenir · ✕ Écarter — OUTILS-5 : « Peut-être » retiré) ;
 *  · light (Retenues/Écartées) s'allège — adresse, IDU, tier, l'action de retour. Le pourquoi et le
 *    signal marché n'y servent plus (la décision est prise). Le q_score interne n'est PLUS servi. */
function TriCard({ it, col, dense, onDragStart, onAction, onFiche }: {
  it: ParcoursItem; col: StatutParcelle; dense: boolean
  onDragStart: () => void; onAction: (s: StatutParcelle) => void; onFiche: () => void
}) {
  const analyse = it.statut === 'a_analyser'
  const titre = it.adresse || it.commune
  return (
    <div draggable onDragStart={onDragStart} data-tri-card={it.idu} data-tri-dense={dense ? '1' : '0'}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className={`group cursor-pointer rounded-lg border p-2.5 transition-colors duration-quick active:cursor-grabbing hover:border-mint/30 ${analyse ? 'border-st-creuser/50 bg-st-creuser/5' : 'border-line-2 bg-surface-3'}`}
      title="Ouvrir la fiche · glisser pour décider">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            {analyse && <span className="text-[10px] text-st-creuser" title="à analyser">◑</span>}
            <span className="truncate text-[12px] text-txt-hi">{titre}</span>
          </div>
          <span title={iduComplet(it.idu)} className="font-mono text-[9.5px] text-txt-dim">{it.adresse ? iduCourt(it.idu) : iduComplet(it.idu)}</span>
        </div>
        <TierBadge tier={it.tier} etage0={null} statut={null} />
      </div>
      <div className="tnum mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 truncate text-[10.5px] text-txt-mut">
        <span>{it.commune}{it.surface_m2 != null ? ` · ${fmtM2(it.surface_m2)}` : ''}</span>
        {/* M131 P3 — badge d'état du bien (affichage pur du fait M125/M129-D) */}
        {etatBienMeta(it.etat_bien) && (
          <span data-etat-bien={it.etat_bien} title={etatBienMeta(it.etat_bien)!.label}
            className="rounded-full border px-1.5 py-0.5 text-[9px] font-medium"
            style={{ borderColor: `${etatBienMeta(it.etat_bien)!.color}55`, color: etatBienMeta(it.etat_bien)!.color }}>
            {etatBienMeta(it.etat_bien)!.short}
          </span>
        )}
        <Badges it={it} />
        {/* OUTILS-5 (P1) — le SIGNAL qui a classé la parcelle (« succession », « permis jamais lancé »…),
            servi par le même moteur que la carte (raison dominante des contributions du score). */}
        {it.raison && <span data-card-signal className="rounded-full bg-mint/10 px-1.5 py-0.5 text-[9px] font-medium text-mint">{it.raison}</span>}
      </div>

      {/* dense uniquement — le POURQUOI (sourcé) + le signal marché/événement */}
      {dense && it.pourquoi && it.pourquoi.length > 0 && (
        <div className="mt-1.5 flex flex-col gap-0.5">
          {it.pourquoi.map((l, i) => (
            <p key={i} className="flex gap-1.5 text-[10.5px] leading-snug text-txt-2"><span className="shrink-0 text-mint">▲</span>{l}</p>
          ))}
        </div>
      )}
      {dense && (it.marche_eur_m2 != null || it.evenement) && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {it.marche_eur_m2 != null && (
            <span className="rounded-full border border-line-2 px-2 py-0.5 text-[9.5px] text-txt-mut" title="Prix médian DVF du bâti ANCIEN de la commune (€/m² habitable) — repère de revente à l'échelle commune. À NE PAS confondre avec le « prix de sortie neuf » de secteur (fiche/Étudier). Pas une estimation par parcelle.">marché ancien commune ~{fmtInt(it.marche_eur_m2)} €/m²</span>
          )}
          {it.evenement && <span className="rounded-full border border-st-ecartee/50 px-2 py-0.5 text-[9.5px] text-st-ecartee" title="Événement foncier rouge (run servi) — mutation probable">événement</span>}
        </div>
      )}

      {col === 'retenue' && (
        <div className="mt-1.5 border-t border-line-2/60 pt-1.5">
          <div className="text-[10px] text-mint" title="Piste créée automatiquement dans le CRM — remettre à trier l'en retire">▸ dans le CRM · contact à préparer</div>
          <ProprioLine p={it.proprietaire_public} />
        </div>
      )}

      {/* gestes — dense : 3 décisions ; light : décision inverse + retour */}
      <div className="mt-2 flex gap-1.5">
        {col !== 'retenue' && (
          <button data-card-retenir onClick={() => onAction('retenue')}
            className="min-h-7 flex-1 rounded-md border border-mint/60 py-1 text-[10.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15">✓ Retenir</button>
        )}
        {/* OUTILS-5 (P4) — « ◑ Peut-être » RETIRÉ : les projets repartant de zéro, deux gestes suffisent
            (✓ Retenir / ✕ Écarter). Aucune colonne « à analyser » à alimenter. */}
        {col !== 'ecartee' && (
          <button data-card-ecarter onClick={() => onAction('ecartee')}
            className="min-h-7 flex-1 rounded-md border border-st-ecartee/50 py-1 text-[10.5px] font-medium text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10">✕ Écarter</button>
        )}
        {col !== 'proposee' && !dense && (
          <button data-card-retrier onClick={() => onAction('proposee')}
            className="min-h-7 flex-1 rounded-md border border-line-2 py-1 text-[10.5px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt"
            title={col === 'ecartee' ? 'Récupérer (repasse à trier)' : 'Remettre à trier (retire du CRM)'}>↩ {col === 'ecartee' ? 'Récupérer' : 'À trier'}</button>
        )}
      </div>
    </div>
  )
}
