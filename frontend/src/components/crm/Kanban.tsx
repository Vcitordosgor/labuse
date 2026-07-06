import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { deletePipeline, getPipeline, getPipelineMeta, patchPipeline } from '../../lib/api'
import { completudeColor, STATUT_META } from '../../lib/status'
import type { PipelineEntry } from '../../lib/types'
import { useApp } from '../../store/useApp'

const TONE_ACCENT: Record<string, string> = {
  cold: '#5C7268', warm: '#E8B44C', hot: '#5CE6A1', reject: '#E8695A',
}

function Card({ e, onDragStart }: { e: PipelineEntry; onDragStart: (ev: React.DragEvent) => void }) {
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
  const meta = prem ? STATUT_META[prem.statut] : null
  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="group cursor-grab rounded-[10px] border border-line-2 bg-surface-3 p-3 active:cursor-grabbing"
    >
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={() => { setView('cartes'); select(e.idu) }}
          className="truncate font-mono text-xs font-medium text-txt-hi hover:text-mint"
          title="Ouvrir la fiche sur la carte"
        >
          {e.idu.slice(8, 10)} {e.idu.slice(10)}
        </button>
        <button
          onClick={() => del.mutate()}
          className="shrink-0 text-txt-dim opacity-0 hover:text-st-ecartee group-hover:opacity-100"
          title="Retirer du pipeline"
        >
          ✕
        </button>
      </div>
      <div className="mt-0.5 truncate text-[11px] text-txt-mut">
        {e.parcel.surface_m2 ? `${Math.round(e.parcel.surface_m2).toLocaleString('fr-FR')} m² · ` : ''}{e.parcel.commune}
      </div>
      <div className="mt-2 flex items-center gap-2">
        {meta && (
          <span className="flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9.5px]" style={{ background: `${meta.color}22`, color: meta.color }}>
            <span className="h-1 w-1 rounded-full" style={{ background: meta.color }} />{meta.label}
          </span>
        )}
        {prem && (
          <>
            <span className="font-display text-xs font-bold" style={{ color: meta?.color }}>{prem.q_score}</span>
            <span className="flex items-center gap-1 text-[9.5px] text-txt-dim" title={`Complétude ${prem.completeness_score}%`}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: completudeColor(prem.completeness_score) }} />
              {prem.completeness_score}%
            </span>
          </>
        )}
        {!prem && <span className="text-[9.5px] text-txt-dim">hors run q_v2</span>}
        <span className="ml-auto text-[9.5px] text-txt-dim">{e.priority}</span>
      </div>
    </div>
  )
}

export function Kanban() {
  const qc = useQueryClient()
  const meta = useQuery({ queryKey: ['pipeline-meta'], queryFn: getPipelineMeta })
  const entries = useQuery({ queryKey: ['pipeline'], queryFn: getPipeline })
  const [dragId, setDragId] = useState<number | null>(null)
  const [overCol, setOverCol] = useState<string | null>(null)
  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => patchPipeline(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
  })

  if (meta.isError || entries.isError) {
    return <div className="flex flex-1 items-center justify-center text-xs text-st-ecartee">Pipeline inaccessible — serveur à relancer ?</div>
  }

  const cols = meta.data?.columns ?? []
  const byCol = (key: string) => (entries.data ?? []).filter((e) => e.status === key)

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-baseline justify-between px-6 pt-5">
        <div>
          <h2 className="text-sm font-medium text-txt-hi">CRM — pipeline de prospection</h2>
          <p className="mt-0.5 text-[11px] text-txt-dim">
            {(entries.data ?? []).length} parcelle{(entries.data ?? []).length > 1 ? 's' : ''} suivie{(entries.data ?? []).length > 1 ? 's' : ''} ·
            glisser une carte pour changer d'étape · ajout depuis la fiche (+ Pipeline)
          </p>
        </div>
      </div>
      <div className="mt-4 flex min-h-0 flex-1 gap-3 overflow-x-auto px-6 pb-5">
        {meta.isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
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
              className={`flex w-[230px] shrink-0 flex-col rounded-xl border bg-surface-1 ${
                overCol === c.key ? 'border-mint' : 'border-line'}`}
            >
              <div className="flex shrink-0 items-center gap-2 px-3 py-2.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
                <span className="truncate text-[11px] font-medium text-txt">{c.label}</span>
                <span className="ml-auto font-mono text-[10px] text-txt-dim">{items.length}</span>
              </div>
              <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2">
                {items.map((e) => (
                  <Card key={e.id} e={e} onDragStart={() => setDragId(e.id)} />
                ))}
                {items.length === 0 && (
                  <div className="rounded-lg border border-dashed border-line-2 py-4 text-center text-[10px] text-txt-dim">vide</div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
