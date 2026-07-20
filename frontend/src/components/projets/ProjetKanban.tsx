import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  chercherPlus, getParcoursEtat, getProjet, patchProjet, projetPdfUrl, proposerProjet, setStatutParcelle,
  type FicheProjet, type ParcoursEtat, type ParcoursItem, type ProprietairePublic, type StatutParcelle,
} from '../../lib/api'
import { useApp } from '../../store/useApp'
import { TierBadge } from '../outils/TierBadge'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

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
  if (f.budget_foncier_eur) out.push(`${(f.budget_foncier_eur / 1000).toLocaleString('fr-FR')} k€`)
  return out
}

function frDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: '2-digit' }) : '—'
}

/** Les 3 colonnes du projet unifié — UNE seule source de vérité : les statuts `projet_parcelles`. */
const COLS: { key: StatutParcelle; label: string; accent: string }[] = [
  { key: 'proposee', label: 'À trier', accent: '#8FB4F0' },
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
    <div className="truncate text-[10px] text-txt-mut" title={`Personne morale · SIREN ${p.siren ?? '—'}`}>
      <span className="text-txt">{p.denomination}</span>{p.siren ? <span className="text-txt-dim"> · SIREN {p.siren}</span> : null}
    </div>
  )
  return <div className="truncate text-[10px] italic text-txt-dim" title="Propriétaire personne physique — non communiqué (privacy)">Propriétaire particulier — non communiqué</div>
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
      <div className="shrink-0 border-b border-line-2 px-6 pt-5 pb-3">
        <button onClick={() => setOpenProjet(null)} className="text-[11px] text-txt-mut hover:text-txt-hi" title="Revenir à la liste des projets">← Mes projets</button>
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
                <span key={i} className="rounded-full border border-line-2 bg-surface-2 px-2 py-0.5 text-[10.5px] text-txt-mut">{c}</span>
              ))}
              {projet?.derniere_execution_at && (
                <span className="text-[10.5px] text-txt-dim">· rejoué {frDate(projet.derniere_execution_at)}</span>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button data-kanban-chercher onClick={() => { setMsg(''); elargir.mutate() }} disabled={elargir.isPending}
              className="rounded-md border border-mint/45 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint hover:bg-mint/20 disabled:opacity-50">
              {elargir.isPending ? '…' : '＋ Chercher plus'}
            </button>
            <a data-kanban-pdf href={projetPdfUrl(pid)} target="_blank" rel="noreferrer"
              className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:border-mint hover:text-txt-hi">Exporter</a>
            <button data-kanban-renommer onClick={() => { setNomInput(projet?.nom ?? nom); setEditing(true) }}
              className="rounded-md px-2 py-1 text-[11px] text-txt-mut hover:text-txt-hi">Renommer</button>
            <button data-kanban-archiver onClick={() => { patch.mutate({ statut: 'archive' }); setOpenProjet(null) }}
              className="rounded-md px-2 py-1 text-[11px] text-txt-mut hover:text-txt-hi">Archiver</button>
          </div>
        </div>
        {msg && <p data-kanban-msg className="mt-1.5 text-[10.5px] text-mint">{msg}</p>}
      </div>

      {/* 3 COLONNES */}
      <div className="flex min-h-0 flex-1 gap-4 overflow-x-auto p-6">
        {etatQ.isLoading && <p className="text-xs text-txt-dim">Chargement du projet…</p>}
        {COLS.map((col) => {
          const list = items(col.key)
          const apercu = expandCol === col.key ? list : list.slice(0, APERCU)
          const reste = list.length - apercu.length
          return (
            <div key={col.key} data-kanban-col={col.key}
              onDragOver={(e) => { e.preventDefault(); setOverCol(col.key) }}
              onDragLeave={() => setOverCol((o) => (o === col.key ? null : o))}
              onDrop={(e) => { e.preventDefault(); onDrop(col.key) }}
              className={`flex w-[320px] max-w-[34vw] shrink-0 flex-col rounded-xl border bg-surface-1 ${overCol === col.key && drag && drag.from !== col.key ? 'border-mint ring-1 ring-mint/40' : 'border-line-2'}`}>
              {/* tête de colonne : compteur + action de tête */}
              <div className="flex shrink-0 items-center gap-2 border-b border-line-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: col.accent }} />
                <span className="text-[12px] font-medium text-txt-hi">{col.label}</span>
                <span data-kanban-count={col.key} className="font-mono text-[11px] text-txt-dim">{count(col.key)}</span>
                {col.key === 'proposee' && count('proposee') > 0 && (
                  <button data-kanban-trier onClick={() => openParcours({ id: pid, nom: projet?.nom ?? nom })}
                    className="ml-auto rounded-md bg-mint px-2.5 py-1 text-[11px] font-semibold text-[#06130C] hover:brightness-110"
                    title="Parcourir les parcelles à trier une par une (carte)">Trier les {count('proposee')}</button>
                )}
                {col.key === 'retenue' && <span className="ml-auto text-[10px] text-txt-dim" title="Chaque retenue crée une piste CRM (contact à préparer)">→ CRM</span>}
                {col.key === 'ecartee' && <span className="ml-auto text-[10px] text-txt-dim">réversible</span>}
              </div>
              {/* aperçu : 2-3 cartes + « + N autres » */}
              <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2.5">
                {list.length === 0 && (
                  <div className="rounded-lg border border-dashed border-line-2 py-6 text-center text-[11px] text-txt-dim">
                    {col.key === 'proposee' ? 'Rien à trier — « Chercher plus »' : col.key === 'retenue' ? 'Aucune retenue' : 'Aucune écartée'}
                  </div>
                )}
                {apercu.map((it) => (
                  <KanbanCard key={it.idu} it={it} col={col.key}
                    onDragStart={() => setDrag({ idu: it.idu, from: col.key })}
                    onAction={(statut) => decide.mutate({ idu: it.idu, statut })}
                    onFiche={() => select(it.idu)} />
                ))}
                {reste > 0 && (
                  <button data-kanban-plus={col.key} onClick={() => setExpandCol(col.key)}
                    className="rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-mut hover:border-mint hover:text-txt-hi">
                    + {reste} autre{reste > 1 ? 's' : ''}
                  </button>
                )}
                {expandCol === col.key && list.length > APERCU && (
                  <button onClick={() => setExpandCol(null)} className="text-[10.5px] text-txt-dim hover:text-txt-mut">réduire</button>
                )}
              </div>
            </div>
          )
        })}
      </div>
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
      className="group cursor-pointer rounded-[10px] border border-line-2 bg-surface-3 p-3 active:cursor-grabbing hover:border-[#2E5A45]"
      title="Ouvrir la fiche · glisser pour changer de colonne">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-mono text-[11px] font-medium text-txt-hi">{it.idu.slice(8, 10)} {it.idu.slice(10)}</span>
        <TierBadge tier={it.tier} etage0={null} statut={null} />
      </div>
      <div className="mt-0.5 text-[10.5px] text-txt-mut">{it.commune}{it.q_score != null ? ` · qualité ${fmt(it.q_score)}/100` : ''}</div>
      {col === 'retenue' && (
        <div className="mt-1.5 border-t border-line-2/60 pt-1.5">
          <div className="text-[10px] text-mint" title="Piste créée automatiquement dans le CRM">▸ dans le CRM · contact à préparer</div>
          <ProprioLine p={it.proprietaire_public} />
        </div>
      )}
      {/* boutons de repli — accessibilité + mobile (le drag n'est pas la seule voie) */}
      <div className="mt-2 flex gap-1.5">
        {col !== 'retenue' && (
          <button data-card-retenir onClick={() => onAction('retenue')}
            className="flex-1 rounded-md bg-mint/90 py-1 text-[10.5px] font-semibold text-[#06130C] hover:bg-mint">✓ Retenir</button>
        )}
        {col !== 'ecartee' && (
          <button data-card-ecarter onClick={() => onAction('ecartee')}
            className="flex-1 rounded-md border border-[#E8695A]/50 py-1 text-[10.5px] font-medium text-[#E8695A] hover:bg-[#E8695A]/10">✕ Écarter</button>
        )}
        {col !== 'proposee' && (
          <button data-card-retrier onClick={() => onAction('proposee')}
            className="flex-1 rounded-md border border-line-2 py-1 text-[10.5px] text-txt-mut hover:border-mint hover:text-txt"
            title={col === 'ecartee' ? 'Récupérer (repasse à trier)' : 'Remettre à trier (retire du CRM)'}>↩ {col === 'ecartee' ? 'Récupérer' : 'À trier'}</button>
        )}
      </div>
    </div>
  )
}
