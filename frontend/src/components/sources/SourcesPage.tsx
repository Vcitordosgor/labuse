import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getSources } from '../../lib/api'
import type { SourceInfo } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const STATUS_DOT: Record<string, string> = {
  active: '#5CE6A1', ok: '#5CE6A1', partial: '#E8B44C', degraded: '#E8B44C',
  planned: '#5C7268', todo: '#5C7268', error: '#E8695A', down: '#E8695A',
}

// B3 (mandat calculette) — FRAÎCHEUR PAR SOURCE. La date affichée est RÉELLE (last_sync_at =
// dernière ingestion), jamais inventée. Tant que le cron n'existe pas, ce sont des dates FIGÉES
// d'ingestion, dites telles quelles. Source sans métadonnée de date → « ingestion non tracée ».
function freshness(iso: string | null): { label: string; color: string } {
  if (!iso) return { label: 'ingestion non tracée', color: '#5C7268' }
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days <= 0) return { label: "aujourd'hui", color: '#5CE6A1' }
  if (days <= 30) return { label: `il y a ${days} j`, color: days <= 7 ? '#5CE6A1' : '#E8B44C' }
  return { label: `il y a ${Math.round(days / 30)} mois`, color: '#E8B44C' }
}

function Row({ s, focused }: { s: SourceInfo; focused: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: 'center' })
  }, [focused])
  const f = freshness(s.last_sync_at)
  return (
    <div ref={ref}
      className={`flex items-center gap-4 rounded-[10px] border px-4 py-3 ${
        focused ? 'border-mint bg-[#0F1A14]' : 'border-line-2 bg-surface-3'}`}>
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: STATUS_DOT[s.status ?? ''] ?? '#5C7268' }}
        title={`Statut : ${s.status ?? 'inconnu'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-xs font-medium text-txt">{s.name}</span>
          {s.provider && <span className="shrink-0 text-[10px] text-txt-dim">{s.provider}</span>}
        </div>
        <div className="mt-0.5 flex items-center gap-3 text-[10.5px] text-txt-dim">
          {s.access_type && <span>{s.access_type}</span>}
          {s.reliability_level && <span>fiabilité {s.reliability_level}</span>}
          {s.documentation_url && (
            <a href={s.documentation_url} target="_blank" rel="noreferrer" className="text-[#5a7d6c] hover:text-mint hover:underline">
              documentation ↗
            </a>
          )}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <div className="font-mono text-[11px]" style={{ color: f.color }}>{f.label}</div>
        <div className="text-[9.5px] text-txt-dim">{s.last_sync_at ? new Date(s.last_sync_at).toLocaleDateString('fr-FR') : '—'}</div>
      </div>
    </div>
  )
}

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const sourcesFocus = useApp((s) => s.sourcesFocus)

  const cats = new Map<string, SourceInfo[]>()
  for (const s of data ?? []) {
    const k = s.category || 'Autres'
    cats.set(k, [...(cats.get(k) ?? []), s])
  }
  // résumé « mises à jour » — dates RÉELLES uniquement (aucune inventée)
  const tracees = (data ?? []).filter((s) => s.last_sync_at)
  const derniere = tracees.map((s) => s.last_sync_at as string).sort().slice(-1)[0]

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-6 py-6">
        <h2 className="text-sm font-medium text-txt-hi">Sources & mises à jour</h2>
        <p className="mt-1 text-[11px] leading-relaxed text-txt-dim">
          Chaque fait affiché dans une fiche est tracé jusqu'à sa source et porte sa date. Ci-dessous,
          la <b className="text-txt-mut">dernière ingestion</b> par source (date réelle). Les
          rafraîchissements sont aujourd'hui manuels ; l'écran est prêt à afficher la fraîcheur
          automatique dès que la synchronisation planifiée sera en place.
        </p>
        {data && (
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5 text-[11px]">
            <span className="font-mono tracking-widest text-txt-dim">MISES À JOUR</span>
            <span className="text-txt-mut"><b className="text-txt">{tracees.length}</b> / {data.length} sources datées</span>
            {derniere && <span className="text-txt-mut">dernière ingestion <b className="text-mint">{new Date(derniere).toLocaleDateString('fr-FR')}</b></span>}
            <span className="text-txt-dim">{(data.length - tracees.length)} sans date tracée</span>
          </div>
        )}
        {isLoading && <div className="mt-6"><Loading label="Chargement des sources" className="text-xs" /></div>}
        {isError && <p className="mt-6 text-xs text-st-ecartee">Sources inaccessibles — serveur à relancer ?</p>}
        {[...cats.entries()].map(([cat, list]) => (
          <div key={cat} className="mt-6">
            <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">{cat.toUpperCase()}</p>
            <div className="flex flex-col gap-2">
              {list.map((s) => <Row key={s.id} s={s} focused={s.name === sourcesFocus} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
