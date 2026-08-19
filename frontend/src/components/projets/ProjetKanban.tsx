import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getParcoursEtat, getProjet, patchProjet, projetPdfUrl, rejouerProjet, setStatutParcelle,
  type Cadrage, type Identite, type ParcoursEtat, type ParcoursItem, type ProprietairePublic,
  type ShortlistDiff, type StatutParcelle,
} from '../../lib/api'
import { fmtDate, fmtEurCompact, fmtInt, fmtM2, iduComplet, iduCourt } from '../../lib/format'
import { CLIENT } from '../../lib/strings'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { TierBadge } from '../outils/TierBadge'
import { Tip } from '../Tip'

const TYPE_LABEL: Record<string, string> = {
  libre: 'Logement libre', social: 'Logement social', etudiant: 'Logement étudiant',
  bureaux: 'Bureaux', autre: 'Projet', logements: 'Logements',
}

/** M120 · Phase 4 — les critères qui FILTRENT (périmètre + facettes du cadrage). Ils font le tri. */
function criteresFiltrants(c: Cadrage): string[] {
  const out: string[] = []
  const cs = c.communes ?? []
  out.push(!cs.length ? "toute l'île" : cs.length === 1 ? cs[0] : `${cs.length} communes`)
  if (c.surfaceMin != null || c.surfaceMax != null) out.push(`surface ${c.surfaceMin ?? 0}–${c.surfaceMax ?? '∞'} m²`)
  if (c.zonagePlu?.length) out.push(`zonage ${c.zonagePlu.join('/')}`)
  if (c.etatSol?.length) out.push(c.etatSol.map((e) => (e === 'nu' ? 'terrain nu' : 'terrain bâti')).join(' · '))
  if (c.signaux?.length) out.push(`${c.signaux.length} signal${c.signaux.length > 1 ? 'aux' : ''} de vie`)
  return out
}

/** M120 · Phase 4 — les infos INDICATIVES (type / budget / livraison). Elles ne filtrent PAS —
 *  rendues en retrait pour ne pas les confondre avec les critères qui font le tri. */
function criteresInformatifs(id: Identite): string[] {
  const out: string[] = []
  if (id.type_logement) out.push(TYPE_LABEL[id.type_logement] ?? id.type_logement)
  if (id.budget_eur) out.push(fmtEurCompact(id.budget_eur))
  if (id.date_livraison) out.push(`livr. ${id.date_livraison}`)
  return out
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
  return { ...etat, proposees, retenues, ecartees, a_analyser,
    counts: { proposee: proposees.length, retenue: retenues.length, ecartee: ecartees.length, a_analyser: a_analyser.length } }
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
  const { setOpenProjet, openParcours, select } = useApp()
  const [drag, setDrag] = useState<{ idu: string; from: StatutParcelle } | null>(null)
  const [overCol, setOverCol] = useState<StatutParcelle | null>(null)
  const [expandCol, setExpandCol] = useState<StatutParcelle | null>(null)
  const [editing, setEditing] = useState(false)
  const [nomInput, setNomInput] = useState(nom)
  const [filtreAnalyse, setFiltreAnalyse] = useState(false)   // M2 : filtre rapide « à analyser » (colonne proposées)
  const [dernierDiff, setDernierDiff] = useState<ShortlistDiff | null>(null)   // M120 : diff du dernier rejeu

  const projetQ = useQuery({ queryKey: ['projet', pid], queryFn: () => getProjet(pid), enabled: pid > 0 })
  const etatQ = useQuery({ queryKey: ['parcours', pid], queryFn: () => getParcoursEtat(pid), enabled: pid > 0 })

  // M120 — PLUS DE RUN À L'OUVERTURE : la shortlist est FIGÉE au cadrage. On lit son état, on ne
  // relance rien. Le seul rafraîchissement est le bouton « Rejouer » explicite ci-dessous.
  const rejouer = useMutation({
    mutationFn: () => rejouerProjet(pid),
    onSuccess: (d) => {
      setDernierDiff(d.shortlist)
      qc.invalidateQueries({ queryKey: ['parcours', pid] })
      qc.invalidateQueries({ queryKey: ['projet', pid] })
      qc.invalidateQueries({ queryKey: ['projets'] })
    },
  })

  // LE geste de statut — UNE seule logique (drag, boutons, Tinder l'appellent tous). Optimiste +
  // resync CRM (retenue↔pipeline) + compteurs des fiches.
  const decide = useMutation({
    mutationFn: ({ idu, statut }: { idu: string; statut: StatutParcelle }) => setStatutParcelle(pid, idu, statut),
    onMutate: async ({ idu, statut }) => {
      await qc.cancelQueries({ queryKey: ['parcours', pid] })
      const prev = qc.getQueryData<ParcoursEtat>(['parcours', pid])
      if (prev) qc.setQueryData<ParcoursEtat>(['parcours', pid], moveItem(prev, idu, statut))
      return { prev }
    },
    onError: (_e, _v, ctx) => { if (ctx?.prev) qc.setQueryData(['parcours', pid], ctx.prev) },
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
              <h1 data-kanban-nom className="truncate font-display text-lg font-bold text-txt-hi" title={projet?.nom ?? nom}>{projet?.nom ?? nom}</h1>
            )}
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {/* critères qui FILTRENT — chips pleines */}
              {projet && criteresFiltrants(projet.cadrage).map((c, i) => (
                <span key={`f${i}`} data-crit-filtrant className="rounded-full bg-surface-3 px-2 py-0.5 text-[10.5px] text-txt-mut">{c}</span>
              ))}
              {/* infos INDICATIVES — en retrait, séparées, jamais confondues avec le tri */}
              {projet && criteresInformatifs(projet.identite).length > 0 && (
                <span className="ml-0.5 flex flex-wrap items-center gap-1.5 border-l border-line-2 pl-2">
                  <span className="text-[9px] uppercase tracking-wide text-txt-dim">indic.</span>
                  {criteresInformatifs(projet.identite).map((c, i) => (
                    <span key={`i${i}`} data-crit-indic className="rounded-full border border-line-2/60 px-2 py-0.5 text-[10px] text-txt-dim">{c}</span>
                  ))}
                </span>
              )}
              {projet?.derniere_execution_at && (
                <span data-kanban-cadrage-date className="whitespace-nowrap text-[10.5px] text-txt-dim">· cadrage du {fmtDate(projet.derniere_execution_at)}</span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <button data-kanban-rejouer disabled={rejouer.isPending} onClick={() => rejouer.mutate()}
              className={`min-h-7 rounded-md px-2.5 py-1 text-[11px] transition-colors duration-quick ${projet?.shortlist_perimee ? 'border border-mint bg-mint/15 font-semibold text-mint hover:brightness-110' : 'border border-line-2 text-txt-mut hover:border-mint hover:text-txt-hi'}`}
              title="Rejouer le cadrage sur les données du jour — vos tris sont conservés">
              {rejouer.isPending ? 'Rejeu…' : projet?.shortlist_perimee ? '↻ Rejouer (cadrage modifié)' : '↻ Rejouer'}</button>
            <a data-kanban-pdf href={projetPdfUrl(pid)} target="_blank" rel="noreferrer"
              className="min-h-7 rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt transition-colors duration-quick hover:border-mint hover:text-txt-hi">Exporter</a>
            <button data-kanban-renommer onClick={() => { setNomInput(projet?.nom ?? nom); setEditing(true) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Renommer</button>
            <button data-kanban-archiver onClick={() => { patch.mutate({ statut: 'archive' }); setOpenProjet(null) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Archiver</button>
          </div>
        </div>
        {/* M120 — bandeau « cadrage modifié » (périmée) et diff du dernier rejeu (jamais un run muet). */}
        {projet?.shortlist_perimee && !dernierDiff && (
          <p data-kanban-perimee className="mt-1.5 rounded-md bg-mint/10 px-2 py-1 text-[10.5px] text-mint">
            Le cadrage a changé — rejouez pour rafraîchir la shortlist (vos tris seront conservés).</p>
        )}
        {dernierDiff && (
          <p data-kanban-diff className="mt-1.5 text-[10.5px] text-txt-dim">
            Rejeu : <b className="text-mint">+{dernierDiff.ajoutees}</b> nouvelle{dernierDiff.ajoutees > 1 ? 's' : ''}{(dernierDiff.ajoutees_refonte ?? 0) > 0 ? ` (dont ${dernierDiff.ajoutees_refonte} entrée${(dernierDiff.ajoutees_refonte ?? 0) > 1 ? 's' : ''} par refonte cascade — nouveau vivier, pas un mouvement de marché)` : ''} · <b>{dernierDiff.sorties}</b> sortie{dernierDiff.sorties > 1 ? 's' : ''} du cadrage · {dernierDiff.tris_conserves} tri{dernierDiff.tris_conserves > 1 ? 's' : ''} conservé{dernierDiff.tris_conserves > 1 ? 's' : ''}.</p>
        )}
        <p data-kanban-ajouter className="mt-1.5 text-[10.5px] text-txt-dim">{CLIENT.projet.ajouterDepuisFiche}</p>
      </div>

      {/* 3 COLONNES */}
      <div className="flex min-h-0 flex-1 gap-4 overflow-x-auto p-4 sm:p-6">
        {etatQ.isLoading && <Loading label="Chargement du projet…" className="mx-auto self-center" />}
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
              className={`flex ${isProp ? 'w-[340px]' : 'w-[300px]'} max-w-[85vw] shrink-0 flex-col rounded-xl border bg-surface-1 shadow-elev-1 transition-colors duration-quick sm:max-w-[34vw] ${overCol === col.key && drag && drag.from !== col.key ? 'border-mint ring-1 ring-mint/40' : 'border-transparent'}`}>
              {/* tête de colonne : compteur + action de tête */}
              <div className="flex shrink-0 items-center gap-2 border-b border-line-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: col.accent }} />
                <span className="text-[12px] font-medium text-txt-hi">{col.label}</span>
                <span data-kanban-count={col.key} className="font-mono text-[11px] text-txt-dim">{count(col.key)}</span>
                {isProp && aAnalyser.length > 0 && (
                  <button data-kanban-filtre-analyse onClick={() => setFiltreAnalyse((v) => !v)}
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold transition-colors duration-quick ${filtreAnalyse ? 'bg-st-creuser text-mint-ink' : 'border border-st-creuser/60 text-st-creuser'}`}
                    title="Filtrer sur les parcelles marquées « à analyser »">◑ à analyser {aAnalyser.length}</button>
                )}
                {isProp && count('proposee') > 0 && (
                  <button data-kanban-trier onClick={() => openParcours({ id: pid, nom: projet?.nom ?? nom })}
                    className="ml-auto rounded-md bg-mint px-2.5 py-1 text-[11px] font-semibold text-mint-ink transition-[filter] duration-quick hover:brightness-110"
                    title="Parcourir les parcelles à trier une par une (carte)">Trier</button>
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
              <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2.5">
                {list.length === 0 && (
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
              </div>
            </div>
          )
        })}
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
 *    marché/événement, et les 3 gestes (✓ Retenir · ◑ Peut-être · ✕ Écarter) ;
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
      <div className="tnum mt-1 truncate text-[10.5px] text-txt-mut">
        {it.commune}{it.surface_m2 != null ? ` · ${fmtM2(it.surface_m2)}` : ''} <Badges it={it} />
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
            <span className="rounded-full border border-line-2 px-2 py-0.5 text-[9.5px] text-txt-mut" title="Prix médian DVF bâti de la COMMUNE (€/m² habitable) — repère commune, pas une estimation par parcelle">marché commune ~{fmtInt(it.marche_eur_m2)} €/m²</span>
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
        {dense && !analyse && (
          <button data-card-analyser onClick={() => onAction('a_analyser')}
            className="min-h-7 flex-1 rounded-md border border-st-creuser/50 py-1 text-[10.5px] text-st-creuser transition-colors duration-quick hover:bg-st-creuser/10">◑ Peut-être</button>
        )}
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
