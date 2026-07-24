import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  createCrmColumn, deleteCrmColumn, deletePipeline, getEventsCount, getPipeline, getPipelineMeta,
  patchPipeline, renameCrmColumn, reorderCrmColumns, resetCrmColumns,
} from '../../lib/api'
import { fmtM2 } from '../../lib/format'
import { completudeColor, SCORE_TIP, verdictMeta } from '../../lib/status'
import type { PipelineColumn, PipelineEntry } from '../../lib/types'
import { Tip } from '../Tip'
import { ErrorState } from '../States'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

/* accents de colonnes = tokens (txt-dim / st-creuser / mint / st-ecartee) en valeur
   hex car servis via style= (pas de classe dynamique). */
const TONE_ACCENT: Record<string, string> = {
  cold: '#5C7268', warm: '#E8B44C', hot: '#5CE6A1', reject: '#E8695A',
}

function Card({ e, onDragStart, newEvents }: { e: PipelineEntry; onDragStart: (ev: React.DragEvent) => void; newEvents: number }) {
  const { select, setView } = useApp()
  const qc = useQueryClient()
  const del = useMutation({
    mutationFn: () => deletePipeline(e.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline'] })
      qc.invalidateQueries({ queryKey: ['pipeline-parcel', e.idu] })
    },
  })
  const prem = e.premium
  // correctif M5 : le badge de carte suit le verdict effectif (tier v2, étage 0 prime)
  const meta = prem ? verdictMeta(prem.statut, prem.tier_v2, prem.etage0) : null
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={(ev) => {
        // le CORPS de la carte ouvre la fiche (inspection : zone inerte au clic) — sauf ✕
        if ((ev.target as HTMLElement).closest('button')) return
        setView('cartes'); select(e.idu)
      }}
      className="group cursor-pointer rounded-lg bg-surface-3 p-3 shadow-elev-1 ring-1 ring-transparent transition-shadow duration-quick active:cursor-grabbing hover:ring-mint/30"
      title="Ouvrir la fiche · glisser pour changer d'étape"
    >
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={() => { setView('cartes'); select(e.idu) }}
          className="truncate font-mono text-xs font-medium text-txt-hi transition-colors duration-quick hover:text-mint"
          title="Ouvrir la fiche sur la carte"
        >
          {e.idu.slice(8, 10)} {e.idu.slice(10)}
        </button>
        {newEvents > 0 && (
          <Tip tip="Événements non lus sur cette parcelle (cloche)">
            <span className="shrink-0 rounded-full bg-violet/15 px-1.5 py-0.5 text-[9px] font-medium text-violet">
              {newEvents} nouveau{newEvents > 1 ? 'x' : ''}
            </span>
          </Tip>
        )}
        <button
          onClick={() => del.mutate()}
          className="-m-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-dim opacity-40 transition-opacity duration-quick hover:text-st-ecartee group-hover:opacity-100"
          title="Retirer du pipeline"
          aria-label="Retirer du pipeline"
        >
          ✕
        </button>
      </div>
      <div className="tnum mt-1 truncate text-[11px] text-txt-mut">
        {e.parcel.surface_m2 ? `${fmtM2(e.parcel.surface_m2)} · ` : ''}{e.parcel.commune}
      </div>
      {/* Phase 2 : d'où vient la piste (projet) */}
      {e.projet && (
        <div className="mt-1 truncate text-[10.5px] text-violet" title={`Piste du projet « ${e.projet.nom} »`}>
          ▸ {e.projet.nom}
        </div>
      )}
      {/* Phase 2 : contact proprio — PRIVACY : personne morale publique OU particulier JAMAIS nommé */}
      {e.proprietaire_public && (
        e.proprietaire_public.type === 'personne_morale' ? (
          <div className="mt-1 truncate text-[10.5px] text-txt-mut" title={`Personne morale (registre public DGFiP) · SIREN ${e.proprietaire_public.siren ?? '—'}`}>
            <span className="text-txt">{e.proprietaire_public.denomination}</span>
            {e.proprietaire_public.siren ? <span className="text-txt-dim"> · SIREN {e.proprietaire_public.siren}</span> : null}
          </div>
        ) : (
          <div className="mt-1 truncate text-[10.5px] italic text-txt-dim" title="Propriétaire personne physique — jamais nommé (privacy)">
            Propriétaire particulier — non communiqué
          </div>
        )
      )}
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        {meta && (
          <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px]" style={{ background: `${meta.color}22`, color: meta.color }}>
            <span className="h-1 w-1 rounded-full" style={{ background: meta.color }} />{meta.label}
          </span>
        )}
        {prem && (
          <>
            <Tip tip={SCORE_TIP.q}>
              <span className="font-display text-xs font-bold tnum" style={{ color: meta?.color }}>{prem.q_score}</span>
            </Tip>
            <Tip tip={`Complétude des données : ${prem.completeness_score}/100 — part des sources disponibles, pas une note de qualité.`}
              className="items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: completudeColor(prem.completeness_score) }} />
              <span className="text-[11px] text-txt-dim tnum">{prem.completeness_score}%</span>
            </Tip>
          </>
        )}
        {!prem && <span className="text-[11px] text-txt-dim">hors run de référence</span>}
        <span className="ml-auto shrink-0 text-[11px] text-txt-dim" title="Priorité de suivi de la piste">{e.priority}</span>
      </div>
    </div>
  )
}

/* ── M12 LOT H — dialogue « où déplacer les cartes ? » avant suppression d'une colonne peuplée.
   La boussole produit : une carte ne disparaît JAMAIS en silence — le déplacement est obligatoire. */
function DeleteColumnDialog({ col, others, onCancel, onConfirm }: {
  col: PipelineColumn; others: PipelineColumn[]; onCancel: () => void
  onConfirm: (moveTo: number | null) => void
}) {
  const [target, setTarget] = useState<number | ''>(others[0]?.id ?? '')
  const populated = (col as { cards?: number }).cards ?? 0
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCancel}>
      <div className="w-full max-w-sm rounded-xl border border-line-2 bg-surface-1 p-5 shadow-elev-2"
        onClick={(ev) => ev.stopPropagation()}>
        <h3 className="font-display text-sm font-bold text-txt-hi">Supprimer « {col.label} »</h3>
        {populated > 0 ? (
          <>
            <p className="mt-2 text-[12px] text-txt-mut">
              Cette colonne contient <span className="text-txt">{populated} carte{populated > 1 ? 's' : ''}</span>.
              Choisissez où les déplacer — aucune carte n'est perdue.
            </p>
            <label className="mt-3 block text-[11px] text-txt-dim">Déplacer les cartes vers</label>
            <select
              value={target}
              onChange={(ev) => setTarget(ev.target.value ? Number(ev.target.value) : '')}
              className="mt-1 w-full rounded-md border border-line-2 bg-surface-2 px-2 py-1.5 text-[12px] text-txt"
            >
              {others.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
          </>
        ) : (
          <p className="mt-2 text-[12px] text-txt-mut">Cette colonne est vide — suppression immédiate.</p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-[12px] text-txt-dim hover:text-txt">Annuler</button>
          <button
            onClick={() => onConfirm(populated > 0 ? (target === '' ? null : target) : null)}
            disabled={populated > 0 && target === ''}
            className="rounded-md bg-st-ecartee/90 px-3 py-1.5 text-[12px] font-medium text-bg hover:bg-st-ecartee disabled:opacity-40"
          >Supprimer</button>
        </div>
      </div>
    </div>
  )
}

export function Kanban() {
  const qc = useQueryClient()
  const meta = useQuery({ queryKey: ['pipeline-meta'], queryFn: getPipelineMeta })
  const entries = useQuery({ queryKey: ['pipeline'], queryFn: getPipeline })
  const evCount = useQuery({ queryKey: ['events-count'], queryFn: getEventsCount, refetchInterval: 60_000 })
  const [dragId, setDragId] = useState<number | null>(null)
  const [overCol, setOverCol] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [pendingDelete, setPendingDelete] = useState<PipelineColumn | null>(null)
  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => patchPipeline(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
  })
  // M12 LOT H — mutations colonnes (invalident meta + pipeline : le remap de cartes est visible)
  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['pipeline-meta'] })
    qc.invalidateQueries({ queryKey: ['pipeline'] })
  }
  const addCol = useMutation({ mutationFn: (label: string) => createCrmColumn(label), onSuccess: invalidateAll })
  const renameCol = useMutation({
    mutationFn: ({ id, label }: { id: number; label: string }) => renameCrmColumn(id, label),
    onSuccess: () => { setEditingId(null); invalidateAll() },
  })
  const reorderCol = useMutation({ mutationFn: (order: number[]) => reorderCrmColumns(order), onSuccess: invalidateAll })
  const delCol = useMutation({
    mutationFn: ({ id, moveTo }: { id: number; moveTo: number | null }) => deleteCrmColumn(id, moveTo),
    onSuccess: () => { setPendingDelete(null); invalidateAll() },
  })
  const resetCols = useMutation({ mutationFn: () => resetCrmColumns(), onSuccess: invalidateAll })

  if (meta.isError || entries.isError) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <ErrorState message="Pipeline inaccessible"
          hint="Le serveur ne répond pas — vos données sont intactes, seule la connexion est en cause."
          retry={() => { meta.refetch(); entries.refetch() }} />
      </div>
    )
  }

  const cols = meta.data?.columns ?? []
  const byCol = (key: string) => (entries.data ?? []).filter((e) => e.status === key)
  const cardCount = (key: string) => byCol(key).length

  const startEdit = (c: PipelineColumn) => { setEditingId(c.id ?? null); setEditLabel(c.label) }
  const commitEdit = () => {
    if (editingId != null && editLabel.trim()) renameCol.mutate({ id: editingId, label: editLabel.trim() })
    else setEditingId(null)
  }
  const doAdd = () => {
    const label = window.prompt('Nom de la nouvelle colonne')?.trim()
    if (label) addCol.mutate(label)
  }
  const moveCol = (idx: number, dir: -1 | 1) => {
    const ids = cols.map((c) => c.id!).filter((i) => i != null)
    const j = idx + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[idx], ids[j]] = [ids[j], ids[idx]]
    reorderCol.mutate(ids)
  }
  // colonne enrichie du nombre de cartes (le dialogue de suppression en a besoin)
  const withCounts = cols.map((c) => ({ ...c, cards: cardCount(c.key) })) as (PipelineColumn & { cards: number })[]

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 flex-wrap items-baseline justify-between gap-2 px-4 pt-5 sm:px-6">
        <div>
          <h2 className="font-display text-lg font-bold text-txt-hi">CRM — pipeline de prospection</h2>
          <p className="mt-0.5 text-[11px] text-txt-dim">
            {(entries.data ?? []).length} parcelle{(entries.data ?? []).length > 1 ? 's' : ''} suivie{(entries.data ?? []).length > 1 ? 's' : ''} ·
            glisser une carte pour changer d'étape · ajout depuis la fiche (+ Pipeline)
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {/* P7 (dernière passe) : dire clairement qu'on peut défiler horizontalement */}
          {cols.length > 4 && !editMode && (
            <span className="rounded-full border border-line-2 px-2.5 py-1 text-[10.5px] text-txt-mut">
              {cols.length} étapes · défiler →
            </span>
          )}
          {editMode && (
            <>
              <button onClick={doAdd}
                className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:border-mint hover:text-mint"
                title="Ajouter une colonne">+ Colonne</button>
              <button
                onClick={() => { if (window.confirm('Réinitialiser le kanban au modèle LABUSE par défaut ? Toutes les cartes seront replacées dans la première colonne.')) resetCols.mutate() }}
                className="rounded-md border border-line-2 px-2.5 py-1 text-[11px] text-txt-dim hover:border-st-ecartee hover:text-st-ecartee"
                title="Restaurer le kanban LABUSE par défaut">Réinitialiser</button>
            </>
          )}
          <button
            onClick={() => { setEditMode((v) => !v); setEditingId(null) }}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors duration-quick ${
              editMode ? 'bg-mint/15 text-mint' : 'border border-line-2 text-txt-dim hover:text-txt'}`}
            title="Personnaliser les colonnes du kanban"
          >{editMode ? 'Terminé' : 'Personnaliser'}</button>
        </div>
      </div>
      {/* P7 : dégradé de bord droit = affordance « il y a d'autres colonnes » */}
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="flex h-full gap-3 overflow-x-auto px-4 pb-5 sm:px-6">
        {meta.isLoading && <div className="p-2"><Loading label="Chargement du pipeline" className="text-xs" /></div>}
        {cols.map((c, idx) => {
          const items = byCol(c.key)
          const accent = TONE_ACCENT[c.tone ?? ''] ?? '#5C7268'
          return (
            <div
              key={c.key}
              onDragOver={(ev) => { ev.preventDefault(); setOverCol(c.key) }}
              onDragLeave={() => setOverCol((o) => (o === c.key ? null : o))}
              onDrop={(ev) => {
                ev.preventDefault()
                setOverCol(null)
                if (dragId != null) move.mutate({ id: dragId, status: c.key })
                setDragId(null)
              }}
              className={`flex w-[230px] shrink-0 flex-col rounded-xl border bg-surface-1 shadow-elev-1 transition-colors duration-quick ${
                overCol === c.key ? 'border-mint ring-1 ring-mint/40' : 'border-transparent'}`}
            >
              <div className="flex shrink-0 items-center gap-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
                {editMode && editingId === c.id ? (
                  <input
                    autoFocus
                    value={editLabel}
                    onChange={(ev) => setEditLabel(ev.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={(ev) => { if (ev.key === 'Enter') commitEdit(); if (ev.key === 'Escape') setEditingId(null) }}
                    className="min-w-0 flex-1 rounded border border-mint/40 bg-surface-2 px-1 py-0.5 text-[11px] text-txt"
                    aria-label="Renommer la colonne"
                  />
                ) : (
                  <button
                    disabled={!editMode}
                    onClick={() => editMode && startEdit(c)}
                    className={`min-w-0 flex-1 truncate text-left text-[11px] font-medium text-txt ${editMode ? 'cursor-text hover:text-mint' : 'cursor-default'}`}
                    title={editMode ? 'Cliquer pour renommer' : c.label}
                  >{c.label}</button>
                )}
                {!editMode && <span className="ml-auto font-mono text-[11px] text-txt-dim">{items.length}</span>}
                {editMode && (
                  <span className="ml-auto flex shrink-0 items-center gap-0.5">
                    <button onClick={() => moveCol(idx, -1)} disabled={idx === 0}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-txt disabled:opacity-25"
                      title="Déplacer à gauche" aria-label="Déplacer la colonne à gauche">←</button>
                    <button onClick={() => moveCol(idx, 1)} disabled={idx === cols.length - 1}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-txt disabled:opacity-25"
                      title="Déplacer à droite" aria-label="Déplacer la colonne à droite">→</button>
                    <button
                      onClick={() => setPendingDelete(withCounts[idx])}
                      disabled={cols.length <= 1}
                      className="flex h-5 w-5 items-center justify-center rounded text-txt-dim hover:text-st-ecartee disabled:opacity-25"
                      title={cols.length <= 1 ? 'La dernière colonne ne peut pas être supprimée' : 'Supprimer la colonne'}
                      aria-label="Supprimer la colonne">✕</button>
                  </span>
                )}
              </div>
              <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto px-2.5 pb-2.5">
                {items.map((e) => (
                  <Card key={e.id} e={e} onDragStart={() => setDragId(e.id)}
                    newEvents={evCount.data?.par_parcelle[e.idu] ?? 0} />
                ))}
                {items.length === 0 && (
                  <div className="rounded-lg bg-surface-2/60 py-4 text-center text-[11px] text-txt-dim">vide</div>
                )}
              </div>
            </div>
          )
        })}
        </div>
        {/* fondu de bord droit — pointer-events-none pour ne pas gêner le drag/scroll */}
        {cols.length > 4 && (
          <div className="pointer-events-none absolute right-0 top-0 h-full w-12 bg-gradient-to-l from-bg to-transparent" />
        )}
      </div>
      {pendingDelete && (
        <DeleteColumnDialog
          col={pendingDelete}
          others={withCounts.filter((c) => c.id !== pendingDelete.id)}
          onCancel={() => setPendingDelete(null)}
          onConfirm={(moveTo) => delCol.mutate({ id: pendingDelete.id!, moveTo })}
        />
      )}
    </div>
  )
}
