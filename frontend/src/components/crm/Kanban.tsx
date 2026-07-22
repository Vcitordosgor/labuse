import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { deletePipeline, getEventsCount, getPipeline, getPipelineMeta, patchPipeline } from '../../lib/api'
import { fmtM2 } from '../../lib/format'
import { completudeColor, SCORE_TIP, verdictMeta } from '../../lib/status'
import type { PipelineEntry } from '../../lib/types'
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

export function Kanban() {
  const qc = useQueryClient()
  const meta = useQuery({ queryKey: ['pipeline-meta'], queryFn: getPipelineMeta })
  const entries = useQuery({ queryKey: ['pipeline'], queryFn: getPipeline })
  const evCount = useQuery({ queryKey: ['events-count'], queryFn: getEventsCount, refetchInterval: 60_000 })
  const [dragId, setDragId] = useState<number | null>(null)
  const [overCol, setOverCol] = useState<string | null>(null)
  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => patchPipeline(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
  })

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
        {/* P7 (dernière passe) : dire clairement qu'on peut défiler horizontalement */}
        {cols.length > 4 && (
          <span className="shrink-0 rounded-full border border-line-2 px-2.5 py-1 text-[10.5px] text-txt-mut">
            {cols.length} étapes · défiler →
          </span>
        )}
      </div>
      {/* P7 : dégradé de bord droit = affordance « il y a d'autres colonnes » */}
      <div className="relative mt-4 min-h-0 flex-1">
        <div className="flex h-full gap-3 overflow-x-auto px-4 pb-5 sm:px-6">
        {meta.isLoading && <div className="p-2"><Loading label="Chargement du pipeline" className="text-xs" /></div>}
        {cols.map((c) => {
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
                <span className="truncate text-[11px] font-medium text-txt">{c.label}</span>
                <span className="ml-auto font-mono text-[11px] text-txt-dim">{items.length}</span>
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
    </div>
  )
}
