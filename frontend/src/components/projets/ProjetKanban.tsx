import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  chercherPlus, getParcoursEtat, getProjet, patchProjet, projetPdfUrl, proposerProjet, setStatutParcelle,
  type FicheProjet, type ParcoursEtat, type ParcoursItem, type ProprietairePublic, type StatutParcelle,
} from '../../lib/api'
import { fmtDate, fmtEurCompact, fmtInt, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { TierBadge } from '../outils/TierBadge'
import { Tip } from '../Tip'

const TYPE_LABEL: Record<string, string> = {
  logements: 'Logements', etudiant: 'Logement étudiant', bureaux: 'Bureaux', autre: 'Projet',
}
const CONTRAINTE_LABEL: Record<string, string> = {
  eviter_ppr: 'hors PPR', eviter_pollution: 'sol sain', eviter_abf: 'hors ABF', eviter_icpe: 'hors ICPE',
}

/** Critères résumés de la fiche → chips lisibles (mêmes libellés que la liste projets). */
function criteres(f: FicheProjet): string[] {
  const out: string[] = []
  if (f.type_programme) {
    const a = f.ampleur ?? {}
    const n = a.logements ? ` ×${a.logements}` : a.sdp_m2 ? ` ${a.sdp_m2} m²` : ''
    const g = a.niveaux ? ` R+${a.niveaux}` : ''
    out.push(`${TYPE_LABEL[f.type_programme] ?? 'Projet'}${n}${g}`)
  }
  const p = f.perimetre
  out.push(!p || p.mode === 'ile' ? "toute l'île" : p.mode === 'secteur' ? `secteur ${p.secteur}`
    : (p.communes ?? []).length === 1 ? p.communes![0] : `${(p.communes ?? []).length} communes`)
  if (f.contraintes?.length) out.push(f.contraintes.map((c) => CONTRAINTE_LABEL[c] ?? c).join(' · '))
  if (f.budget_foncier_eur) out.push(fmtEurCompact(f.budget_foncier_eur))
  return out
}

/** Les 3 colonnes du projet unifié — UNE seule source de vérité : les statuts `projet_parcelles`.
 *  Accents = tokens de statut (à trier reste NEUTRE : la couleur est pour les décisions). */
const COLS: { key: StatutParcelle; label: string; accent: string }[] = [
  { key: 'proposee', label: 'À trier', accent: '#39463F' },
  { key: 'retenue', label: 'Retenues', accent: '#5CE6A1' },
  { key: 'ecartee', label: 'Écartées', accent: '#E8695A' },
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
  const proposed = useRef(false)
  const [drag, setDrag] = useState<{ idu: string; from: StatutParcelle } | null>(null)
  const [overCol, setOverCol] = useState<StatutParcelle | null>(null)
  const [expandCol, setExpandCol] = useState<StatutParcelle | null>(null)
  const [editing, setEditing] = useState(false)
  const [nomInput, setNomInput] = useState(nom)
  const [msg, setMsg] = useState('')
  const [filtreAnalyse, setFiltreAnalyse] = useState(false)   // M2 : filtre rapide « à analyser » (colonne proposées)

  const projetQ = useQuery({ queryKey: ['projet', pid], queryFn: () => getProjet(pid), enabled: pid > 0 })
  const etatQ = useQuery({ queryKey: ['parcours', pid], queryFn: () => getParcoursEtat(pid), enabled: pid > 0 })

  // à l'ouverture : (re)proposer les parcelles du jour — idempotent, NON destructif (ON CONFLICT DO
  // NOTHING). Garantit qu'« À trier » n'est jamais vide pour un projet jamais trié. Même source que le Tinder.
  useEffect(() => {
    if (!pid || proposed.current) return
    proposed.current = true
    proposerProjet(pid).then(() => qc.invalidateQueries({ queryKey: ['parcours', pid] }))
  }, [pid, qc])

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
  const elargir = useMutation({
    mutationFn: () => chercherPlus(pid, { limit: 48, ile: true }),
    onSuccess: (r) => { setMsg(r.n_added > 0 ? `+${r.n_added} parcelle(s) ajoutée(s) (élargi à l'île)` : 'aucune nouvelle parcelle (déjà toutes proposées)'); qc.invalidateQueries({ queryKey: ['parcours', pid] }) },
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
        <div className="mt-1.5 flex items-start justify-between gap-3">
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
              {projet && criteres(projet.fiche).map((c, i) => (
                <span key={i} className="rounded-full bg-surface-3 px-2 py-0.5 text-[10.5px] text-txt-mut">{c}</span>
              ))}
              {projet?.derniere_execution_at && (
                <span className="whitespace-nowrap text-[10.5px] text-txt-dim">· rejoué {fmtDate(projet.derniere_execution_at)}</span>
              )}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
            <button data-kanban-chercher onClick={() => { setMsg(''); elargir.mutate() }} disabled={elargir.isPending}
              className="min-h-7 rounded-md border border-mint/45 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20 disabled:opacity-50">
              {elargir.isPending ? '…' : '+ Chercher plus'}
            </button>
            <a data-kanban-pdf href={projetPdfUrl(pid)} target="_blank" rel="noreferrer"
              className="min-h-7 rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt transition-colors duration-quick hover:border-mint hover:text-txt-hi">Exporter</a>
            <button data-kanban-renommer onClick={() => { setNomInput(projet?.nom ?? nom); setEditing(true) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Renommer</button>
            <button data-kanban-archiver onClick={() => { patch.mutate({ statut: 'archive' }); setOpenProjet(null) }}
              className="min-h-7 rounded-md px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">Archiver</button>
          </div>
        </div>
        {msg && <p data-kanban-msg className="mt-1.5 text-[10.5px] text-mint">{msg}</p>}
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
                    {isProp ? (filtreAnalyse ? 'Rien à analyser' : 'Rien à trier — « Chercher plus »') : col.key === 'retenue' ? 'Aucune retenue' : 'Aucune écartée'}
                  </div>
                )}
                {isProp
                  /* variante B : liste dense (encaisse 52+ parcelles, file de travail) */
                  ? apercu.map((it) => (
                      <ProposeeRow key={it.idu} it={it}
                        onDragStart={() => setDrag({ idu: it.idu, from: 'proposee' })}
                        onAction={(statut) => decide.mutate({ idu: it.idu, statut })}
                        onFiche={() => select(it.idu)} />
                    ))
                  /* variante A : cartes visuelles (décisions peu nombreuses du client) */
                  : apercu.map((it) => (
                      <KanbanCard key={it.idu} it={it} col={col.key}
                        onDragStart={() => setDrag({ idu: it.idu, from: col.key })}
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

/** M2 — vignette ortho IGN en LAZY LOADING (jamais chargée hors écran). Placeholder si pas de centre. */
function Vignette({ center }: { center: [number, number] | null | undefined }) {
  if (!center) return <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-line-2 bg-surface-2 text-[8px] text-txt-dim">IGN</div>
  const [lng, lat] = center; const d = 0.0009
  const url = `https://data.geopf.fr/wms-r/wms?LAYERS=HR.ORTHOIMAGERY.ORTHOPHOTOS&FORMAT=image/jpeg&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:4326&BBOX=${lat - d},${lng - d},${lat + d},${lng + d}&WIDTH=96&HEIGHT=96`
  return <img loading="lazy" src={url} alt="" className="h-12 w-12 shrink-0 rounded-md border border-line-2 object-cover" />
}

/** M2 — badges parcelle (défisc / PC caduc / hors critères). */
function Badges({ it }: { it: ParcoursItem }) {
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
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

/** M2 — LIGNE DENSE de la file « proposées » (variante B) : encaisse 52+ parcelles, triée par rang,
 *  « à analyser » remonté en tête (badge). Draggable ; boutons de décision inline. */
function ProposeeRow({ it, onDragStart, onAction, onFiche }: {
  it: ParcoursItem; onDragStart: () => void; onAction: (s: StatutParcelle) => void; onFiche: () => void
}) {
  const analyse = it.statut === 'a_analyser'
  return (
    <div draggable onDragStart={onDragStart} data-proposee-row={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className={`group flex cursor-pointer items-center gap-2 rounded-md border px-2 py-1.5 transition-colors duration-quick hover:border-mint/30 ${analyse ? 'border-st-creuser/50 bg-st-creuser/5' : 'border-line-2 bg-surface-2'}`}
      title="Ouvrir la fiche · glisser pour décider">
      {analyse && <span className="text-[10px] text-st-creuser" title="à analyser (remonté en tête)">◑</span>}
      <span className="w-[86px] shrink-0 truncate font-mono text-[10.5px] text-txt-hi">{it.idu.slice(8, 10)} {it.idu.slice(10)}</span>
      <span className="min-w-0 flex-1 truncate text-[10.5px] text-txt-mut">{it.commune}<Badges it={it} /></span>
      <TierBadge tier={it.tier} etage0={null} statut={null} />
      {it.surface_m2 != null && <span className="tnum hidden shrink-0 font-mono text-[10px] text-txt-dim sm:inline">{fmtM2(it.surface_m2)}</span>}
      <span className="flex shrink-0 gap-1 opacity-60 transition-opacity duration-quick group-hover:opacity-100">
        <button data-row-retenir onClick={() => onAction('retenue')} className="rounded border border-mint/60 px-1.5 py-1 text-[10px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15" title="Retenir">✓</button>
        {!analyse && <button data-row-analyser onClick={() => onAction('a_analyser')} className="rounded border border-st-creuser/50 px-1.5 py-1 text-[10px] text-st-creuser transition-colors duration-quick hover:bg-st-creuser/10" title="À analyser">◑</button>}
        <button data-row-ecarter onClick={() => onAction('ecartee')} className="rounded border border-st-ecartee/50 px-1.5 py-1 text-[10px] text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10" title="Écarter">✕</button>
      </span>
    </div>
  )
}

/** Carte de parcelle — draggable (DnD natif) ET boutons de repli (fallback accessible/mobile).
 *  Le corps ouvre la fiche ; les boutons appellent la mutation de statut (même logique partout). */
function KanbanCard({ it, col, onDragStart, onAction, onFiche }: {
  it: ParcoursItem; col: StatutParcelle
  onDragStart: () => void; onAction: (s: StatutParcelle) => void; onFiche: () => void
}) {
  return (
    <div draggable onDragStart={onDragStart}
      data-kanban-card={it.idu}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('button')) onFiche() }}
      className="group cursor-pointer rounded-lg bg-surface-3 p-3 shadow-elev-1 ring-1 ring-transparent transition-shadow duration-quick active:cursor-grabbing hover:ring-mint/30"
      title="Ouvrir la fiche · glisser pour changer de colonne">
      <div className="flex gap-2.5">
        <Vignette center={it.center} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-mono text-[11px] font-medium text-txt-hi">{it.idu.slice(8, 10)} {it.idu.slice(10)}</span>
            <TierBadge tier={it.tier} etage0={null} statut={null} />
          </div>
          <div className="tnum mt-0.5 truncate text-[10.5px] text-txt-mut"
            title="Tier = probabilité relative de mutation (facteur P) ; qualité = complétude du dossier (couches renseignées). Deux choses distinctes.">
            {it.commune}{it.q_score != null ? ` · qualité ${fmtInt(it.q_score)}/100` : ''}{it.surface_m2 != null ? ` · ${fmtM2(it.surface_m2)}` : ''}</div>
          <div className="mt-1"><Badges it={it} /></div>
        </div>
      </div>
      {col === 'retenue' && (
        <div className="mt-1.5 border-t border-line-2/60 pt-1.5">
          <div className="text-[10px] text-mint" title="Piste créée automatiquement dans le CRM — remettre à trier l'en retire">▸ dans le CRM · contact à préparer</div>
          <ProprioLine p={it.proprietaire_public} />
        </div>
      )}
      {/* boutons de repli — accessibilité + mobile (le drag n'est pas la seule voie) */}
      <div className="mt-2 flex gap-1.5">
        {col !== 'retenue' && (
          <button data-card-retenir onClick={() => onAction('retenue')}
            className="min-h-7 flex-1 rounded-md border border-mint/60 py-1 text-[10.5px] font-semibold text-mint transition-colors duration-quick hover:bg-mint/15">✓ Retenir</button>
        )}
        {col !== 'ecartee' && (
          <button data-card-ecarter onClick={() => onAction('ecartee')}
            className="min-h-7 flex-1 rounded-md border border-st-ecartee/50 py-1 text-[10.5px] font-medium text-st-ecartee transition-colors duration-quick hover:bg-st-ecartee/10">✕ Écarter</button>
        )}
        {col !== 'proposee' && (
          <button data-card-retrier onClick={() => onAction('proposee')}
            className="min-h-7 flex-1 rounded-md border border-line-2 py-1 text-[10.5px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt"
            title={col === 'ecartee' ? 'Récupérer (repasse à trier)' : 'Remettre à trier (retire du CRM)'}>↩ {col === 'ecartee' ? 'Récupérer' : 'À trier'}</button>
        )}
      </div>
    </div>
  )
}
